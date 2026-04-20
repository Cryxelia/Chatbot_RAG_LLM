from django.db import models
from django.contrib.auth.models import User
import uuid

class Conversation(models.Model):
    """
    Represents a chat conversation.

    A conversation can:
    - belong to a logged in user
    - be anonymous (linked to session_key)
    - be a fork of another conversation
    - be archived or shared
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE,  null=True, blank=True)
    parent = models.ForeignKey("self",null=True,blank=True,on_delete=models.SET_NULL,related_name="forks")
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True)
    is_shared = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    fork_depth = models.PositiveSmallIntegerField(default=0) # Depth of the fork tree (for limiting/sorting)


    class Meta:
        db_table = "chat_conversation"
        ordering = ['-created_at']
        indexes =  [
            models.Index(fields=["user"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["parent", "fork_depth"]), 
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title"],
                name="unique_title_per_user"
            )
        ]
    
    def __str__(self):
        return f"Conversation {self.id} ({self.user})"

class Message(models.Model): # a single message in a conversation
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]
    conversation = models.ForeignKey(Conversation, related_name="messages",  on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    class Meta:
        db_table = "chat_message"
        ordering = ['created_at']
        indexes =  [
            models.Index(fields=["conversation"])
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class RagState(models.Model):
    """
    Global RAG state shared between all workers

    Used to store:
    - vector store IDs
    - other global metadata for the RAG pipeline
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_state"

    def __str__(self):
        return self.key
    

class RagFileState(models.Model):
    """
    Metadata for files used in the RAG system.

    Used to:
    - avoid indexing the same file multiple times
    - track chunk information per file
    """
    filename = models.CharField(max_length=255, unique=True)
    file_hash = models.CharField(max_length=64)
    chunks = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_file_state"

class ConversationContext(models.Model):
    """
    Summarized context object for a conversation.

    Used for:
    - context compression
    - RAG
    - memory management between messages
    """

    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="context")
    domain = models.CharField(max_length=150)
    subdomain = models.CharField(max_length=150, blank=True)
    purpose = models.CharField(max_length=200, blank=True)
    assumptions  = models.JSONField(default=dict) 
    summary = models.TextField(blank=True)
    context_version = models.PositiveIntegerField(default=1)


    updated_at = models.DateTimeField(auto_now=True)

    class Meta: 
        db_table = "chat_conversation_context"

    
    def __str__(self):
        return f"Context for {self.conversation_id}"
    

class ConversationContextVersion(models.Model):
    """
    versions of conversation context.

    Enables:
    - rollback
    - analysis
    - comparison between context changes
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="context_versions")
    version = models.PositiveIntegerField()
    summary = models.TextField(blank=True)
    domain = models.CharField(max_length=150)
    subdomain = models.CharField(max_length=150, blank=True)
    purpose = models.CharField(max_length=200, blank=True)
    assumptions  = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_conversation_context_version"
        ordering = ['-version']
        unique_together = ("conversation", "version")

class UserLongTermMemory(models.Model):
    """
    Long-term memory per user.

    Used to:
    - preserve overall context between conversations
    - customize responses over time
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="long_term_memory")
    context_summary = models.TextField(default="", blank=True)
    assumptions = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "long_term_memory"

    def add_summary(self, new_summary):
        if self.context_summary:
            self.context_summary += "\n" + new_summary
        else:
            self.context_summary = new_summary
        self.save()
