from django.core.management.base import BaseCommand
from django.conf import settings
import os
from chat.chat_helper import refresh_vector_store


class Command(BaseCommand):
    help = "Refresh RAG vector store"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dir", type=str, help="Valfri sökväg till PDF-mapp")

    def handle(self, *args, **options):
        force = options["force"]
        custom_dir = options.get("dir")

        if custom_dir:
            folder = os.path.join(settings.BASE_DIR, custom_dir)
        else:
            folder = os.path.join(settings.BASE_DIR, "pdf_files")

        self.stdout.write(f"Använder mapp: {folder}")

        ids = refresh_vector_store(force_refresh=force)

        self.stdout.write(self.style.SUCCESS(f"Klart: {ids}"))