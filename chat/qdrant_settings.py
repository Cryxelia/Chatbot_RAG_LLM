from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance
from django.conf import settings
from openai import OpenAI
import logging
import time
import os


logger = logging.getLogger("rag")

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")
HOST = QDRANT_URL.replace("https://", "").replace("http://", "") # remove http:// and https:// from the URL 


qdrant_client =  QdrantClient( #Initializes Qdrant client via REST
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=False,
)

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def create_collection(collection_name, dim):
    from .help_functions import retry_api_call
    def _create():      # _ means its a protected function and shouldn't be used outside it's context
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config = VectorParams(size=dim, distance=Distance.COSINE), # Checking if the dimensions match
            timeout=60
        )
        logger.info(f"Collection '{collection_name}' skapad.")
        return True

    return retry_api_call(_create, retries=5)

def get_embedding(text, model="text-embedding-3-small"):
    """
        creates embedding via OpenAI
    """
    from .help_functions import retry_api_call

    def _call_embedding():
        return openai_client.embeddings.create(model=model, input=text).data[0].embedding

    try:
        emb = retry_api_call(_call_embedding, retries=5)
        if emb is None:
            logger.error("Embedding misslyckades efter retries.")
        return emb
    except Exception as e:
        logger.error(f"Fel vid embedding: {e}")
        return None


def init_collection():
    test_emb = get_embedding("dimension check") # dynamically determine embedding dimension
    if not test_emb:
        raise ValueError("Embedding misslyckades vid initiering av collection!")
    
    dim = len(test_emb)
    
    existing_collections = [c.name for c in qdrant_client.get_collections().collections] # Get all existing collections

    if QDRANT_COLLECTION not in existing_collections:
        create_collection(QDRANT_COLLECTION, dim)

        for _ in range(10):       # Waiting until Qdrant has registered the vector field correctly
            info = qdrant_client.get_collection(QDRANT_COLLECTION)
            vectors_info = info.config.params.vectors

            # A protection against Qdrant being able to return different formats depending on version
            if isinstance(vectors_info, dict) and "vector" in vectors_info:
                break
            elif isinstance(vectors_info, VectorParams):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Vector field 'vector' registrerades inte på servern!")

    
    # Final verification of dimension
    info = qdrant_client.get_collection(QDRANT_COLLECTION)
    
    vectors_info = info.config.params.vectors
    if isinstance(vectors_info, dict):
        stored_dim = list(vectors_info.values())[0].size
    elif isinstance(vectors_info, VectorParams):
        stored_dim = vectors_info.size
    else:
        raise ValueError("Okänt format på vectors")

    if stored_dim != dim:
        raise ValueError(f"Dimension mismatch! Collection={stored_dim}, Embedding={dim}")
    
    return QDRANT_COLLECTION


