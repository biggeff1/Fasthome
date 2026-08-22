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

    parts = [kind, province, parent, name]
    return "RDC-" + "-".join(slug(part) for part in parts)


class Command(BaseCommand):
    help = "Importe le fichier canonique de localisation RDC de Fasthome."

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

        if PropertyLocation.objects.exists():
            raise CommandError(
                "Import refusé: des PropertyLocation existent déjà. "
                "Les propriétés existantes sont protégées; il faut les réconcilier avant de remplacer l'arbre."
            )

        LocationNode.objects.all().delete()
        counts = {key: 0 for key in EXPECTED_KEYS}

        for p_order, province in enumerate(payload["provinces"], 1):
            p = self._create_node("PROVINCE", province["name"], None, province["name"], p_order)
            counts["PROVINCE"] += 1

            for c_order, city in enumerate(province.get("cities", []), 1):
                city_node = self._create_node("CITY", city["name"], p, province["name"], c_order)
                counts["CITY"] += 1
                for s_order, commune in enumerate(city.get("communes", []), 1):
                    self._create_node("COMMUNE", commune_name(commune), city_node, province["name"], s_order)
                    counts["COMMUNE"] += 1

            for t_order, territory in enumerate(province.get("territories", []), 1):
                t = self._create_node("TERRITORY", territory["name"], p, province["name"], t_order)
                counts["TERRITORY"] += 1

                rural_items = territory.get("rural_communes", territory.get("communes_rurales", []))
                for s_order, item in enumerate(rural_items, 1):
                    self._create_node("RURAL_COMMUNE", commune_name(item), t, province["name"], s_order)
                    counts["RURAL_COMMUNE"] += 1

                for s_order, item in enumerate(territory.get("sectors", []), 1):
                    self._create_node("SECTOR", item_name(item), t, province["name"], s_order)
                    counts["SECTOR"] += 1

                for s_order, item in enumerate(territory.get("chiefdoms", territory.get("chefferies", [])), 1):
                    self._create_node("CHIEFDOM", item_name(item), t, province["name"], s_order)
                    counts["CHIEFDOM"] += 1

        self.stdout.write(self.style.SUCCESS("Référentiel canonique importé."))
        for key in EXPECTED_KEYS:
            self.stdout.write(f"{key}: {counts[key]}")

    def _create_node(self, kind, name, parent, province_name_value, order):
        parent_name = parent.name if parent else "RDC"
        return LocationNode.objects.create(
            name=name,
            kind=kind,
            code=generated_code(kind, province_name_value, parent_name, name),
            parent=parent,
            order=order,
            active=True,
        )

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


def item_name(item):
    return item if isinstance(item, str) else str(item.get("name") or "").strip()


def commune_name(item):
    return item_name(item)
