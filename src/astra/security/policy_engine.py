"""
YAML-driven Policy Engine
Supports simple rule matching with effect allow/deny/review.
Rules are evaluated in order; first match wins.
"""
from typing import Any, Dict, List
import yaml
import fnmatch
import structlog

logger = structlog.get_logger(__name__)

class PolicyRule:
    def __init__(self, rule_def: Dict[str, Any]):
        self.id = rule_def.get('id')
        self.when = rule_def.get('when', {})
        self.effect = rule_def.get('effect', 'review')

    def matches(self, tool: str, args: Dict[str, Any]) -> bool:
        # Basic matching: support tool glob and arg path globs
        tool_pattern = self.when.get('tool')
        if tool_pattern and not fnmatch.fnmatch(tool, tool_pattern):
            return False

        # args matching: simple key path support using dot notation
        for key, pattern in self.when.items():
            if key == 'tool':
                continue
            # key might be like args.dst
            if not key.startswith('args.'):
                continue
            arg_path = key.split('.', 1)[1]
            val = _get_nested(args, arg_path.split('.'))
            if val is None:
                return False
            if isinstance(pattern, list):
                if not any(fnmatch.fnmatch(str(val), p) for p in pattern):
                    return False
            else:
                if not fnmatch.fnmatch(str(val), pattern):
                    return False
        return True

def _get_nested(d: Dict[str, Any], path: List[str]):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur

class PolicyEngine:
    def __init__(self, policy_yaml: str):
        data = yaml.safe_load(policy_yaml)
        self.rules = [PolicyRule(r) for r in data.get('rules', [])]
        self.default = data.get('default', 'review')

    def evaluate(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        for rule in self.rules:
            if rule.matches(tool, args):
                return {'effect': rule.effect, 'rule': rule.id}
        return {'effect': self.default, 'rule': None}
