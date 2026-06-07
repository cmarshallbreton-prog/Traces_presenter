import json
from datetime import datetime, timezone

FICHIER_JSON = "traces260105.json"
FICHIER_SORTIE = "events_filtres.json"

DATE_DEBUT = "2025-09-03T13:00:00Z"
DATE_FIN = "2025-09-03T15:00:00Z"


def parse_date(date_str):
    return datetime.fromisoformat(
        date_str.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


debut = parse_date(DATE_DEBUT)
fin = parse_date(DATE_FIN)

with open(FICHIER_JSON, "r", encoding="utf-8") as f:
    events = json.load(f)

events_filtres = []

for event in events:
    timestamp = event.get("timestamp", {}).get("$date")

    if timestamp is None:
        continue

    date_event = parse_date(timestamp)

    if debut <= date_event < fin:
        events_filtres.append(event)

with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
    json.dump(events_filtres, f, ensure_ascii=False, indent=2)

print(f"{len(events_filtres)} événement(s) exporté(s) dans {FICHIER_SORTIE}")