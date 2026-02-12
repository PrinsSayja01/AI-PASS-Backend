from rag_mvp.chunk import chunk_text
from rag_mvp.index import RAGIndex

doc = "AI-Pass is a marketplace. It has skills, sandbox, governance, RAG, and billing. " * 20

chunks = chunk_text(doc, chunk_words=60)
metas = [{"doc_id":"doc1","chunk":i} for i in range(len(chunks))]

idx = RAGIndex()
idx.add(chunks, metas)

q = "What is AI-Pass?"
print(idx.search(q, k=3))
