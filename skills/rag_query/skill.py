from sdk.skill_base import SkillBase, SkillMeta
from rag_mvp.store import query as rag_query

class RagQuerySkill(SkillBase):
    meta = SkillMeta("rag_query", "1.0.0", "Reasoning", "Medium", "Free", True, True)

    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2},
            "k": {"type": "integer", "minimum": 1, "maximum": 10},
            "tenant_id": {"type": "string"}  # optional override, else ctx tenant
        },
        "required": ["query"],
        "additionalProperties": False
    }

    output_schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string"},
                        "chunk": {"type": "integer"},
                        "score": {"type": "number"},
                        "text": {"type": "string"}
                    },
                    "required": ["doc_id", "chunk", "score", "text"]
                }
            },
            "_credits": {"type": "integer"}
        },
        "required": ["answer", "citations", "_credits"],
        "additionalProperties": True
    }

    def execute(self, ctx, inp):
        tenant_id = inp.get("tenant_id") or ctx.get("tenant_id", "t1")
        q = inp["query"]
        k = int(inp.get("k", 5))

        hits = rag_query(tenant_id, q, k)

        # MVP answer: just join top chunks (later: send to LLM)
        if not hits:
            return {
                "answer": "No documents found for this tenant. Add docs first using /rag/add.",
                "citations": [],
                "_credits": 2
            }, 0.6, {"note": "no_docs"}

        answer = " ".join([h["text"] for h in hits[:2]])  # keep short
        citations = [
            {
                "doc_id": h["doc_id"],
                "chunk": h["chunk"],
                "score": h["score"],
                "text": h["text"][:300]
            }
            for h in hits
        ]

        return {
            "answer": answer,
            "citations": citations,
            "_credits": 5
        }, 0.75, {"top_k": k}
