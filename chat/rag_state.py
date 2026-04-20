from .models import RagState
from django.utils import timezone
from django.db import transaction


VECTOR_STORE_KEY = "vector_store_ids"  # Constant key to identify vector store-state in the database

def get_vector_store_ids():
    # Retrieves current vector store-Ins from the database.
    try:
        state = RagState.objects.get(key=VECTOR_STORE_KEY)
        return state.value
    except RagState.DoesNotExist:
        return []

def set_vector_store_ids(ids):
    # Saves or updates vector store IDs in the database.
    RagState.objects.update_or_create(
        key=VECTOR_STORE_KEY,
        defaults={"value": ids, "updated_at": timezone.now()}
    )

def get_or_lock_vector_store_state():
    # Retrieves and locks the vector store state for safe updating and to avoid parallel updates vector store
    with transaction.atomic():
        state, _ = RagState.objects.select_for_update().get_or_create(
            key=VECTOR_STORE_KEY,
            defaults={"value": []}
        )
        return state