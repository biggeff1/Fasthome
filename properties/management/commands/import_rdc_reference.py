import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.location_models import LocationNode, PropertyLocation

REFERENCE_PATH = Path("docs/RDC_LOCATION_REFERENCE.json")
EXPECTED_KEYS = ("PROVINCE", "CITY", "TERRITORY", "COMMUNE", "RURAL_COMMUNE", "SECTOR", "CHIEFDOM")


def generated_code(kind, province, parent, name):
    """Generate a stable local code when the reference JSON intentionally has names only."""
    def slug(value):
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
        return value[:40] or "UNKNOWN"

    return "RDC-" + "-".join(slug(part) for part in (kind, province, parent, name))


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", value).strip()).upper()


def item_name(item):
    return item if isinstance(item, str) else str(item.get("name") or "").strip()


def commune_name(item):
    return item_name(item)


class Command(BaseCommand):
    help = "Importe le fichier canonique de localisation RDC de Fasthome."

    def add_arguments(self, parser):
        parser.add_argument("--reconcile", action="store_true")
        parser.add_argument("--deactivate-stale", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if not REFERENCE_PATH.exists():
            raise CommandError(
                "Fichier manquant: docs/RDC_LOCATION_REFERENCE.json. "
                "Copiez votre fichier complet à cet emplacement avant de lancer l'import."
            )

        try:
            payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalide ligne {exc.lineno}, colonne {exc.colno}: {exc.msg}") from exc

        self.validate(payload)

        if options["reconcile"] or options["dry_run"]:
            canonical = self.build_tree(payload, persist=not options["dry_run"])
            if options["dry_run"]:
                self.stdout.write(self.style.SUCCESS("Dry-run validé: aucune modification de base."))
                self.print_counts(canonical)
                return
            self.reconcile_property_locations(canonical)
            if options["deactivate_stale"]:
                self.deactivate_stale(canonical)
            self.stdout.write(self.style.SUCCESS("Référentiel importé et propriétés réconciliées."))
            self.print_counts(canonical)
            return

        if PropertyLocation.objects.exists():
            raise CommandError(
                "Import refusé: des PropertyLocation existent déjà. "
                "Relancez avec --reconcile pour migrer les références existantes sans supprimer les propriétés."
            )

        LocationNode.objects.all().delete()
        canonical = self.build_tree(payload, persist=True)
        self.stdout.write(self.style.SUCCESS("Référentiel canonique importé."))
        self.print_counts(canonical)

    def build_tree(self, payload, persist=True):
        counts = {key: 0 for key in EXPECTED_KEYS}
        canonical = {}

        if persist:
            LocationNode.objects.all().delete()

        def create(kind, name, parent, province, order):
            if persist:
                node = LocationNode.objects.create(
                    name=name,
                    kind=kind,
                    code=generated_code(kind, province, parent.name if parent else "RDC", name),
                    parent=parent,
                    order=order,
                    active=True,
                )
            else:
                node = SimpleNode(name=name, kind=kind, parent=parent, code=generated_code(kind, province, parent.name if parent else "RDC", name))
            canonical[(kind, norm(name), parent.id if parent and persist else id(parent) if parent else None)] = node
            counts[kind] += 1
            return node

        for p_order, province in enumerate(payload["provinces"], 1):
            p = create("PROVINCE", province["name"], None, province["name"], p_order)

            for c_order, city in enumerate(province.get("cities", []), 1):
                city_node = create("CITY", item_name(city), p, province["name"], c_order)
                for s_order, commune in enumerate(city.get("communes", []), 1):
                    create("COMMUNE", commune_name(commune), city_node, province["name"], s_order)

            for t_order, territory in enumerate(province.get("territories", []), 1):
                t = create("TERRITORY", item_name(territory), p, province["name"], t_order)
                rural_items = territory.get("rural_communes", territory.get("communes_rurales", []))
                for s_order, item in enumerate(rural_items, 1):
                    create("RURAL_COMMUNE", commune_name(item), t, province["name"], s_order)
                for s_order, item in enumerate(territory.get("sectors", []), 1):
                    create("SECTOR", item_name(item), t, province["name"], s_order)
                for s_order, item in enumerate(territory.get("chiefdoms", territory.get("chefferies", [])), 1):
                    create("CHIEFDOM", item_name(item), t, province["name"], s_order)

        return {**{"counts": counts}, **canonical}

    @staticmethod
    def reconcile_property_locations(canonical):
        def find(kind, name, parent):
            parent_id = parent.id
            return LocationNode.objects.filter(kind=kind, name=name, parent_id=parent_id, active=True).first()

        for location in PropertyLocation.objects.select_related("province", "city_or_territory", "subdivision"):
            province = LocationNode.objects.filter(kind="PROVINCE", name__iexact=location.province.name, active=True).first()
            if not province:
                raise CommandError(f"Province introuvable pour PropertyLocation {location.pk}: {location.province.name}")

            level2 = LocationNode.objects.filter(
                kind=location.city_or_territory.kind,
                name__iexact=location.city_or_territory.name,
                parent=province,
                active=True,
            ).first()
            if not level2:
                raise CommandError(
                    f"Parent introuvable pour PropertyLocation {location.pk}: {location.city_or_territory.name}"
                )

            location.province_id = province.id
            location.city_or_territory_id = level2.id

            if location.subdivision_id:
                subdivision = LocationNode.objects.filter(
                    kind=location.subdivision.kind,
                    name__iexact=location.subdivision.name,
                    parent=level2,
                    active=True,
                ).first()
                if subdivision:
                    location.subdivision_id = subdivision.id
                else:
                    raise CommandError(
                        f"Subdivision introuvable pour PropertyLocation {location.pk}: {location.subdivision.name}"
                    )
            location.save(update_fields=["province", "city_or_territory", "subdivision"])

    @staticmethod
    def deactivate_stale(canonical):
        current_ids = {
            node.id for key, node in canonical.items() if key != "counts" and hasattr(node, "id")
        }
        if current_ids:
            LocationNode.objects.filter(active=True).exclude(id__in=current_ids).update(active=False)

    @staticmethod
    def print_counts(canonical):
        for key in EXPECTED_KEYS:
            print(f"{key}: {canonical['counts'][key]}")

    @staticmethod
    def validate(payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("provinces"), list):
            raise CommandError("Le fichier doit contenir une clé 'provinces' sous forme de liste.")
        if not payload["provinces"]:
            raise CommandError("Le fichier ne contient aucune province.")

        def require_name(item, kind):
            if isinstance(item, str):
                if not item.strip():
                    raise CommandError(f"{kind}: nom vide.")
                return
            if not isinstance(item, dict) or not str(item.get("name") or "").strip():
                raise CommandError(f"{kind}: le nom est obligatoire.")

        for province in payload["provinces"]:
            require_name(province, "PROVINCE")
            for city in province.get("cities", []):
                require_name(city, "CITY")
                for commune in city.get("communes", []):
                    require_name(commune, "COMMUNE")
            for territory in province.get("territories", []):
                require_name(territory, "TERRITORY")
                for rural in territory.get("rural_communes", territory.get("communes_rurales", [])):
                    require_name(rural, "RURAL_COMMUNE")
                for sector in territory.get("sectors", []):
                    require_name(sector, "SECTOR")
                for chiefdom in territory.get("chiefdoms", territory.get("chefferies", [])):
                    require_name(chiefdom, "CHIEFDOM")


class SimpleNode:
    _counter = 0

    def __init__(self, name, kind, parent, code):
        SimpleNode._counter += 1
        self.id = -SimpleNode._counter
        self.name = name
        self.kind = kind
        self.parent = parent
        self.code = code
