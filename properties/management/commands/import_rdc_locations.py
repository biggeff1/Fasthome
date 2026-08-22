import re
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError

from properties.location_models import LocationNode


SOURCE_URL = (
    "https://www.awa-afrika.com/veillejuridique/"
    "TableauSynoptiqueDesEntitesTerritoriales.pdf"
)
EXPECTED = {
    "PROVINCE": 26,
    "TERRITORY": 145,
    "CITY": 99,
    "COMMUNE": 620,
    "SECTOR": 472,
    "CHIEFDOM": 262,
}

PROVINCE_ALIASES = {
    "BAS UELE": "Bas-Uele",
    "EQUATEUR": "Équateur",
    "HAUT KATANGA": "Haut-Katanga",
    "HAUT LOMAMI": "Haut-Lomami",
    "HAUT UELE": "Haut-Uele",
    "ITURI": "Ituri",
    "KASAI": "Kasaï",
    "KASAI CENTRAL": "Kasaï-Central",
    "KASAI ORIENTAL": "Kasaï-Oriental",
    "KINSHASA": "Kinshasa",
    "KONGO CENTRAL": "Kongo Central",
    "KWANGO": "Kwango",
    "KWILU": "Kwilu",
    "LOMAMI": "Lomami",
    "LUALABA": "Lualaba",
    "MAI NDOMBE": "Mai-Ndombe",
    "MANIEMA": "Maniema",
    "MONGALA": "Mongala",
    "NORD KIVU": "Nord-Kivu",
    "NORD UBANGI": "Nord-Ubangi",
    "SANKURU": "Sankuru",
    "SUD KIVU": "Sud-Kivu",
    "SUD UBANGI": "Sud-Ubangi",
    "TANGANNYIIKA": "Tanganyika",
    "TSHOPO": "Tshopo",
    "TSHUAPA": "Tshuapa",
}


def clean(value):
    if value is None:
        return ""
    value = str(value).replace("\u00ad", "")
    value = re.sub(r"\s+", " ", value).strip(" -\n\r\t")
    return value


def split_cell(value):
    value = str(value or "").replace("\r", "\n")
    return [clean(x) for x in value.split("\n") if clean(x)]


def province_name(value):
    key = re.sub(r"[^A-ZÀ-Ÿ ]", "", clean(value).upper())
    key = re.sub(r"\s+", " ", key).strip()
    return PROVINCE_ALIASES.get(key)


def normalize_table_row(row):
    cells = list(row or [])
    while len(cells) < 6:
        cells.append("")
    return [split_cell(cells[i]) for i in range(6)]


class Command(BaseCommand):
    help = "Importe le référentiel administratif RDC depuis le tableau de la Décentralisation."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=SOURCE_URL)
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            import pdfplumber
        except ImportError as exc:
            raise CommandError(
                "pdfplumber est requis. Exécutez: pip install -r requirements.txt"
            ) from exc

        pdf_path = self._download(options["url"])
        stats = {key: 0 for key in EXPECTED}
        current_province = None
        current_territory = None
        current_city = None
        order = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                detected = self._province_from_heading(text)
                if detected:
                    current_province = detected
                    current_territory = None
                    current_city = None

                for table in page.extract_tables() or []:
                    for row in table:
                        columns = normalize_table_row(row)
                        if not any(columns):
                            continue
                        if self._is_header_or_total(columns):
                            continue

                        territories, cities, communes, sectors, chefferies, _ = columns
                        province = current_province
                        if not province:
                            continue

                        for name in territories:
                            if self._valid_entity(name):
                                current_territory = self._ensure(
                                    province, "TERRITORY", name, order, options["dry_run"]
                                )
                                order += 1
                                stats["TERRITORY"] += 1
                                current_city = None

                        for name in cities:
                            if self._valid_entity(name):
                                current_city = self._ensure(
                                    province, "CITY", name, order, options["dry_run"]
                                )
                                order += 1
                                stats["CITY"] += 1

                        if province.name == "Kinshasa" and current_territory and not current_city:
                            current_city = self._ensure(
                                province,
                                "CITY",
                                "Kinshasa",
                                order,
                                options["dry_run"],
                            )
                            order += 1

                        for name in communes:
                            if not self._valid_entity(name):
                                continue
                            if current_city:
                                self._ensure(
                                    current_city, "COMMUNE", name, order, options["dry_run"]
                                )
                                stats["COMMUNE"] += 1
                            elif current_territory:
                                self._ensure(
                                    current_territory,
                                    "RURAL_COMMUNE",
                                    name,
                                    order,
                                    options["dry_run"],
                                )
                                stats["COMMUNE"] += 1
                            order += 1

                        if current_territory:
                            for name in sectors:
                                if self._valid_entity(name):
                                    self._ensure(
                                        current_territory,
                                        "SECTOR",
                                        name,
                                        order,
                                        options["dry_run"],
                                    )
                                    stats["SECTOR"] += 1
                                    order += 1
                            for name in chefferies:
                                if self._valid_entity(name):
                                    self._ensure(
                                        current_territory,
                                        "CHIEFDOM",
                                        name,
                                        order,
                                        options["dry_run"],
                                    )
                                    stats["CHIEFDOM"] += 1
                                    order += 1

        if not options["dry_run"]:
            stats["PROVINCE"] = LocationNode.objects.filter(
                parent__isnull=True, kind="PROVINCE", active=True
            ).count()
            stats["TERRITORY"] = LocationNode.objects.filter(kind="TERRITORY", active=True).count()
            stats["CITY"] = LocationNode.objects.filter(kind="CITY", active=True).count()
            stats["COMMUNE"] = LocationNode.objects.filter(
                kind__in=["COMMUNE", "RURAL_COMMUNE"], active=True
            ).count()
            stats["SECTOR"] = LocationNode.objects.filter(kind="SECTOR", active=True).count()
            stats["CHIEFDOM"] = LocationNode.objects.filter(kind="CHIEFDOM", active=True).count()

        for key in EXPECTED:
            self.stdout.write(f"{key}: {stats[key]}")

        if options["strict"]:
            mismatches = [
                f"{key}={stats[key]} (attendu {expected})"
                for key, expected in EXPECTED.items()
                if stats[key] != expected
            ]
            if mismatches:
                raise CommandError(
                    "Référentiel incomplet ou ambigu : " + ", ".join(mismatches)
                )

        self.stdout.write(self.style.SUCCESS("Import du référentiel RDC terminé."))

    def _download(self, url):
        request = Request(url, headers={"User-Agent": "Fasthome-RDC-Location-Importer/1.0"})
        try:
            response = urlopen(request, timeout=60)
            data = response.read()
        except Exception as exc:
            raise CommandError(f"Impossible de télécharger le référentiel: {exc}") from exc
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.write(data)
        handle.close()
        return Path(handle.name)

    def _province_from_heading(self, text):
        match = re.search(r"PROVINCE(?:\s+DE)?\s*:?\s*([^\n]+)", text, re.I)
        if not match:
            return None
        value = re.sub(r"\s+DES ENTITÉS.*$", "", match.group(1), flags=re.I)
        return province_name(value)

    @staticmethod
    def _valid_entity(name):
        upper = name.upper()
        if len(name) < 2:
            return False
        if upper in {"TERRITOIRE", "VILLE", "COMMUNE", "SECTEUR", "CHEFFERIE", "OBSERVATION"}:
            return False
        if upper.startswith("TOTAL") or upper.startswith("NB"):
            return False
        return not re.fullmatch(r"\d+", name)

    @staticmethod
    def _is_header_or_total(columns):
        text = " ".join(" ".join(c) for c in columns).upper()
        return "TOTAL ETD" in text or "TERRITOIRE VILLE COMMUNE" in text

    @staticmethod
    def _ensure(parent, kind, name, order, dry_run):
        if dry_run:
            return type("DryNode", (), {"name": name, "kind": kind, "parent": parent})()
        node, _ = LocationNode.objects.get_or_create(
            parent=parent,
            kind=kind,
            name=name,
            defaults={"order": order, "active": True},
        )
        return node
