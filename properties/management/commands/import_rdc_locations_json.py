import json
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.location_models import LocationNode


SOURCE_URL = "https://raw.githubusercontent.com/open-admin-data/dr-congo-administrative-divisions/master/data/all-flat.json"

# This source is an administrative-database reference, not a 2025 legal ETD census.
# Counts are verified from the downloaded dataset itself before strict import.
MIN_EXPECTED = {
    "PROVINCE": 26,
    "CITY": 39,
    "TERRITORY": 145,
    "SECTOR": 1,
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
        parser.add_argument("--reset", action="store_true", help="Efface le référentiel avant import; refusé si des propriétés sont liées.")

    @transaction.atomic
    def handle(self, *args, **options):
        rows = load_json(options["url"])
        if options["reset"] and not options["dry_run"]:
            if LocationNode.objects.filter(property_locations_as_province__isnull=False).exists():
                raise CommandError("Reset refusé: des propriétés utilisent déjà le référentiel administratif.")
            LocationNode.objects.all().delete()

        parsed = self.parse_rows(rows)
        stats_source = parsed["stats"]
        self.validate_source(stats_source, options["strict"])

        # Resolve parents from the source IDs, then write a clean, deterministic tree.
        source_nodes = {}
        pending = list(parsed["rows"])
        stats_written = {}

        while pending:
            progress = 0
            rest = []
            for row in pending:
                node_id = row["id"]
                parent_id = row["parent_id"]
                if parent_id and parent_id not in source_nodes:
                    rest.append(row)
                    continue

                parent_node = source_nodes.get(parent_id)
                if options["dry_run"]:
                    source_nodes[node_id] = object()
                else:
                    node, _ = LocationNode.objects.update_or_create(
                        code=row["code"],
                        defaults={
                            "name": row["name"],
                            "kind": row["kind"],
                            "parent": parent_node,
                            "active": True,
                            "order": row["order"],
                        },
                    )
                    source_nodes[node_id] = node
                stats_written[row["kind"]] = stats_written.get(row["kind"], 0) + 1
                progress += 1

            if not progress:
                unresolved = [r["id"] for r in rest[:10]]
                raise CommandError(f"Parents introuvables pour des nœuds: {unresolved}")
            pending = rest

        for kind in sorted(stats_source):
            self.stdout.write(
                f"SOURCE {kind}: {stats_source[kind]} | IMPORT {stats_written.get(kind, 0)}"
            )

        if not options["dry_run"]:
            db_stats = {
                kind: LocationNode.objects.filter(kind=kind, active=True).count()
                for kind in stats_source
            }
            for kind in sorted(db_stats):
                self.stdout.write(f"DB {kind}: {db_stats[kind]}")

            if options["strict"]:
                if db_stats != stats_source:
                    raise CommandError(
                        f"La base ne correspond pas exactement à la source: source={stats_source}, db={db_stats}"
                    )

        self.stdout.write(self.style.SUCCESS("Référentiel administratif importé et vérifié."))

    @staticmethod
    def parse_rows(rows):
        parsed_rows = []
        stats = {}
        seen_ids = set()

        for order, row in enumerate(rows):
            node_id = str(row.get("id") or "").strip()
            name = ((row.get("name") or {}).get("local") or "").strip()
            parent = row.get("parent") or {}
            parent_id = str(parent.get("id") or "").strip() or None
            level_name = ((row.get("level_name") or {}).get("local") or "").strip().lower()
            code = str(((row.get("code") or {}).get("id") or node_id)).strip()
            kind = Command.kind_for(level_name, row.get("level"))

            if not node_id or not name or not kind:
                continue
            if node_id in seen_ids:
                raise CommandError(f"ID administratif dupliqué dans la source: {node_id}")
            seen_ids.add(node_id)
            parsed_rows.append({
                "id": node_id,
                "name": name,
                "parent_id": parent_id,
                "code": code,
                "kind": kind,
                "order": order,
            })
            stats[kind] = stats.get(kind, 0) + 1

        return {"rows": parsed_rows, "stats": stats}

    @staticmethod
    def validate_source(stats, strict):
        if not strict:
            return
        missing = [
            f"{kind}={stats.get(kind, 0)} (minimum {minimum})"
            for kind, minimum in MIN_EXPECTED.items()
            if stats.get(kind, 0) < minimum
        ]
        if missing:
            raise CommandError(
                "Source administrative incomplète ou inattendue: " + ", ".join(missing)
            )

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
