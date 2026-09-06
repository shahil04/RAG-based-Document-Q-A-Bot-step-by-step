from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import HF_TOKEN


def get_embedding_model():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs=(
            {"token": HF_TOKEN}
            if HF_TOKEN
            else {}
        )
    )

    return embeddings