import time
import random
import json
import hashlib
import os
import logging
from .models import RagFileState

logger = logging.getLogger("rag")

def retry_api_call(func, *args, retries=5, base_delay=1, max_delay=30, **kwargs):

    for attempt in range(1, retries + 1): # Loop  through the number of attempts
        try:
            return func(*args,  **kwargs) # Tries to run a funtcion 
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.error(f"[Retry] Nätverksfel: {e} (försök {attempt}/{retries})")
        
        except Exception as e:
            if "timeout" in  str(e).lower() or "connection" in  str(e).lower():
                logger.error(f"[Retry] API-fel: {e} (försök {attempt}/{retries})")
            else:
                raise
        
        # Increase the wait time after each attempt
        sleep_time = min(max_delay,  base_delay * (2 ** (attempt - 1)))
        sleep_time += random.uniform(0, 1.0)  # Add a little random variation to avoid competition for resources 
        logger.info(f"Sover i {sleep_time:.2f} sekunder innan retry...")    
        time.sleep(sleep_time)

    raise RuntimeError(f"Misslyckades efter {retries} försök.")


def hash_chunk(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()  # create hash of text to check for changes in the chunks


def compute_file_hash(path):
    """
        Save pdf document to hash (MD5-hash)
        The hash reprsents the  content of the file
        And see what has changed
    """
    try:
        hasher = hashlib.md5()
        # Reading file in binary format
        with open(path, "rb") as  f:
            while chunk := f.read(8192): #  read file in chunks 
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Kunde inte beräkna hash för {path}: {e}")
        raise


def load_file_state():
    """
        checking if the file's status and see if it has changed
        Use global cache (IN_MEMORY_FILE_STATE) 
        The file status contains information about previously uploaded files
    """
    try:
        state = {}
        for obj in RagFileState.objects.all():
            state[obj.filename] = {
                "file_hash": obj.file_hash,
                "chunks": obj.chunks or {}
            }
        return state
    except Exception as e:
        logger.error(f"Kunde inte läsa state-fil: {e}")
        return {}
    


def save_file_state(state):
    """
        save the current state to global cache and Saves the current file status to both disk and global cache.
        
    """
    try:
        for filename, data in state.items():
            RagFileState.objects.update_or_create(
                filename=filename,
                defaults={
                    "file_hash": data["file_hash"],
                    "chunks": data["chunks"]
                }
            )
    except Exception as e:
        logger.error(f"Kunde inte spara state-fil: {e}")
        raise

def update_context_summary(old_summary, user_msg, ai_msg, max_chars=1500):
    # Updates a running summary of the conversation's context. used for context compression, RAG prompting and memory management over longer conversations

    new_piece = f"User: {user_msg}\nAssistant: {ai_msg}"
    combined = (old_summary + "\n" + new_piece).strip()

    if len(combined) <= max_chars:
        return combined

    return combined[-max_chars:]
