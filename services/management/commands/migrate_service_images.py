import logging
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from services.models import Service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Upload local service images to default storage (Cloudinary in prod) and update paths."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be uploaded without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        migrated = 0
        skipped = 0
        for service in Service.objects.exclude(img_path="").iterator():
            if not service.img_path:
                skipped += 1
                continue

            current_path = str(service.img_path.name)

            # If already stored remotely (e.g., Cloudinary) skip
            if current_path.startswith("https://") or current_path.startswith("http://"):
                logger.info("Skipping remote image for service %s (%s)", service.id, current_path)
                skipped += 1
                continue

            # If the file already exists in default storage, skip uploading again
            if default_storage.exists(current_path):
                logger.info("Already in storage: %s", current_path)
                migrated += 1
                continue

            content = None

            # Try to read via the file field/storage
            try:
                with service.img_path.open("rb") as f:
                    content = ContentFile(f.read())
            except Exception:
                # Fallback to local filesystem path if available
                local_file = Path(service.img_path.path) if hasattr(service.img_path, "path") else None
                if local_file and local_file.exists():
                    with local_file.open("rb") as f:
                        content = ContentFile(f.read())

            if content is None:
                logger.warning("Could not read image for service %s: %s", service.id, current_path)
                skipped += 1
                continue

            if dry_run:
                logger.info("[DRY RUN] Would upload %s", current_path)
                migrated += 1
                continue

            # Upload to default storage
            saved_path = default_storage.save(current_path, content)
            service.img_path.name = saved_path
            service.save(update_fields=["img_path"])
            logger.info("Uploaded and updated service %s to %s", service.id, saved_path)
            migrated += 1

        self.stdout.write(self.style.SUCCESS(f"Migrated: {migrated}, Skipped: {skipped}"))
