from llama_index.vector_stores.weaviate import WeaviateVectorStore
import weaviate
from dotenv import load_dotenv
import os 

# Load environment variables from .env file
load_dotenv()

cluster_url = os.getenv("WEAVIATE_URL")
api_key = os.getenv("WEAVIATE_API_KEY")

weaviate_client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=weaviate.auth.AuthApiKey(api_key),
    skip_init_checks=True,
)

def get_weaviate_client () :
    return weaviate_client