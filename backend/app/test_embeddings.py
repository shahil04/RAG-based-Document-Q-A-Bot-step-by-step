from app.rag.embeddings import get_embedding_model


embedding_model = get_embedding_model()

text = "FastAPI is a modern Python web framework."

vector = embedding_model.embed_query(text)

print("Vector length:", len(vector))
print("First 10 values:")
print(vector[:10])