from dotenv import load_dotenv
from django.conf import settings
import requests
from openai import OpenAI
import time
import logging
import os

logger = logging.getLogger("rag")

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")
VERIFY = "/etc/pki/tls/certs/ca-bundle.crt"  # CPanel cert bundle
HEADERS = {
    "Authorization": f"Bearer {QDRANT_API_KEY}",
    "Content-Type": "application/json"
}

INIT_DONE = False

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def create_collection(collection_name, dim):
    from .help_functions import retry_api_call

    def _create():     # _ means its a protected function and shouldn't be used outside it's context
        url = f"{QDRANT_URL}/collections/{collection_name}"
        payload = {
            "vectors": {
                "default": {"size": dim, "distance": "Cosine"}
            }
        }

        r = requests.put(url, json=payload, headers=HEADERS, verify=VERIFY)

        if r.status_code == 409:
            logger.info(f"Collection '{collection_name}' finns redan.")
            return True

        r.raise_for_status()
        logger.info(f"Collection '{collection_name}' skapad via REST.")
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

        if not isinstance(emb, list):
            emb = emb.tolist()  # om det är np.array
        if not all(isinstance(x, float) for x in emb):
            emb = [float(x) for x in emb]
        
        logger.info(f"Vector length: {len(emb)}")
        return emb
    except Exception as e:
        logger.error(f"Fel vid embedding: {e}")
        return None



def init_collection():
    global INIT_DONE, EMBEDDING_DIM

    if INIT_DONE:
        return QDRANT_COLLECTION, EMBEDDING_DIM  

    logger.info("Initierar Qdrant collection...")

    test_emb = get_embedding("dimension check") # Set dimension on vector
    if not test_emb:
        raise ValueError("Embedding misslyckades vid initiering av collection!")
    
    EMBEDDING_DIM = len(test_emb)
    
    create_collection(QDRANT_COLLECTION, EMBEDDING_DIM)

    r = requests.get(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}",
        headers=HEADERS,
        verify=VERIFY
    )

    r.raise_for_status()
    vectors_info = r.json()["result"]["config"]["params"]["vectors"]

    if isinstance(vectors_info, dict):
        stored_dim = list(vectors_info.values())[0]["size"]
    else:
        raise ValueError("Unknown format of vector")
   
    if stored_dim != EMBEDDING_DIM:
        raise ValueError(f"Dimension mismatch! Collection={stored_dim}, Embedding={EMBEDDING_DIM}")
    
    INIT_DONE = True
    
    return QDRANT_COLLECTION, EMBEDDING_DIM   

def query_vectors(vector, top_k=15):

    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search"

    if not vector:
        logger.error("query_vectors fick None vector")
        return []

    payload = {
        "vector": {
            "name": "default", 
            "vector": vector
        },
        "limit": top_k,
        "with_payload": True
    }

    try:
        r = requests.post(url, json=payload, headers=HEADERS, verify=VERIFY)

        try:
            r.raise_for_status()
        except Exception:
            logger.error(f"Qdrant search error: {r.status_code} {r.text}")
            return []

        result = r.json().get("result", [])

        points = []
        for item in result:
            point = {
                "id": item.get("id"),
                "payload": item.get("payload"),
                "score": item.get("score")  
            }
            points.append(point)

        logger.info(f"Search returnerade {len(points)} resultat")

        return points

    except Exception as e:
        logger.error(f"Fel vid query_vectors: {e}")
        return []