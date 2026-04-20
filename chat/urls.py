from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import user_routes
from . import views
from . import conversation
from . import chat_helper

urlpatterns = [
    path("", views.home, name="home"),
    path("chat/<uuid:chat_id>/", views.chat_session, name="chat_with_id"),
    path("chat/", views.chat, name="chat"),

    # conversation and messages
    path("chat/get_user_conversations/", conversation.get_user_conversations, name="get_user_conversations"),
    path("chat/<uuid:chat_id>/messages/", conversation.get_conversation_messages, name="get_conversation_messages"),
    path("chat/<uuid:chat_id>/archive/", conversation.archive_conversation, name="archive_conversation"),
    path("chat/<uuid:chat_id>/delete/", conversation.delete_conversation, name="delete_conversation"),
    
    path("chat/get_archived_conversations/", conversation.get_archived_conversations, name="get_archived_conversations"),
    path("chat/<uuid:chat_id>/unarchive/", conversation.unarchive_conversation, name="unarchive_conversation"),

    # help functionns
    path("chat/<uuid:chat_id>/clear_history/",chat_helper.clear_conversation_history, name="clear_history"),

    # admin
    path("admin/refresh-vector-stores/", views.refresh_vector_store_ids, name="refresh_vector_stores"),  

    # Authentication
    path("register/", user_routes.register, name="register"),
    path("login/", user_routes.login, name="login"),
    path("logout/", user_routes.logout, name="logout") 
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
