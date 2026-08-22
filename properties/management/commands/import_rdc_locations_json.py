import json
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.location_models import LocationNode


SOURCE_URL = "https://raw.githubusercontent.com/open-admin-data/dr-congo-administrative-divisions/master/data/all-flat.json"
EXPECTED = {
    "PROVINCE": 26,
    "CITY": 39,
    "TERRITORY": 145,
    "COMMUNE": 0,
    "RURAL_COMMUNE": 0,
    "SECTOR": 472,
    "CHIEFDOM": 262,
}


def load_json(url):
    request = Request(url, headers={"User-Agent": "Fasthome-RDC-Location-Importer/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except Exception as exc:
        raise CommandError(f"Impossible de charger le référentiel structuré: {exc}") from exc
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    raise CommandError("Le référentiel structuré doit contenir une liste dans la clé 'data'.")


class Command(BaseCommand):
    help = "Importe le référentiel administratif RDC structuré par identifiant et parent."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=SOURCE_URL)
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        rows = load_json(options["url"])
        nodes = {}
        pending = list(rows)
        stats = {}

        while pending:
            progress = 0
            rest = []
            for row in pending:
                node_id = str(row.get("id") or "").strip()
                name = ((row.get("name") or {}).get("local") or "").strip()
                parent = row.get("parent") or {}
                parent_id = str(parent.get("id") or "").strip() or None
                level_name = ((row.get("level_name") or {}).get("local") or "").strip().lower()
                code = str(((row.get("code") or {}).get("id") or node_id)).strip()
                kind = self.kind_for(level_name, row.get("level"))

                if not node_id or not name or not kind:
                    continue
                if parent_id and parent_id not in nodes:
                    rest.append(row)
                    continue

                parent_node = nodes.get(parent_id)
                if options["dry_run"]:
                    nodes[node_id] = object()
                else:
                    node, _ = LocationNode.objects.update_or_create(
                        code=code,
                        defaults={
                            "name": name,
                            "kind": kind,
                            "parent": parent_node,
                            "active": True,
                            "order": len(nodes),
                        },
                    )
                    nodes[node_id] = node
                stats[kind] = stats.get(kind, 0) + 1
                progress += 1

            if not progress:
                unresolved = [str(r.get("id")) for r in rest[:10]]
                raise CommandError(f"Parents introuvables pour des nœuds: {unresolved}")
            pending = rest

        if not options["dry_run"]:
            stats = {
                kind: LocationNode.objects.filter(kind=kind, active=True).count()
                for kind in EXPECTED
            }

        for kind in EXPECTED:
            self.stdout.write(f"{kind}: {stats.get(kind, 0)}")

        if options["strict"]:
            mismatches = [
                f"{kind}={stats.get(kind, 0)} (attendu {expected})"
                for kind, expected in EXPECTED.items()
                if stats.get(kind, 0) != expected
            ]
            if mismatches:
                raise CommandError("Référentiel incohérent : " + ", ".join(mismatches))

        self.stdout.write(self.style.SUCCESS("Référentiel administratif importé et vérifié."))

    @staticmethod
    def kind_for(level_name, level):
        normalized = (
            level_name.replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("-", " ")
        )
        if normalized == "province" or level == 1:
            return "PROVINCE"
        if normalized in {"ville", "ville province"}:
            return "CITY"
        if normalized == "territoire":
            return "TERRITORY"
        if normalized == "commune":
            return "COMMUNE"
        if normalized == "commune rurale":
            return "RURAL_COMMUNE"
        if normalized == "secteur":
            return "SECTOR"
        if normalized == "chefferie":
            return "CHIEFDOM"
        return None
