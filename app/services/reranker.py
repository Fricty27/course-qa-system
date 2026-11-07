from sentence_transformers import CrossEncoder

_model = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder('BAAI/bge-reranker-base', device='cpu')
    return _model


def rerank(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    if not chunks:
        return chunks
    pairs = [(query, c['text']) for c in chunks]
    scores = _get_model().predict(pairs)
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [c for _, c in ranked[:top_k]]
