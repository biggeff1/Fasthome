import hashlib
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
        value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
        return value[:18] or "UNKNOWN"

    raw = "RDC-" + "-".join(slug(part) for part in (kind, province, parent, name))
    if len(raw) <= 40:
        return raw
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8].upper()
    return raw[:31] + "-" + digest


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", value).strip()).upper()


def item_name(item):
    return item if isinstance(item, str) else str(item.get("name") or "").strip()


def items_for(obj, *keys):
    """Return the first explicitly supplied list among aliases used by the JSON reference."""
    for key in keys:
        value = obj.get(key)
        if value is not None:
            if not isinstance(value, list):
                raise CommandError(f"La clé '{key}' doit être une liste.")
            return value
    return []


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

        if options["dry_run"]:
            canonical = self.build_tree(payload, persist=False)
            self.stdout.write(self.style.SUCCESS("Dry-run validé: aucune modification de base."))
            self.print_counts(canonical)
            return

        if options["reconcile"]:
            canonical = self.build_tree(payload, persist=True, preserve_existing=True)
            self.reconcile_property_locations()
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

    def build_tree(self, payload, persist=True, preserve_existing=False):
        counts = {key: 0 for key in EXPECTED_KEYS}
        canonical = {"counts": counts}

        if persist and not preserve_existing:
            LocationNode.objects.all().delete()

        def create(kind, name, parent, province, order):
            if persist:
                if preserve_existing:
                    node, _ = LocationNode.objects.get_or_create(
                        name=name,
                        kind=kind,
                        parent=parent,
                        defaults={
                            "code": generated_code(kind, province, parent.name if parent else "RDC", name),
                            "order": order,
                            "active": True,
                        },
                    )
                    changed = []
                    expected_code = generated_code(kind, province, parent.name if parent else "RDC", name)
                    if node.code != expected_code:
                        node.code = expected_code
                        changed.append("code")
                    if node.order != order:
                        node.order = order
                        changed.append("order")
                    if not node.active:
                        node.active = True
                        changed.append("active")
                    if changed:
                        node.save(update_fields=changed)
                else:
                    node = LocationNode.objects.create(
                        name=name,
                        kind=kind,
                        code=generated_code(kind, province, parent.name if parent else "RDC", name),
                        parent=parent,
                        order=order,
                        active=True,
                    )
            else:
                node = SimpleNode(
                    name=name,
                    kind=kind,
                    parent=parent,
                    code=generated_code(kind, province, parent.name if parent else "RDC", name),
                )
            canonical[(kind, norm(name), parent.id if parent else None)] = node
            counts[kind] += 1
            return node

        for p_order, province in enumerate(payload["provinces"], 1):
            p = create("PROVINCE", item_name(province), None, item_name(province), p_order)

            for c_order, city in enumerate(items_for(province, "cities", "villes"), 1):
                city_name = item_name(city)
                city_node = create("CITY", city_name, p, item_name(province), c_order)
                for s_order, commune in enumerate(items_for(city, "communes"), 1):
                    create("COMMUNE", item_name(commune), city_node, item_name(province), s_order)

            for t_order, territory in enumerate(items_for(province, "territories", "territoires"), 1):
                territory_name = item_name(territory)
                t = create("TERRITORY", territory_name, p, item_name(province), t_order)

                for s_order, item in enumerate(
                    items_for(territory, "rural_communes", "communes_rurales", "rural_communes"), 1
                ):
                    create("RURAL_COMMUNE", item_name(item), t, item_name(province), s_order)

                for s_order, item in enumerate(items_for(territory, "sectors", "secteurs"), 1):
                    create("SECTOR", item_name(item), t, item_name(province), s_order)

                for s_order, item in enumerate(items_for(territory, "chiefdoms", "chefferies"), 1):
                    create("CHIEFDOM", item_name(item), t, item_name(province), s_order)

        return canonical

    @staticmethod
    def reconcile_property_locations():
        for location in PropertyLocation.objects.select_related(
            "province", "city_or_territory", "subdivision"
        ):
            province = LocationNode.objects.filter(
                kind="PROVINCE", name__iexact=location.province.name, active=True
            ).first()
            if not province:
                raise CommandError(
                    f"Province introuvable pour PropertyLocation {location.pk}: {location.province.name}"
                )

            level2 = LocationNode.objects.filter(
                kind=location.city_or_territory.kind,
                name__iexact=location.city_or_territory.name,
                parent=province,
                active=True,
            ).first()
            if not level2:
                raise CommandError(
                    f"Parent introuvable pour PropertyLocation {location.pk}: "
                    f"{location.city_or_territory.name}"
                )

            updates = []
            if location.province_id != province.id:
                location.province_id = province.id
                updates.append("province")
            if location.city_or_territory_id != level2.id:
                location.city_or_territory_id = level2.id
                updates.append("city_or_territory")

            if location.subdivision_id:
                subdivision = LocationNode.objects.filter(
                    kind=location.subdivision.kind,
                    name__iexact=location.subdivision.name,
                    parent=level2,
                    active=True,
                ).first()
                if not subdivision:
                    raise CommandError(
                        f"Subdivision introuvable pour PropertyLocation {location.pk}: "
                        f"{location.subdivision.name}"
                    )
                if location.subdivision_id != subdivision.id:
                    location.subdivision_id = subdivision.id
                    updates.append("subdivision")

            if updates:
                location.save(update_fields=updates)

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
            for city in items_for(province, "cities", "villes"):
                require_name(city, "CITY")
                for commune in items_for(city, "communes"):
                    require_name(commune, "COMMUNE")
            for territory in items_for(province, "territories", "territoires"):
                require_name(territory, "TERRITORY")
                for rural in items_for(territory, "rural_communes", "communes_rurales"):
                    require_name(rural, "RURAL_COMMUNE")
                for sector in items_for(territory, "sectors", "secteurs"):
                    require_name(sector, "SECTOR")
                for chiefdom in items_for(territory, "chiefdoms", "chefferies"):
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
