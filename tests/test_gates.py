from validate import EvalResult, gates_decision

def test_block_when_toolacc_low():
    base_ppl = 8.5
    res = EvalResult(ppl=8.6, toolAcc=0.82, drift=0.03, guardrail=0.98, logs=[])
    d = gates_decision(base_ppl, res)
    assert d["block"] is True

def test_canary_near_thresholds():
    base_ppl = 8.5
    res = EvalResult(ppl=9.34, toolAcc=0.905, drift=0.069, guardrail=0.951, logs=[])
    d = gates_decision(base_ppl, res)
    assert d["block"] is False and d["forceCanary"] is True