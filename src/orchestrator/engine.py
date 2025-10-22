from orchestrator.actions import act_retrieve, act_grounded_answer

def handle_query(query: str, ctx: dict | None = None):
    r = act_retrieve(query=query, k=12, ctx=ctx)
    if not r.get("ok"):
        return r
    a = act_grounded_answer(query=query, ctx=ctx)
    return a
