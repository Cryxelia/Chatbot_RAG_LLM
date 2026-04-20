from django.contrib.auth.models import User
from django.db import transaction
from .models import Conversation
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth import logout as django_logout
import json
from django.shortcuts import render, redirect


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            return render(request, "register.html", {
                "error": "Fyll i alla fält"
            })

        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {
                    "error": "Användaren finns redan"
                })


        new_user = User.objects.create_user(
            username=username,
            password=password
        )
        return redirect("login")

    return render(request, "register.html")


def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
    
        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "login.html", {
                "error": "Fel användarnamn eller lösenord"
            })

        django_login(request, user)
        return redirect("chat")

    return render(request, "login.html")


def logout(request):
    if request.method == "POST":
        django_logout(request)
    return redirect("login")

def migrate_anonymous_chats_to_user(request, user):
    # if an anonymous user register, all the chats automatically saved in the new profile
    chat_ids = request.session.get("chat_ids", [])

    if not chat_ids:
        return 

    with transaction.atomic():
        conversations = (
            Conversation.objects
            .select_for_update()
            .filter(id__in=chat_ids, user=None)
        )

        for conv in conversations:
            conv.user = user
            conv.save(update_fields=["user", "updated_at"])

            ctx = getattr(conv, "context", None)
            if ctx:
                ctx.context_version += 1
                ctx.save(update_fields=["context_version", "updated_at"])


    request.session["chat_ids"] = []