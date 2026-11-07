import chromadb
from app.services.embedding import get_embedding, get_embeddings

client = chromadb.PersistentClient(path="./data/chroma_db")

def get_collection(course_id: str):
    return client.get_or_create_collection(name=f"course_{course_id}")

def delete_collection(course_id: str):
    try:
        client.delete_collection(name=f"course_{course_id}")
    except Exception:
        pass  # collection may not exist yet


def get_all_chunks(course_id: str) -> list[dict]:
    collection = get_collection(course_id)
    result = collection.get(where={"course_id": course_id}, include=["documents", "metadatas"])
    if not result["documents"]:
        return []
    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(result["documents"], result["metadatas"])
    ]


def delete_chunks_by_doc(course_id: str, doc_name: str):
    try:
        collection = get_collection(course_id)
        collection.delete(where={"doc_name": doc_name})
    except Exception:
        pass


_EMBED_BATCH = 500


def add_chunks(collection, chunks, progress_callback=None):
    if not chunks:
        print("⚠️ 没有提取到有效文本")
        return

    total = len(chunks)
    print(f"🔄 正在生成向量... 共 {total} 个文本块")
    done = 0
    for i in range(0, total, _EMBED_BATCH):
        batch = chunks[i:i + _EMBED_BATCH]
        texts = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        ids = [c["metadata"]["chunk_id"] for c in batch]
        embeddings = get_embeddings(texts)
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        done += len(batch)
        if progress_callback:
            progress_callback(done, total)

    print(f"✅ 向量存入完成！课程ID: {chunks[0]['metadata']['course_id']}")