import time
import json
from astra.security.tokenizer import Tokenizer

SECRET = b'supersecret'

def test_token_create_verify():
    t = Tokenizer(SECRET)
    token = t.create('tester', {'fs.write'}, ttl=2)
    ok, reason, payload = t.verify(token, {'fs.write'})
    assert ok
    assert payload['sub'] == 'tester'

    # Expire
    time.sleep(3)
    ok2, reason2, _ = t.verify(token, {'fs.write'})
    assert not ok2

from astra.security.policy_engine import PolicyEngine

def test_policy_match():
    yaml = '''version: 1
rules:
  - id: allow-docs
    when:
      tool: "fs.copy"
      args.dst: 'C:\\Users\\*\\Documents\\**'
    effect: allow
default: review
'''
    p = PolicyEngine(yaml)
    res = p.evaluate('fs.copy', {'dst': 'C:\\Users\\alice\\Documents\\a.txt'})
    assert res['effect'] == 'allow'
    res2 = p.evaluate('fs.copy', {'dst': 'C:\\Windows\\System32\\b.dll'})
    assert res2['effect'] == 'review'
