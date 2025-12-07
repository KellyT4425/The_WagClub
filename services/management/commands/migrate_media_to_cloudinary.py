from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from services.models import Service, ServiceImage

logger = logging.getLogger(__name__)
CLOUD_MARKER = "res.cloudinary.com"


def is_cloudinary(url: str | None) -> bool:
    return bool(url and CLOUD_MARKER in url)


def local_path_for(field_name: str | None) -> Path | None:
    """Return an absolute local filesystem path for a media field name."""
    if not field_name:
        return None
    media_root = Path(getattr(settings, "MEDIA_ROOT", "."))
    return (media_root / field_name).resolve()


def iter_targets() -> Iterable[Tuple[object, str]]:
    """Yield all model/field pairs that hold media needing migration."""
    for s in Service.objects.exclude(img_path="").exclude(img_path__isnull=True):
        yield s, "img_path"
    for si in ServiceImage.objects.exclude(image_url="").exclude(image_url__isnull=True):
        yield si, "image_url"


class Command(BaseCommand):
    help = (
        "Uploads local media (Service.img_path, ServiceImage.image_url) to Cloudinary "
        "via default storage and updates the database fields. Skips already-remote files."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show actions without uploading or saving.",
        )

    def handle(self, *args, **opts):
        dry = bool(opts.get("dry_run"))

        already_cloud = 0
        to_migrate = 0
        uploaded = 0
        missing = 0
        errors = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Scanning media..."))

        for obj, field_name in iter_targets():
            f = getattr(obj, field_name, None)

            # Try best-effort URL; avoid .open() / .path() when Cloudinary storage is active
            try:
                url = f.url  # may raise if missing
            except Exception:
                url = None

            if is_cloudinary(url):
                already_cloud += 1
                continue

            name = getattr(f, "name", "") or ""
            lp = local_path_for(name)

            if not lp or not lp.exists():
                self.stdout.write(self.style.WARNING(f"[missing] {obj}  {name}"))
                missing += 1
                continue

            to_migrate += 1
            self.stdout.write(f"[migrate] {obj}  {name}")

            if dry:
                uploaded += 1  # count as would upload
                continue

            try:
                data = lp.read_bytes()  # read from local filesystem
                stored_name = default_storage.save(name, ContentFile(data))  # goes to Cloudinary
                setattr(obj, field_name, stored_name)
                with transaction.atomic():
                    obj.save(update_fields=[field_name])

                # sanity: ensure URL is now Cloudinary
                try:
                    new_url = getattr(getattr(obj, field_name), "url", None)
                except Exception:
                    new_url = None

                if is_cloudinary(new_url):
                    self.stdout.write(self.style.SUCCESS(f"   OK: {new_url}"))
                    uploaded += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            "   Upload complete but URL not Cloudinary; check storage/STORAGES."
                        )
                    )
                    errors += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ERROR: {e}"))
                errors += 1

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(f"Already on Cloudinary : {already_cloud}"))
        self.stdout.write(self.style.NOTICE(f"Need migration       : {to_migrate}"))
        self.stdout.write(self.style.WARNING(f"Missing local files  : {missing}"))
        if dry:
            self.stdout.write(self.style.HTTP_INFO(f"[DRY RUN] Would upload: {uploaded}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Uploaded             : {uploaded}"))
            if errors:
                self.stdout.write(self.style.ERROR(f"Errors               : {errors}"))

        self.stdout.write(self.style.SUCCESS("Done." if not dry else "Dry run complete."))
