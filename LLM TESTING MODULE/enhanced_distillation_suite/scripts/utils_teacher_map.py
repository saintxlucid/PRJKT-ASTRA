from typing import List, Dict, Any
import math

def build_sparse_teacher_over_student(step_top_logprobs: Dict[str, float], student_tokenize) -> Dict[int, float]:
    """
    step_top_logprobs: {"token_str": logprob, ...} from teacher for ONE timestep
    student_tokenize: function that returns student token ids for a string (no special tokens)
    Returns: dict {student_token_id: prob}
    """
    out: Dict[int, float] = {}
    for tok_str, lp in (step_top_logprobs or {}).items():
        # best-effort: only accept single-token encodes to avoid fragmentation
        ids = student_tokenize(tok_str)
        if len(ids) != 1:
            continue
        pid = ids[0]
        p = math.exp(lp)
        out[pid] = out.get(pid, 0.0) + p
    s = sum(out.values()) or 1.0
    for k in list(out.keys()):
        out[k] /= s
    return out