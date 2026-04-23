import datetime
import json
import logging
from .models import Conversation, Message, ConversationContext, ConversationContextVersion, UserLongTermMemory, RagState
from .conversation import generate_unique_title, check_conversation_access
from .help_functions import update_context_summary, retry_api_call
from .system_instructions import BASE_SYSTEM_PROMPT
from .chunking import count_tokens
from markdown2 import markdown
import re
from .rag import get_relevant_chunks
from django.conf import settings
from .rag_state import get_or_lock_vector_store_state
from django.db import transaction
from django.http import JsonResponse

logger = logging.getLogger("rag")

MAX_CONTEXT_TOKENS = 6000
MAX_HISTORY_TOKENS = 10000
MAX_MESSAGES = 200
MAX_SESSION_CHAT_IDS = 10
VECTOR_STORE_KEY = "vector_store_ids"


def to_date_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def refresh_vector_store(force_refresh=False):
    """This function calls all the functions in rag.py
    and Initiates vector stores"""
    from .rag import upload_rag_files_to_vector_store

    state = get_or_lock_vector_store_state()
    with transaction.atomic():
        state = RagState.objects.select_for_update().get_or_create(
            key=VECTOR_STORE_KEY,
            defaults={"value": []}
        )[0]
    
    if force_refresh or not state.value:
        try:
            collection_name = upload_rag_files_to_vector_store(force_refresh=force_refresh)
            state.value = [collection_name] if collection_name else []
            state.save(update_fields=["value", "updated_at"])
        except Exception as e:
            logger.exception("Misslyckades att initiera vector store")
            raise RuntimeError("Kunde inte initiera vector store") from e

    return state.value


def get_openai_client():
    # Returns an instance of the OpenAI client.
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY saknas!")
    from openai import OpenAI
    return OpenAI(api_key=api_key)

def add_history_to_messages(messages, chat_history, max_history_tokens=MAX_HISTORY_TOKENS, max_messages=MAX_MESSAGES):
    # Adds history to the message list without exceeding token limits.
    total_tokens = 0
    for msg in reversed(chat_history[-max_messages:]):
        role = msg.get("role")
        content = msg.get("content")
        if not role or not content:
            continue
        token_count = count_tokens(content)
        if max_history_tokens is not None and total_tokens + token_count > max_history_tokens:
            break
        messages.insert(1, {"role": role, "content": content})
        total_tokens += token_count

def ai_response_to_message(ai_text, role="assistant"):
    # Converts AI text to HTML and returns in standard format
    html = markdown(
        ai_text,
        extras=["fenced-code-blocks", "tables", "strike", "cuddled-lists", "break-on-newline"]
    )
    html = re.sub(r'【(\d+:\d+)†source】', r'<sup aria-label="Source \1">[\1]</sup>', html)
    return {'created_at': to_date_time(), 'user': role, 'message': html}

def prune_conversation_messages(conversation, max_messages=200, delete_oldest=20):
    # Deletes older messages if max_messages is exceeded.
    qs = conversation.messages.order_by("created_at")
    count = qs.count()
    if count > max_messages:
        oldest_ids = qs.values_list('id', flat=True)[:delete_oldest]
        conversation.messages.filter(id__in=list(oldest_ids)).delete()
        logger.info(f"Rensade {len(oldest_ids)} gamla meddelanden från konversation {conversation.id}")


def get_or_create_conversation(request, chat_id=None):

    conversation = None

    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()

    if chat_id:
        conversation = Conversation.objects.filter(id=chat_id).first()
        if not conversation:
            return None, {"error": "Konversationen hittades inte"}, 404

        if not check_conversation_access(conversation, request):
            return None, {"error": "Åtkomst nekad"}, 403

    if not conversation and request.method == "POST":
        conversation = Conversation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=None if request.user.is_authenticated else request.session.session_key
        )

        ConversationContext.objects.create(
            conversation=conversation,
            domain="general",
            purpose="conversation",
            assumptions={},
            summary=""
        )

        if not request.user.is_authenticated:
            chat_ids = request.session.get("chat_ids", [])
            chat_ids.insert(0, str(conversation.id))
            request.session["chat_ids"] = chat_ids[:MAX_SESSION_CHAT_IDS]
            request.session.modified = True
            request.session.save()

    return conversation, None, None

def append_user_message(conversation, user_message):
    # Adds a message from the user and updates title/updated_at
    Message.objects.create(conversation=conversation, role="user", content=user_message)
    if not conversation.title:
        conversation.title = generate_unique_title(conversation.user, user_message)
        conversation.save(update_fields=["title"])
    conversation.save(update_fields=["updated_at"])

def append_ai_message(conversation, ai_message):
    # Adds the AI's response as a message
    Message.objects.create(conversation=conversation, role="assistant", content=ai_message.get("message", ""))

def update_conversation_context(conversation, user_message, ai_message):
    if hasattr(conversation, "context"):
        with transaction.atomic():
            ctx = ConversationContext.objects.select_for_update().get(conversation=conversation)

            logger.warning(
                "CTX UPDATE | conv_id=%s | current_version=%s",
                conversation.id,
                ctx.context_version,
            )

            ConversationContextVersion.objects.create(
                conversation=conversation,
                version=ctx.context_version,
                summary=ctx.summary,
                domain=ctx.domain,
                subdomain=ctx.subdomain,
                purpose=ctx.purpose,
                assumptions=ctx.assumptions
            )

            ctx.summary = update_context_summary(ctx.summary, user_message, ai_message.get("message", ""))
            ctx.context_version += 1
            ctx.save(update_fields=["summary", "context_version", "updated_at"])

def build_base_messages(conversation, chat_history=None, ltm=None):
    # Creates basic messages for AI with system prompts and history.
    messages = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]
    user = getattr(conversation, "user", None)

    if ltm and ltm.context_summary:
        messages.append({
            "role": "system",
            "content": f"Du minns följande om användaren:\n- Sammanfattning: {ltm.context_summary}\n- Antaganden: {json.dumps(ltm.assumptions)}\nHåll dig konsekvent till detta."
        })

    ctx = getattr(conversation, "context", None)
    if ctx:
        messages.append({"role": "system", "content": f"Du befinner dig i följande kontext för denna konversation:\n- Domän: {ctx.domain}\n- Subdomän: {ctx.subdomain}\n- Syfte: {ctx.purpose}\n- Antaganden: {ctx.assumptions}\n- Sammanfattning hittills: {ctx.summary}\n\nHåll dig konsekvent till detta."})
    if chat_history:
        add_history_to_messages(messages, chat_history)
    return messages

def append_rag_context(messages, question):
    # Adds RAG context to messages based on the query."
    all_chunks = get_relevant_chunks(question)
    if all_chunks:
        context, total_tokens = "", 0
        used_chunks = 0
        for chunk in all_chunks:
            chunk_text = chunk["text"]
            chunk_tokens = count_tokens(chunk_text)
            if MAX_CONTEXT_TOKENS and total_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
                break
            context += "\n\n" + chunk_text
            total_tokens += chunk_tokens
            used_chunks += 1

        logger.info(f"chunks_used={used_chunks} | total_tokens={total_tokens}")
        messages.append({"role": "system", "content": "Använd endast följande kontext för att svara korrekt."})
        messages.append({"role": "user", "content": f"KONTEKST:\n{context}\n\nFRÅGA:\n{question}"})
    else:
        messages.append({"role": "system", "content": "Ingen extern kontext hittades, svara utifrån min tidigare konversation och kunskap."})
        messages.append({"role": "user", "content": question})
    return messages

def call_openai(messages, model="gpt-4o-mini", temperature=0.3, top_p=1):
    # Calling OpenAI API with retry
    def inner_call():
        client = get_openai_client()
        return client.responses.create(model=model, input=messages, temperature=temperature, top_p=top_p)
    return retry_api_call(inner_call)

def get_ai_response_modular(question, conversation, chat_history=None):
    # Handles the entire AI response including RAG and LTM.
    user = getattr(conversation, "user", None)
    ltm = None
    if user:
        ltm, _ = UserLongTermMemory.objects.get_or_create(user=user)

    messages = build_base_messages(conversation, chat_history)  

    messages = append_rag_context(messages, question)

    if ltm and ltm.context_summary:
        messages.insert(-1, {  
            "role": "system",
            "content": f"Observera att du minns följande om användaren:\n- Sammanfattning: {ltm.context_summary}\n- Antaganden: {json.dumps(ltm.assumptions)}\nHåll dig konsekvent till detta."
        })

    try:
        response = call_openai(messages)
    except Exception:
        logger.exception("OpenAI API-anrop misslyckades")
        return {"message": "Jag har tekniska problem just nu. Försök igen om en stund."}

    text_output = getattr(response, "output_text", None) or "Fel: OpenAI kunde inte generera ett svar."

    if ltm:
        ltm.add_summary(f"Fråga: {question}\nSvar: {text_output}")

    return ai_response_to_message(text_output)


def clear_conversation_history(request, chat_id):
    # Clears history for a temporary conversation. (For anonymous session only.)
    chat_ids = request.session.get("chat_ids", [])
    chat_ids = [cid for cid in chat_ids if Conversation.objects.filter(id=cid).exists()]
    request.session["chat_ids"] = chat_ids
    if str(chat_id) not in chat_ids:
        return JsonResponse({"error": "Åtkomst nekad"}, status=403)

    conversation = Conversation.objects.filter(id=chat_id, user=None).first()
    if not conversation:
        return JsonResponse({"error": "Konversationen hittades inte"}, status=404)

    conversation.messages.all().delete()

    return JsonResponse({"success": True})