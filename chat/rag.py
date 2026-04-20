
import os
from .chunking import process_pdf_to_chunks
import datetime
from .help_functions import hash_chunk, load_file_state, save_file_state, compute_file_hash, retry_api_call
import logging
import time
from django.db import transaction

logger = logging.getLogger("rag")

def batch_upsert(collection_name, vectors, batch_size=200):
    """
        This function handels vectors before sending them to the database
        it also ends  the vectors in batches
    """
    from .qdrant_settings import  qdrant_client

    vectors = [v for v in vectors if v.get("vector") is not None]
    if not vectors:
        return
    
    dim = len(vectors[0]["vector"]) # checking the  diim on the vectors
    for v in vectors:
        if len (v["vector"]) != dim:
            raise ValueError(f"Embedding-dimension mismatch! Förväntad {dim}, fick {len(v['vector'])}")

    for i in range(0, len(vectors), batch_size): # uppload to qdrant in batches
        batch = vectors[i:i+batch_size]
        for v in batch:
            logger.info("Upsertar dokument:", v.get("payload"))

        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True
            )
        except Exception as e:
            logger.error(f"Fel vid batch-upsert: {e}")

@transaction.atomic
def upload_rag_files_to_vector_store(folder=None,  force_refresh=False):
    from .qdrant_settings import get_embedding, init_collection, qdrant_client, VectorParams

    try:
        collection_name = init_collection()
        

        for _ in range(10):  
            info = qdrant_client.get_collection(collection_name)
            vectors_info = info.config.params.vectors
            if isinstance(vectors_info, dict) and "vector" in vectors_info:
                break
            elif isinstance(vectors_info, VectorParams):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Vector field 'vector' registrerades inte på servern!")

        # Default folder if none given
        if folder is None:
            folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"pdf_files")
        if not os.path.exists(folder):
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

                if file_state[filename]["file_hash"] == file_hash:
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

                        file_state[filename]["chunks"][chunk_id] = {
                            "embedding": embedding,
                            "text": chunk["text"],
                            "timestamp": str(datetime.datetime.now())
                        }

                    vectors.append({
                        "id" : chunk_id,
                        "vector": embedding,
                        "payload": {
                            "file" : filename,
                            "text" : chunk["text"],
                            "source_pdf" : chunk["source_pdf"],
                            "page_number": chunk["page_number"], 
                            "timestamp": str(datetime.datetime.now())
                        }
                    })
                
                # Upsert to Qdrant in batches
                batch_size = 200
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i+batch_size]
                    retry_api_call(qdrant_client.upsert, collection_name=collection_name, points=batch, retries=5)
                    
                    for r in batch: 
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



def get_relevant_chunks(question, top_k=15):
    """
        creates an embeddinhg of the question and search in the database for similar chunks
        returns a list with text
    """
    from .qdrant_settings import init_collection, get_embedding, qdrant_client
    try:
        collection_name = init_collection()
        if not collection_name:
            logger.error("Ingen collection hittad!")
            return []
            
        info = qdrant_client.get_collection(collection_name)
        if info.points_count == 0:
            logger.warning("Collection är tom – inga vektorer att söka i.")
            return []

        query_vector = get_embedding(question)
        if query_vector is None:
            logger.error("Embedding för frågan misslyckades")
            return []
    
        search_result = qdrant_client.query_points( 
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        chunks = [
            {
                "text": point.payload.get("text"),
                "source_pdf": point.payload.get("source_pdf")  
            }
            for point in search_result.points
            if point.payload and "text" in point.payload
        ]
        return chunks
    except Exception as e:
        logger.error(f"Fel vid sökning i vector store: {e}")
        return []


def validate_vector_store_ids(vector_store_ids):
    """Validate vector store IDs and remove all invalid IDs"""
    if not isinstance(vector_store_ids, list):
        logger.error("validate_vector_store_ids: vector_store_ids är inte en lista.")
        return []

    clean_ids = [vid for vid in vector_store_ids if isinstance(vid, str) and vid.strip()]
    return clean_ids