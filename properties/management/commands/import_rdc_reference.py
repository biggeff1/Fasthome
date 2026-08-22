import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.location_models import LocationNode

REFERENCE_PATH = Path("docs/RDC_LOCATION_REFERENCE.json")
EXPECTED_KEYS = ("PROVINCE", "CITY", "TERRITORY", "COMMUNE", "RURAL_COMMUNE", "SECTOR", "CHIEFDOM")


class Command(BaseCommand):
    help = "Importe le fichier canonique de localisation RDC de Fasthome."

    @transaction.atomic
    def handle(self, *args, **options):
        if not REFERENCE_PATH.exists():
            raise CommandError(
                "Fichier manquant: docs/RDC_LOCATION_REFERENCE.json. "
                "Copiez votre fichier complet à cet emplacement avant de lancer l'import."
            )

        payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        self.validate(payload)

        # Build a canonical tree from scratch only when no existing PropertyLocation depends on it.
        if LocationNode.objects.filter(property_locations_as_province__isnull=False).exists():
            raise CommandError(
                "Import refusé: des propriétés utilisent déjà PropertyLocation. "
                "Utilisez d'abord la commande de réconciliation prévue à cet effet."
            )

        LocationNode.objects.all().delete()
        counts = {key: 0 for key in EXPECTED_KEYS}

        for p_order, province in enumerate(payload["provinces"], 1):
            p = LocationNode.objects.create(
                name=province["name"], kind="PROVINCE", code=province["code"], order=p_order, active=True
            )
            counts["PROVINCE"] += 1

            for c_order, city in enumerate(province.get("cities", []), 1):
                city_node = LocationNode.objects.create(
                    name=city["name"], kind="CITY", code=city["code"], parent=p,
                    order=c_order, active=True,
                )
                counts["CITY"] += 1
                for s_order, commune in enumerate(city.get("communes", []), 1):
                    LocationNode.objects.create(
                        name=commune["name"], kind="COMMUNE", code=commune["code"], parent=city_node,
                        order=s_order, active=True,
                    )
                    counts["COMMUNE"] += 1

            for t_order, territory in enumerate(province.get("territories", []), 1):
                t = LocationNode.objects.create(
                    name=territory["name"], kind="TERRITORY", code=territory["code"], parent=p,
                    order=t_order, active=True,
                )
                counts["TERRITORY"] += 1
                for s_order, item in enumerate(territory.get("rural_communes", []), 1):
                    LocationNode.objects.create(
                        name=item["name"], kind="RURAL_COMMUNE", code=item["code"], parent=t,
                        order=s_order, active=True,
                    )
                    counts["RURAL_COMMUNE"] += 1
                for s_order, item in enumerate(territory.get("sectors", []), 1):
                    LocationNode.objects.create(
                        name=item["name"], kind="SECTOR", code=item["code"], parent=t,
                        order=s_order, active=True,
                    )
                    counts["SECTOR"] += 1
                for s_order, item in enumerate(territory.get("chiefdoms", []), 1):
                    LocationNode.objects.create(
                        name=item["name"], kind="CHIEFDOM", code=item["code"], parent=t,
                        order=s_order, active=True,
                    )
                    counts["CHIEFDOM"] += 1

        self.stdout.write(self.style.SUCCESS("Référentiel canonique importé."))
        for key in EXPECTED_KEYS:
            self.stdout.write(f"{key}: {counts[key]}")

    @staticmethod
    def validate(payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("provinces"), list):
            raise CommandError("Le fichier doit contenir une clé 'provinces' sous forme de liste.")

        seen_codes = set()

        def require_node(item, kind):
            if not isinstance(item, dict):
                raise CommandError(f"Entrée {kind} invalide.")
            code = str(item.get("code") or "").strip()
            name = str(item.get("name") or "").strip()
            if not code or not name:
                raise CommandError(f"{kind}: code et nom sont obligatoires.")
            if code in seen_codes:
                raise CommandError(f"Code administratif dupliqué: {code}")
            seen_codes.add(code)

        for province in payload["provinces"]:
            require_node(province, "PROVINCE")
            for city in province.get("cities", []):
                require_node(city, "CITY")
                for commune in city.get("communes", []):
                    require_node(commune, "COMMUNE")
            for territory in province.get("territories", []):
                require_node(territory, "TERRITORY")
                for rural in territory.get("rural_communes", []):
                    require_node(rural, "RURAL_COMMUNE")
                for sector in territory.get("sectors", []):
                    require_node(sector, "SECTOR")
                for chiefdom in territory.get("chiefdoms", []):
                    require_node(chiefdom, "CHIEFDOM")
