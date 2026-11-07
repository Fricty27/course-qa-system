from rank_bm25 import BM25Okapi
from app.services.vector_store import get_collection, get_all_chunks
from app.services.embedding import get_embedding
from app.services.llm import generate_answer
from app.services.reranker import rerank


def semantic_search(query: str, course_id: str, top_k: int = 10) -> list[dict]:
    collection = get_collection(course_id)
    query_emb = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where={"course_id": course_id}
    )

    output = []
    for doc, meta, score in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        output.append({
            "text": doc,
            "page_num": meta["page_num"],
            "doc_name": meta["doc_name"],
            "score": float(score),
        })
    return output


def hybrid_search(query: str, course_id: str, top_k: int = 10) -> list[dict]:
    """BM25 关键词检索 + 语义检索，用 RRF 合并，解决生僻术语召回失效问题。"""
    all_chunks = get_all_chunks(course_id)
    if not all_chunks:
        return semantic_search(query, course_id, top_k=top_k)

    # BM25：逐字符分词（无需额外依赖，对中文技术术语精确匹配效果好）
    tokenized_corpus = [list(c["text"]) for c in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(list(query))
    bm25_order = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

    # 语义检索
    sem_results = semantic_search(query, course_id, top_k=20)

    # RRF 合并（k=60 为标准取值）
    candidates: dict[str, dict] = {}

    for rank, idx in enumerate(bm25_order[:20]):
        c = all_chunks[idx]
        key = c["text"]
        if key not in candidates:
            candidates[key] = {
                "text": c["text"],
                "page_num": c["metadata"]["page_num"],
                "doc_name": c["metadata"]["doc_name"],
                "score": 0.0,
            }
        candidates[key]["score"] += 1.0 / (60 + rank + 1)

    for rank, r in enumerate(sem_results):
        key = r["text"]
        if key not in candidates:
            candidates[key] = {**r, "score": 0.0}
        candidates[key]["score"] += 1.0 / (60 + rank + 1)

    return sorted(candidates.values(), key=lambda x: x["score"], reverse=True)[:top_k]


def ranked_search(query: str, course_id: str) -> list[dict]:
    chunks = hybrid_search(query, course_id, top_k=10)
    return rerank(query, chunks, top_k=3)


def rag_answer(question: str, course_id: str) -> dict:
    chunks = ranked_search(question, course_id)
    if not chunks:
        return {"answer": "", "sources": [], "chunks": []}

    answer = generate_answer(question, chunks)
    sources = [{"doc_name": c["doc_name"], "page_num": c["page_num"]} for c in chunks]
    return {"answer": answer, "sources": sources, "chunks": chunks}
