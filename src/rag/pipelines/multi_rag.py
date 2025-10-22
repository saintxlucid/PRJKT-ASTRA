from typing import List, Dict
from telemetry.events import emit
from memory.bridge import callbacks

class Doc(dict):
    pass

def _rrf(runs: List[List[Doc]], k=20) -> List[Doc]:
    bucket: Dict[str, float] = {}
    merged: Dict[str, Doc] = {}
    for run in runs:
        for rank, d in enumerate(run[:k], start=1):
            bucket[d["id"]] = bucket.get(d["id"], 0.0) + 1.0 / (60 + rank)
            merged.setdefault(d["id"], d)
    out = list(merged.values())
    out.sort(key=lambda d: bucket.get(d["id"], 0), reverse=True)
    for d in out:
        d["score"] = bucket.get(d["id"], 0.0)
    return out

class BM25Retriever:
    def search(self, query: str, k=50) -> List[Doc]:
        return []

class DenseRetriever:
    def search(self, query: str, k=50) -> List[Doc]:
        return []

class Reranker:
    def rank(self, query: str, docs: List[Doc]) -> List[Doc]:
        return docs

bm25 = BM25Retriever()
dense = DenseRetriever()
reranker = Reranker()

def multi_retrieve(query: str, k: int = 12, ctx: dict | None = None):
    callbacks.pre_retrieve(query, ctx)
    bm25_res  = bm25.search(query, k=50)
    dense_res = dense.search(query, k=50)
    fused     = _rrf([bm25_res, dense_res], k=50)[:k]
    ranked    = reranker.rank(query, fused)[:k]
    emit("retrieval.complete",
         {"q": query, "k": k, "n": len(ranked),
          "sources": list({d.get("source") for d in ranked})})
    callbacks.post_retrieve(query, ranked, ctx)
    return {"docs": ranked, "trace": {"stages": ["bm25","dense","rrf","rerank"]}}

def grounded_answer(query: str, ctx: dict | None = None):
    batch = multi_retrieve(query, k=8, ctx=ctx)
    context = "\n\n".join(d.get("text","") for d in batch["docs"])[:2000]
    answer = f"[GROUNDING]\n{context[:400]}...\n[ANSWER]\nGrounded summary placeholder."
    callbacks.post_answer(query, answer, ctx)
    emit("answer.complete", {"q": query, "len": len(answer)})
    return {"answer": answer, "citations": [d["id"] for d in batch["docs"]]}
