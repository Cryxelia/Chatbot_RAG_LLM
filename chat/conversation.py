from .models import Conversation, Message, ConversationContext
import uuid
from django.http import JsonResponse
import re
from django.db.models import Count
from django.views.decorators.http import require_POST

def get_user_conversations(request):
    #Returns the user's active (not archived) conversations.
    conversations = []

    if request.user.is_authenticated:
        qs = (Conversation.objects.filter(user=request.user, is_archived=False).annotate(msg_count=Count("messages")).filter(msg_count__gt=0).order_by("-updated_at"))
        for conv in qs:
            last_msg = conv.messages.order_by("-created_at").first()
            conversations.append({
                "id": str(conv.id),
                "title": conv.title or (last_msg.content[:50] if last_msg else "Ny konversation"),
                "last_message": last_msg.content if last_msg else None,
                "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
    else:
        temp_ids = request.session.get("chat_ids", []) # Anonymous conversations via session

        qs = (
            Conversation.objects
            .filter(id__in=temp_ids)
            .annotate(msg_count=Count("messages"))
            .filter(msg_count__gt=0)
            .order_by("-updated_at")
        )

        for conv in qs:
            last_msg = conv.messages.order_by("-created_at").first()

            conversations.append({
                "id": str(conv.id),
                "title": conv.title or (last_msg.content[:50] if last_msg else "Ny konversation"),
                "last_message": last_msg.content if last_msg else None,
                "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "message_count": conv.messages.count(),
                "is_shared": conv.is_shared,
                "created_at": conv.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

    conversations.sort(key=lambda x: x["updated_at"], reverse=True)

    return JsonResponse({"conversations": conversations})


def get_conversation_messages(request, chat_id):
    # Retrieves all messages for a specific conversation.
    conversation = (
        Conversation.objects
        .prefetch_related("messages")
        .filter(id=chat_id)
        .first()
    )

    if not conversation:
        return JsonResponse({"messages": []})

    if not check_conversation_access(conversation, request):
        return JsonResponse({"error": "Access denied"}, status=403)

    messages = [
        {
            "user": msg.role,
            "message": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for msg in conversation.messages.all()
    ]

    return JsonResponse({"messages": messages, "is_archived": conversation.is_archived})


def check_conversation_access(conversation, request, write=False):
    if conversation.is_shared and not write:
        return True

    if conversation.user_id:
        allowed = request.user.is_authenticated and conversation.user_id == request.user.id
        return allowed

    allowed = (
        bool(request.session.session_key)
        and conversation.session_key == request.session.session_key
    )

    return allowed

def clone_conversation(source, new_user):
    #  Creates a fork (clone) of an existing conversation,including messages and context.
    clone = Conversation.objects.create(
        user=new_user if new_user and new_user.is_authenticated else None,
        parent=source.parent,
        fork_depth=source.fork_depth + 1,
        is_shared=False,
        title=source.title,
    )

    messages = [
        Message(
            conversation=clone,
            role=msg.role,
            content=msg.content
        )
        for msg in source.messages.all()
    ]
    Message.objects.bulk_create(messages)

    ctx = getattr(source, "context", None)

    ConversationContext.objects.create(
        conversation=clone,
        domain=ctx.domain if ctx else "general",
        subdomain=ctx.subdomain if ctx else "",
        purpose=ctx.purpose if ctx else "conversation",
        assumptions=ctx.assumptions if ctx else {},
        summary=ctx.summary if ctx else "",
    )
        
    return clone

@require_POST
def archive_conversation(request, chat_id):
    # Archives a conversation for the logged in user.
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Åtkomst nekad"}, status=401)

    conversation = Conversation.objects.filter(id=chat_id, user=request.user).first()

    if not conversation or not check_conversation_access(conversation, request):
        return JsonResponse({"error": "Åtkomst nekad"}, status=403)

    conversation.is_archived = True
    conversation.save(update_fields=["is_archived"])

    return JsonResponse({"success": True})

@require_POST
def delete_conversation(request, chat_id):
    # Permanently deletes a conversation.
    conversation = Conversation.objects.filter(id=chat_id).first()

    if not conversation or not check_conversation_access(conversation, request):
        return JsonResponse({"error": "Åtkomst nekad"}, status=403)

    conversation.delete()
    return JsonResponse({"success": True})

@require_POST
def toggle_share_conversation(request, chat_id):
    # Turns sharing of a conversation on/off.
    conversation = Conversation.objects.filter(id=chat_id).first()

    if not conversation or not request.user.is_authenticated:
        return JsonResponse({"error": "Åtkomst nekad"}, status=403)

    conversation.is_shared = not conversation.is_shared
    conversation.save(update_fields=["is_shared"])

    return JsonResponse({
        "shared": conversation.is_shared,
        "share_url": f"/chat/{conversation.id}/" if conversation.is_shared else None
    })


def generate_unique_title(user, base_title):
    # Generates a unique conversation title per user.
    base = re.sub(r"\s+", " ", base_title.strip())[:40]

    qs = Conversation.objects.filter(user=user, title__startswith=base)


    if not qs.exists():
        return base
    
    counter = 2
    while True:
        candidate = f"{base} ({counter})" 
        if not  qs.filter(title=candidate).exists():
            return candidate
        counter += 1

def get_archived_conversations(request):
    #  Returns the user's archived conversations.
    conversations = []

    if request.user.is_authenticated:
        qs = (
            Conversation.objects.filter(user=request.user, is_archived=True)
            .annotate(msg_count=Count("messages"))
            .filter(msg_count__gt=0)
            .order_by("-updated_at")
        )
        for conv in qs:
            last_msg = conv.messages.order_by("-created_at").first()
            conversations.append({
                "id": str(conv.id),
                "title": conv.title or (last_msg.content[:50] if last_msg else "Ny konversation"),
                "last_message": last_msg.content if last_msg else None,
                "updated_at": conv.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })

    return JsonResponse({"conversations": conversations})

@require_POST
def unarchive_conversation(request, chat_id):
    # Returns the user's archived conversations.
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Åtkomst nekad"}, status=401)

    conversation = Conversation.objects.filter(
        id=chat_id,
        user=request.user
    ).first()

    if not conversation:
        return JsonResponse({"error": "Åtkomst nekad"}, status=403)

    conversation.is_archived = False
    conversation.save(update_fields=["is_archived"])

    return JsonResponse({"success": True})
