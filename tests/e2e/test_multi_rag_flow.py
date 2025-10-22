import os
from orchestrator.engine import handle_query

def test_flow_smoke():
    out = handle_query("what is the consent policy?", ctx={"session":"smoke"})
    assert out.get("ok") is True
    assert "result" in out and ("answer" in out["result"] or "result" in out["result"])
