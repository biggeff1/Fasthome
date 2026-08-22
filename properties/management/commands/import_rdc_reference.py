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
    def slug(value):
        value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
        return value[:40] or "UNKNOWN"

    return "RDC-" + "-".join(slug(part) for part in (kind, province, parent, name))


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", value)).strip().upper()


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
            raise CommandError("Fichier manquant: docs/RDC_LOCATION_REFERENCE.json")

        try:
            payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalide ligne {exc.lineno}, colonne {exc.colno}: {exc.msg}") from exc

        self.validate(payload)
        stats = self.count_reference(payload)
        self.print_counts(stats)

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run validé: aucune modification de base."))
            return

        if options["reconcile"]:
            canonical = self.build_tree(payload, persist=True)
            self.reconcile_property_locations(canonical)
            if options["deactivate_stale"]:
                self.deactivate_stale(canonical)
            self.stdout.write(self.style.SUCCESS("Référentiel importé et propriétés réconciliées."))
            self.print_db_counts()
            return

        if PropertyLocation.objects.exists():
            raise CommandError(
                "Import refusé: des PropertyLocation existent déjà. "
                "Relancez avec --reconcile pour migrer les références existantes sans supprimer les propriétés."
            )

        LocationNode.objects.all().delete()
        self.build_tree(payload, persist=True)
        self.stdout.write(self.style.SUCCESS("Référentiel canonique importé."))
        self.print_db_counts()

    @staticmethod
    def count_reference(payload):
        counts = {key: 0 for key in EXPECTED_KEYS}
        counts["PROVINCE"] = len(payload["provinces"])
        for province in payload["provinces"]:
            for city in province.get("cities", []):
                counts["CITY"] += 1
                counts["COMMUNE"] += len(city.get("communes", []))
            for territory in province.get("territories", []):
                counts["TERRITORY"] += 1
                counts["RURAL_COMMUNE"] += len(territory.get("rural_communes", territory.get("communes_rurales", [])))
                counts["SECTOR"] += len(territory.get("sectors", territory.get("secteurs", [])))
                counts["CHIEFDOM"] += len(territory.get("chiefdoms", territory.get("chefferies", [])))
        return counts

    def build_tree(self, payload, persist=True):
        canonical = {}

        def create(kind, name, parent, province, order):
            if persist:
                node = LocationNode.objects.update_or_create(
                    parent=parent,
                    kind=kind,
                    name=name,
                    defaults={
                        "code": generated_code(kind, province, parent.name if parent else "RDC", name),
                        "order": order,
                        "active": True,
                    },
                )[0]
            else:
                node = SimpleNode(name, kind, parent, generated_code(kind, province, parent.name if parent else "RDC", name))
            canonical[(kind, norm(name), parent.id if parent else None)] = node
            return node

        if persist:
            provinces = {p.name: p for p in LocationNode.objects.filter(kind="PROVINCE", active=True)}
        else:
            provinces = {}

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
                for s_order, item in enumerate(territory.get("sectors", territory.get("secteurs", [])), 1):
                    create("SECTOR", item_name(item), t, province["name"], s_order)
                for s_order, item in enumerate(territory.get("chiefdoms", territory.get("chefferies", [])), 1):
                    create("CHIEFDOM", item_name(item), t, province["name"], s_order)
        return canonical

    @staticmethod
    def reconcile_property_locations(canonical):
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
                raise CommandError(f"Parent introuvable pour PropertyLocation {location.pk}: {location.city_or_territory.name}")
            location.province_id = province.id
            location.city_or_territory_id = level2.id
            if location.subdivision_id:
                subdivision = LocationNode.objects.filter(
                    kind=location.subdivision.kind,
                    name__iexact=location.subdivision.name,
                    parent=level2,
                    active=True,
                ).first()
                if not subdivision:
                    raise CommandError(f"Subdivision introuvable pour PropertyLocation {location.pk}: {location.subdivision.name}")
                location.subdivision_id = subdivision.id
            location.save(update_fields=["province", "city_or_territory", "subdivision"])

    @staticmethod
    def deactivate_stale(canonical):
        current_ids = {node.id for node in canonical.values() if hasattr(node, "id") and node.id > 0}
        if current_ids:
            LocationNode.objects.filter(active=True).exclude(id__in=current_ids).update(active=False)

    def print_db_counts(self):
        self.stdout.write("Base:")
        for key in EXPECTED_KEYS:
            self.stdout.write(f"  {key}: {LocationNode.objects.filter(kind=key, active=True).count()}")

    def print_counts(self, counts):
        self.stdout.write("Référentiel: ")
        for key in EXPECTED_KEYS:
            self.stdout.write(f"  {key}: {counts[key]}")

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
                for sector in territory.get("sectors", territory.get("secteurs", [])):
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
