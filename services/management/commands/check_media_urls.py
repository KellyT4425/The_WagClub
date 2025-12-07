from __future__ import annotations

import logging
import requests
from typing import Iterable, Tuple

from django.core.management.base import BaseCommand

from services.models import Service, ServiceImage

logger = logging.getLogger(__name__)


def iter_targets() -> Iterable[Tuple[object, str]]:
    for s in Service.objects.exclude(img_path="").exclude(img_path__isnull=True):
        yield s, "img_path"
    for si in ServiceImage.objects.exclude(image_url="").exclude(image_url__isnull=True):
        yield si, "image_url"


class Command(BaseCommand):
    help = "Check Service and ServiceImage URLs for reachability (200)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of checks (for quick runs).",
        )

    def handle(self, *args, **opts):
        limit = opts.get("limit")
        checked = 0
        ok = 0
        missing = 0
        errors = 0

        for obj, field_name in iter_targets():
            if limit is not None and checked >= limit:
                break

            f = getattr(obj, field_name, None)
            try:
                url = f.url  # may raise if missing
            except Exception:
                url = None

            checked += 1
            name = getattr(f, "name", "") if f else ""

            if not url:
                self.stdout.write(self.style.WARNING(f"[no url] {obj} {name}"))
                missing += 1
                continue

            try:
                resp = requests.head(url, timeout=5)
                status = resp.status_code
                if status == 200:
                    ok += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"[bad status {status}] {obj} {name} {url}")
                    )
                    errors += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[error] {obj} {name} {url} :: {e}"))
                errors += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Checked: {checked}"))
        self.stdout.write(self.style.SUCCESS(f"OK: {ok}"))
        self.stdout.write(self.style.WARNING(f"No URL: {missing}"))
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors/Bad status: {errors}"))
        else:
            self.stdout.write(self.style.SUCCESS("All reachable."))
