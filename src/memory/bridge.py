class callbacks:
    @staticmethod
    def pre_retrieve(query: str, ctx: dict | None = None):
        # attach tags or enrich query
        print(f"[CB] pre_retrieve: {query}")
        return None

    @staticmethod
    def post_retrieve(query: str, docs, ctx: dict | None = None):
        print(f"[CB] post_retrieve: {query} -> {len(docs)} docs")
        return None

    @staticmethod
    def post_answer(query: str, answer: str, ctx: dict | None = None):
        print(f"[CB] post_answer: {query} -> {len(answer)} chars")
        return None
