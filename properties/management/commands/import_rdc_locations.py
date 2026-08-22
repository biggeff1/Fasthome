import hashlib
import re
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.location_models import LocationNode, PropertyLocation


SOURCE_URL = "https://www.awa-afrika.com/veillejuridique/TableauSynoptiqueDesEntitesTerritoriales.pdf"
EXPECTED = {
    "PROVINCE": 26,
    "TERRITORY": 145,
    "CITY": 99,
    "COMMUNE": 620,
    "RURAL_COMMUNE": 0,
    "SECTOR": 472,
    "CHIEFDOM": 262,
}

PROVINCES = {
    "BAS UELE": "Bas-Uele", "EQUATEUR": "Équateur", "HAUT KATANGA": "Haut-Katanga",
    "HAUT LOMAMI": "Haut-Lomami", "HAUT UELE": "Haut-Uele", "ITURI": "Ituri",
    "KASAI": "Kasaï", "KASAI CENTRAL": "Kasaï-Central", "KASAI ORIENTAL": "Kasaï-Oriental",
    "KINSHASA": "Kinshasa", "KONGO CENTRAL": "Kongo Central", "KWANGO": "Kwango",
    "KWILU": "Kwilu", "LOMAMI": "Lomami", "LUALABA": "Lualaba", "MAI NDOMBE": "Mai-Ndombe",
    "MANIEMA": "Maniema", "MONGALA": "Mongala", "NORD KIVU": "Nord-Kivu",
    "NORD UBANGI": "Nord-Ubangi", "SANKURU": "Sankuru", "SUD KIVU": "Sud-Kivu",
    "SUD UBANGI": "Sud-Ubangi", "TANGANNYIIKA": "Tanganyika", "TSHOPO": "Tshopo",
    "TSHUAPA": "Tshuapa",
}


def clean(value):
    value = str(value or "").replace("\u00ad", "").replace("\x00", " ")
    return re.sub(r"\s+", " ", value).strip(" -\n\r\t")


def norm(value):
    value = clean(value).upper()
    for source, target in {"É": "E", "È": "E", "Ê": "E", "À": "A", "Â": "A", "Î": "I", "Ô": "O"}.items():
        value = value.replace(source, target)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", value)).strip()


def slug_code(kind, parent_code, name):
    digest = hashlib.sha1(f"{kind}|{parent_code}|{norm(name)}".encode()).hexdigest()[:12].upper()
    return f"RDC-{kind[:3]}-{digest}"


def split_cell(value):
    return [clean(x) for x in str(value or "").replace("\r", "\n").split("\n") if clean(x)]


def valid_entity(name):
    name = clean(name)
    upper = norm(name)
    if len(name) < 2 or upper.isdigit():
        return False
    if upper in {"TERRITOIRE", "VILLE", "COMMUNE", "SECTEUR", "CHEFFERIE", "OBSERVATION"}:
        return False
    if upper.startswith("TOTAL") or upper.startswith("NB "):
        return False
    if "SECRETARIAT" in upper or "MOKAMBIA" in upper or "FAIT A" in upper:
        return False
    return True


class Command(BaseCommand):
    help = "Importe la nomenclature RDC du Secrétariat Général de la Décentralisation."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=SOURCE_URL)
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--reconcile", action="store_true")
        parser.add_argument("--deactivate-stale", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            import pdfplumber
        except ImportError as exc:
            raise CommandError("pdfplumber est requis. Exécutez: pip install -r requirements.txt") from exc

        pdf_path = self._download(options["url"])
        records = self._parse_pdf(pdf_path, pdfplumber)
        stats = self._stats(records)
        self.stdout.write("Référentiel extrait de la source officielle :")
        for kind in EXPECTED:
            self.stdout.write(f"  {kind}: {stats.get(kind, 0)}")

        if options["strict"]:
            mismatches = [
                f"{kind}={stats.get(kind, 0)} (attendu {expected})"
                for kind, expected in EXPECTED.items()
                if stats.get(kind, 0) != expected
            ]
            if mismatches:
                raise CommandError("Extraction incomplète : " + ", ".join(mismatches))

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run validé : aucune modification de base."))
            return

        canonical = self._write_tree(records)
        if options["reconcile"]:
            self._reconcile_property_locations(canonical)
        if options["deactivate_stale"]:
            self._deactivate_stale(canonical)

        db_stats = {kind: LocationNode.objects.filter(kind=kind, active=True).count() for kind in EXPECTED}
        for kind in EXPECTED:
            self.stdout.write(f"  DB {kind}: {db_stats[kind]}")
        if options["strict"] and any(db_stats[k] < EXPECTED[k] for k in EXPECTED):
            raise CommandError("La base ne contient pas encore tous les nœuds du référentiel officiel.")
        self.stdout.write(self.style.SUCCESS("Référentiel RDC importé et validé."))

    def _download(self, url):
        request = Request(url, headers={"User-Agent": "Fasthome-RDC-Location-Importer/2.1"})
        try:
            with urlopen(request, timeout=90) as response:
                data = response.read()
        except Exception as exc:
            raise CommandError(f"Impossible de télécharger le référentiel officiel: {exc}") from exc
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.write(data)
        handle.close()
        return Path(handle.name)

    def _parse_pdf(self, pdf_path, pdfplumber):
        records, current_province, current_territory, current_city, order = [], None, None, None, 0
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                detected = self._province_from_heading(page.extract_text() or "")
                if detected:
                    current_province, current_territory, current_city = detected, None, None
                tables = page.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text", "text_x_tolerance": 3, "text_y_tolerance": 3, "min_words_vertical": 2, "min_words_horizontal": 1})
                for table in tables:
                    for raw_row in table:
                        cells = list(raw_row or [])
                        while len(cells) < 6:
                            cells.append("")
                        if self._header_or_total(cells) or not current_province:
                            continue
                        territories, cities, communes, sectors, chiefs = [split_cell(cells[i]) for i in range(5)]
                        for name in territories:
                            if valid_entity(name):
                                current_territory = {"kind": "TERRITORY", "name": name, "parent": current_province, "order": order}
                                records.append(current_territory); order += 1; current_city = None
                        for name in cities:
                            if valid_entity(name):
                                current_city = {"kind": "CITY", "name": name, "parent": current_province, "order": order}
                                records.append(current_city); order += 1
                        if current_province == "Kinshasa" and not current_city and not current_territory:
                            current_city = {"kind": "CITY", "name": "Kinshasa", "parent": current_province, "order": order}
                            records.append(current_city); order += 1
                        for name in communes:
                            if valid_entity(name):
                                parent = current_city or current_territory
                                if parent:
                                    kind = "COMMUNE" if current_city else "RURAL_COMMUNE"
                                    records.append({"kind": kind, "name": name, "parent": parent, "order": order}); order += 1
                        if current_territory:
                            for name in sectors:
                                if valid_entity(name):
                                    records.append({"kind": "SECTOR", "name": name, "parent": current_territory, "order": order}); order += 1
                            for name in chiefs:
                                if valid_entity(name):
                                    records.append({"kind": "CHIEFDOM", "name": name, "parent": current_territory, "order": order}); order += 1
        return self._deduplicate(records)

    @staticmethod
    def _deduplicate(records):
        result, seen = [], set()
        for record in records:
            parent = record["parent"]
            parent_key = parent if isinstance(parent, str) else f"{parent['kind']}:{norm(parent['name'])}"
            key = (record["kind"], parent_key, norm(record["name"]))
            if key not in seen:
                seen.add(key); result.append(record)
        return result

    @staticmethod
    def _stats(records):
        stats = {kind: 0 for kind in EXPECTED}
        stats["PROVINCE"] = len(PROVINCES)
        for record in records:
            stats[record["kind"]] = stats.get(record["kind"], 0) + 1
        return stats

    @staticmethod
    def _header_or_total(cells):
        text = norm(" ".join(clean(c) for c in cells))
        return "TOTAL ETD" in text or "TERRITOIRE VILLE COMMUNE" in text

    @staticmethod
    def _province_from_heading(text):
        match = re.search(r"PROVINCE(?:\s+DE)?\s*:?\s*([^\n]+)", text, re.I)
        if not match:
            return None
        value = re.sub(r"\s+DES ENTIT[ÉE]S.*$", "", match.group(1), flags=re.I)
        return PROVINCES.get(norm(value))

    def _write_tree(self, records):
        nodes = {}
        for index, name in enumerate(PROVINCES.values(), 1):
            node, _ = LocationNode.objects.update_or_create(parent=None, kind="PROVINCE", name=name, defaults={"code": f"RDC-PROV-{index:02d}", "active": True, "order": index})
            nodes[("PROVINCE", norm(name))] = node
        pending = list(records)
        while pending:
            progress, rest = 0, []
            for record in pending:
                parent = record["parent"]
                parent_key = ("PROVINCE", norm(parent)) if isinstance(parent, str) else (parent["kind"], norm(parent["name"]))
                parent_node = nodes.get(parent_key)
                if parent_node is None:
                    rest.append(record); continue
                node, _ = LocationNode.objects.update_or_create(parent=parent_node, kind=record["kind"], name=record["name"], defaults={"code": slug_code(record["kind"], parent_node.code or str(parent_node.pk), record["name"]), "active": True, "order": record["order"]})
                nodes[(record["kind"], norm(record["name"]))] = node
                progress += 1
            if not progress:
                raise CommandError("Parents introuvables: " + ", ".join(f"{r['kind']}:{r['name']}" for r in rest[:10]))
            pending = rest
        return nodes

    @staticmethod
    def _reconcile_property_locations(canonical):
        for location in PropertyLocation.objects.select_related("province", "city_or_territory", "subdivision"):
            province = canonical.get(("PROVINCE", norm(location.province.name)))
            if not province:
                continue
            level2 = canonical.get((location.city_or_territory.kind, norm(location.city_or_territory.name)))
            if not level2 or level2.parent_id != province.id:
                continue
            location.province_id, location.city_or_territory_id = province.id, level2.id
            if location.subdivision:
                subdivision = canonical.get((location.subdivision.kind, norm(location.subdivision.name)))
                if subdivision and subdivision.parent_id == level2.id:
                    location.subdivision_id = subdivision.id
            location.save(update_fields=["province", "city_or_territory", "subdivision"])

    @staticmethod
    def _deactivate_stale(canonical):
        canonical_ids = {node.id for node in canonical.values()}
        LocationNode.objects.filter(active=True).exclude(id__in=canonical_ids).update(active=False)
