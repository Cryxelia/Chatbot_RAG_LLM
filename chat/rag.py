import requests
import uuid
import os
from .chunking import process_pdf_to_chunks
import datetime
from .help_functions import hash_chunk, load_file_state, save_file_state, compute_file_hash, retry_api_call, STATE_FILE
import logging
from .qdrant_settings import init_collection, QDRANT_URL, HEADERS, VERIFY, query_vectors

logger = logging.getLogger("rag")

VECTOR_STORE_NAME = "rag_store"
VECTOR_STORE_NAMESPACE = "pdf_chunks"
EMBEDDING_DIM = None

def upsert_vectors(collection_name, vectors):
    """Upsert vectors via REST"""
    if not vectors:
        return

    url = f"{QDRANT_URL}/collections/{collection_name}/points?wait=true"
    payload = {"points": vectors}
    r = requests.put(url, json=payload, headers=HEADERS, verify=VERIFY)
    r.raise_for_status()
    logger.info(f"Upsert lyckades: {len(vectors)} vectors till {collection_name}")
    logger.debug(f"Qdrant response: {r.text}")
    return r.json()

def batch_upsert(collection_name, vectors, batch_size=50):
    """
        This function handels vectors before sending them to the database
        it also ends  the vectors in batches
    """

    vectors = [
        v for v in vectors 
        if v.get("vectors") and v["vectors"].get("default")
    ]
    if not vectors:
        logger.warning("Ingen vektor att upserta, hoppar över batch")
        return
    
    dim = len(vectors[0]["vectors"]["default"])

    for v in vectors:
        if len(v["vectors"]["default"]) != dim:
            raise ValueError(
                 f"Embedding-dimension mismatch! Förväntad {dim}, fick {len(v['vectors']['default'])}"
            )

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        for v in batch:
            logger.info(f"Upsertar dokument: {v.get('payload')}")

        try:
            retry_api_call(upsert_vectors, collection_name, batch, retries=5)
        except Exception as e:
            logger.error(f"Fel vid batch-upsert: {e}")



def upload_rag_files_to_vector_store(folder=None,  force_refresh=False):
    from .qdrant_settings import get_embedding, init_collection

    try:
        collection_name, embedding_dim = init_collection_safe()
        global EMBEDDING_DIM
        EMBEDDING_DIM = embedding_dim

        logger.info(f"Initierad collection: {collection_name}, embedding dimension: {EMBEDDING_DIM}")
        # Default folder if none given
        if folder is None:
            folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"pdf_files")
        if not os.path.exists(folder):
            logger.info(f"Sökväg för PDF: {folder}")
            logger.info(f"Filer i folder: {os.listdir(folder)}")
            return []
        
        file_state = load_file_state()

        uploaded_files= []

        # Loop through PDF files in folder
        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            if not filename.lower().endswith(".pdf") or not os.path.isfile(path):
                continue
            try:
                file_hash = compute_file_hash(path) # Skipping unmodified files using file hash
                if filename not in file_state:
                    file_state[filename] = {"file_hash": "", "chunks": {}}

                try:
                    save_file_state(file_state)
                    logger.info(f"State-fil sparad: {STATE_FILE}")
                except Exception as e:
                    logger.error(f"Misslyckades spara state-fil: {e}")

                if not force_refresh and file_state[filename]["file_hash"] == file_hash:
                    logger.info(f"{filename} har inte ändrats, hoppar över.")
                    continue

                # Process PDF into chunks
                chunks =  process_pdf_to_chunks(path)
                if not chunks:
                    continue    

                vectors = []
                for chunk in chunks:
                    chunk_id = hash_chunk(chunk["text"])
                    if chunk_id in file_state[filename]["chunks"]:
                        embedding = file_state[filename]["chunks"][chunk_id]["embedding"]
                    else:
                        embedding = retry_api_call(get_embedding, chunk["text"], retries=5)
                        if embedding is None:
                            logger.error(f"Embedding misslyckades för chunk: {chunk[:50]}...")
                            continue
                           
                        if not all(isinstance(x, float) for x in embedding):
                            embedding = [float(x) for x in embedding]

                        if len(embedding) != EMBEDDING_DIM:
                            logger.error(f"Embedding dimension mismatch: {len(embedding)} vs {EMBEDDING_DIM}")
                            continue
               
                        file_state[filename]["chunks"][chunk_id] = {
                            "embedding": embedding,
                            "text": chunk["text"],
                            "timestamp": str(datetime.datetime.now())
                        }

                    vectors.append({
                        "id" : chunk_id,
                        "vectors": {
                            "default": embedding
                        },
                        "payload": {
                            "file" : filename,
                            "text" : chunk["text"],
                            "source_pdf" : chunk["source_pdf"],
                            "page_number": chunk["page_number"], 
                            "timestamp": str(datetime.datetime.now())
                        }
                    })
                
                if not vectors:
                    logger.warning(f"Inga giltiga vectors skapades för fil: {filename}")
                else: 
                    # Upsert to Qdrant in batches
                    batch_upsert(collection_name, vectors)

                for r in vectors: 
                    logger.info(f"Returnerar dokument: {r['payload'].get('file')} - chunk id: {r['id']}") 

                uploaded_files.append(filename)

                file_state[filename]["file_hash"] = file_hash
                save_file_state(file_state)
            except Exception as e:
                logger.error(f"Fel vid processering av fil {filename}: {e}")
                continue
        
        logger.info(f"Qdrant collection '{collection_name}' uppdaterad.")
        return collection_name
    except Exception as e:
        logger.error(f"Fel vid upload till vector store: {e}")
        return None

def get_embedding_dim():
    global EMBEDDING_DIM
    if EMBEDDING_DIM is None:
        _, EMBEDDING_DIM = init_collection()
    return EMBEDDING_DIM

def init_collection_safe():
    from .qdrant_settings import init_collection

    collection_name, embedding_dim = init_collection()
    if not collection_name or not embedding_dim:
        raise RuntimeError("Initiering av Qdrant collection misslyckades!")
    return collection_name, embedding_dim

def get_relevant_chunks(question, top_k=15):
    """
    Creates an embedding of the question and searches in the Qdrant Cloud for similar chunks.
    Returns a list of dicts with 'text'.
    """
    from .qdrant_settings import init_collection, get_embedding, QDRANT_URL, HEADERS, VERIFY

    try:
        collection_name, EMBEDDING_DIM = init_collection_safe()
        if not collection_name:
            logger.error("Ingen collection hittad!")
            return []
        
        query_vector = get_embedding(question)
        if not query_vector or not isinstance(query_vector, list):
            logger.error(f"Felaktig embedding: {query_vector}")
            return []

        dim = get_embedding_dim()
        if not dim:
            logger.error("ingen dimension hittad")
            return None

        if len(query_vector) != dim:
            logger.error(f"Embedding dimension mismatch: {len(query_vector)} vs {dim}")
            
        dim = len(query_vector)
        if dim != EMBEDDING_DIM:
            logger.error(f"Embedding dimension mismatch: {dim} vs {EMBEDDING_DIM}")

        if len(query_vector) != EMBEDDING_DIM:
            logger.error("Query embedding dimension mismatch, skippar search")
            return []

        results = query_vectors(query_vector, top_k)

        chunks = [
            {"text": point.get("payload", {}).get("text")}
            for point in results
            if point.get("payload") and "text" in point.get("payload")
        ]
        return chunks

    except Exception as e:
        logger.error(f"Fel vid search i vector store: {e}")
        return []

def validate_vector_store_ids(vector_store_ids):
    """Validate vector store IDs and remove all invalid IDs"""
    if not isinstance(vector_store_ids, list):
        logger.error("validate_vector_store_ids: vector_store_ids är inte en lista.")
        return []

    clean_ids = [vid for vid in vector_store_ids if isinstance(vid, str) and vid.strip()]
    return clean_ids