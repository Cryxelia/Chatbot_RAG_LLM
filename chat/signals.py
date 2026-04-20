# signals.py
from django.contrib.sessions.models import Session
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Conversation

@receiver(pre_delete, sender=Session)
# automatically remove all conversation that dont have a user and are tied to the current session before the session ends
def cleanup_anonymous_conversations(sender, instance, **kwargs):
    Conversation.objects.filter(
        user=None,
        session_key=instance.session_key
    ).delete()
