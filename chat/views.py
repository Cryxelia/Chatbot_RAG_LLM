from django.shortcuts import render, redirect
from django.http import JsonResponse
from .questions import questions
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from .chat_helper import (
    get_or_create_conversation,
    append_user_message,
    append_ai_message,
    update_conversation_context,
    prune_conversation_messages,
    get_ai_response_modular,
    to_date_time,         
    refresh_vector_store 
)
import logging

logger = logging.getLogger("rag")

@require_POST
@staff_member_required #Forces and updates vector store (admin/staff only).
def refresh_vector_store_ids(request):
    ids = refresh_vector_store(force_refresh=True)
    return JsonResponse({"vector_store_ids": ids, "count": len(ids)})

def home(request): # Redirect from start to chat
    return redirect('chat')

def chat(request, chat_id=None): 
    return chat_session(request, chat_id)

def chat_session(request, chat_id=None): 
    """Main view and handles chat sessions, supporting both temporary and saved conversations."""
    # Get or create conversation based on user + chat_id
    conversation, error, status = get_or_create_conversation(request, chat_id)
    if error:
        return JsonResponse(error, status=status)

    # Recives  the user message
    if request.method == "POST":
        try:
            user_message = request.POST.get("message", "").strip()
            if not user_message:
                return JsonResponse({"error": "Tomt meddelande"}, status=400)

            append_user_message(conversation, user_message) # Save the user's message in the database

            # Makes history
            history = conversation.messages.order_by("created_at")
            chat_history = [{"role": msg.role, "content": msg.content} for msg in history]

            # calls ai-modell
            try:
                    ai_message = get_ai_response_modular(
                        user_message,
                        conversation=conversation,
                        chat_history=chat_history
                    )
            except Exception:
                    ai_message = {"message": "Något gick fel. Försök igen."}

            # Saves ai message
            append_ai_message(conversation, ai_message)
            update_conversation_context(conversation, user_message, ai_message)

            prune_conversation_messages(conversation)
            conversation.save(update_fields=["updated_at"])

            timestamp = to_date_time()

        # return JSON to frontend
            return JsonResponse({
                "chat_id": str(conversation.id),
                "user_message": {
                    "role": "user",
                    "content": user_message,
                    "created_at": timestamp
                },
                "ai_message": {
                    "role": "assistant",
                    "content": ai_message.get("message", ""),
                    "created_at": timestamp
                }
            })
        except Exception:
                logger.exception(
                    "POST /chat/ kraschade | chat_id=%s | conv_id=%s",
                    chat_id,
                    conversation.id if conversation else None,
                )
                return JsonResponse({"error": "Internt serverfel"}, status=500)
        
    # Render chat page
    history = conversation.messages.order_by("created_at") if conversation else []
    return render(request, "chat.html", {
        "history": history,
        "chat_id": str(conversation.id) if conversation else None,
        "questions": questions,
    })



