# backend/models.py

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Create and store the embed model
embed_model = HuggingFaceEmbedding(model_name="hiieu/halong_embedding")

def get_embed_model():
    return embed_model
