from orchestrator.registry import action
from rag.pipelines.multi_rag import multi_retrieve, grounded_answer

@action("multi_rag.retrieval", timeout_s=8)
def act_retrieve(query: str, k: int = 12, ctx: dict | None = None):
    return multi_retrieve(query, k=k, ctx=ctx)

@action("multi_rag.answer", timeout_s=12)
def act_grounded_answer(query: str, ctx: dict | None = None):
    return grounded_answer(query=query, ctx=ctx)

@action("planner.refine", timeout_s=4)
def act_refine(query: str, feedback: str, ctx: dict | None = None):
    return {"refined": f"{query} :: {feedback}"}
