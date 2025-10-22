"""
Tool Bus API (v1)
Provides endpoints for previewing and executing tools.
"""
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional
import structlog
import asyncio
import os

from astra.security.tokenizer import Tokenizer
from astra.security.dpapi_store import dpapi_unprotect
from astra.security.policy_engine import PolicyEngine
from astra.telemetry.audit import emit as audit_emit

logger = structlog.get_logger(__name__)

app = FastAPI(title='ASTRA Tool Bus')

# Load policy
POLICY_PATH = os.getenv('ASTRA_POLICY_PATH', '/app/config/policy.yaml')
try:
    with open(POLICY_PATH, 'r', encoding='utf-8') as f:
        POLICY_YAML = f.read()
except Exception:
    POLICY_YAML = 'version:1\nrules: []\ndefault: review'

policy_engine = PolicyEngine(POLICY_YAML)

# Load secret for tokenizer (DPAPI blob expected or raw secret env)
TOKEN_SECRET_BLOB = os.getenv('ASTRA_TOKEN_SECRET_BLOB')
if TOKEN_SECRET_BLOB:
    SECRET = dpapi_unprotect(TOKEN_SECRET_BLOB.encode('utf-8'))
else:
    SECRET = os.getenv('ASTRA_TOKEN_SECRET', 'dev_secret').encode('utf-8')

tokenizer = Tokenizer(SECRET)

class ToolRequest(BaseModel):
    tool: str
    args: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

@app.post('/v1/tools/preview')
async def preview(req: ToolRequest):
    # Evaluate policy
    decision = policy_engine.evaluate(req.tool, req.args or {})
    # Produce a fake diff and risk score for preview
    diff = [f"will_call:{req.tool}"]
    risk = 0.1 if decision['effect'] == 'allow' else 0.5

    # Emit audit event
    audit_emit({
        'action': 'tool.preview',
        'tool': req.tool,
        'args_redacted': _redact_args(req.args),
        'policy': decision,
        'outcome': {'diff': diff, 'risk': risk},
        'trace_id': req.trace_id,
    })

    return {'diff': diff, 'risk': risk, 'scopes': ['fs.write'], 'requires_consent': decision['effect'] != 'allow'}

@app.post('/v1/tools/execute')
async def execute(req: ToolRequest, x_astra_token: Optional[str] = Header(None)):
    # Verify token
    if not x_astra_token:
        raise HTTPException(status_code=401, detail='Missing token')
    ok, reason, payload = tokenizer.verify(x_astra_token, set())
    if not ok:
        raise HTTPException(status_code=401, detail=f'Token invalid: {reason}')

    # Evaluate policy
    decision = policy_engine.evaluate(req.tool, req.args or {})
    if decision['effect'] == 'deny':
        audit_emit({'action': 'tool.execute', 'tool': req.tool, 'policy': decision, 'outcome': {'status': 'deny'}})
        raise HTTPException(status_code=403, detail='Policy denied')

    # Simulate execution (dry-run safe execution)
    result = {'status': 'ok', 'details': f'executed {req.tool}'}

    # Emit audit
    audit_emit({
        'action': 'tool.execute',
        'tool': req.tool,
        'args_redacted': _redact_args(req.args),
        'policy': decision,
        'consent': {'token_id': payload.get('nonce')},
        'outcome': {'status': 'ok'},
        'trace_id': req.trace_id or payload.get('trace_id')
    })

    return {'status': 'ok', 'result': result, 'audit_id': f"evt_{os.urandom(4).hex()}"}

@app.post('/v1/consent/grant')
async def consent_grant(body: Dict[str, Any]):
    # For MVP, simply record consent and return token
    sub = body.get('sub', 'user')
    scopes = set(body.get('scopes', []))
    token = tokenizer.create(sub, scopes)
    audit_emit({'action': 'consent.grant', 'sub': sub, 'scopes': list(scopes), 'token_id': token.split('.')[-1][:8]})
    return {'token': token}

def _redact_args(args: Dict[str, Any]):
    # Very small redaction: remove sensitive-looking keys
    if not args:
        return {}
    redacted = {}
    for k,v in args.items():
        if any(s in k.lower() for s in ['password','secret','key']):
            redacted[k] = 'REDACTED'
        else:
            redacted[k] = v
    return redacted

# If run as a module, start a dev server
if __name__ == '__main__':
    import uvicorn
    uvicorn.run('astra.api.toolbus:app', host='0.0.0.0', port=8000, reload=True)
