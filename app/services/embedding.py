from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    device='cpu',
)


def get_embedding(text: str) -> list:
    return model.encode(text, convert_to_tensor=False, normalize_embeddings=True).tolist()


def get_embeddings(texts: list[str]) -> list:
    return model.encode(texts, convert_to_tensor=False, normalize_embeddings=True).tolist()
