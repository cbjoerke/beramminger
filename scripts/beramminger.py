import datetime
import os
import sys
import time
import pymongo
import requests
from dotenv import load_dotenv

load_dotenv()

# Secrets
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
WEBHOOK_DSBV =os.getenv("WEBHOOK_DSBV", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

try:
    client = pymongo.MongoClient(MONGODB_URI)
    client.admin.command('ping')
    print(f"Successfully connected to MongoDB!")
except Exception as e:
    print(f"ERROR: Failed to connect to MongoDB: {e}")
    sys.exit(1)

db = client["beramminger"]
collection = db["alle_beramminger"]

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
}

today = datetime.date.today()

BACKFILL_DAYS = int(os.getenv("BACKFILL_DAYS", "14"))
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "1000"))

def fetch_hits_for_day(day: datetime.date) -> list[dict]:
    """Fetch all hits for a given day."""
    page = 1
    all_hits: list[dict] = []

    while True:
        params = {
            'fraDato': day.strftime('%Y-%m-%d'),
            'tilDato': day.strftime('%Y-%m-%d'),
            'domstolid': '',
            'sortTerm': 'startdato',
            'sortAscending': 'true',
            'pageSize': str(PAGE_SIZE),
            'page': str(page),
            'query': '',
        }

        response = requests.get(
            'https://www.domstol.no/api/episerver/v3/beramming',
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        hits = payload.get('hits', [])

        print(f"{day} page {page}: {len(hits)} hits")

        if not hits:
            break

        all_hits.extend(hits)

        if len(hits) < PAGE_SIZE:
            break

        page += 1
        time.sleep(0.2)

    return all_hits

start_date = today - datetime.timedelta(days=BACKFILL_DAYS - 1)
print(f"Backfilling from {start_date} to {today} ({BACKFILL_DAYS} days)")

inserted_count = 0
processed_ids = set()
total_hits_seen = 0

for offset in range(BACKFILL_DAYS):
    day = start_date + datetime.timedelta(days=offset)
    day_hits = fetch_hits_for_day(day)
    total_hits_seen += len(day_hits)

    for beramming in day_hits:

        beramming_id = beramming['id']

        if beramming_id in processed_ids:
            continue
        processed_ids.add(beramming_id)

        print(f"Sjekker {beramming_id}...")

        if collection.find_one({'id': beramming_id}):
            print(f"- Skipping {beramming_id} (already exists).")
            continue

        sak_id = beramming["sakId"]
        sak_response = requests.get(
            'https://www.domstol.no/api/episerver/v3/beramming/{}'.format(sak_id),
            headers=headers,
            timeout=30,
        )
        sak_response.raise_for_status()
        sak_data = sak_response.json()

        beramming["sakstype"] = sak_data["sakstype"]
        beramming["saksinfo"] = sak_data

        result = collection.update_one({'id': beramming_id}, {'$set': beramming}, upsert=True)

        if result.matched_count == 0:
            print(f"- Inserted new beramming with id {beramming_id}.")
            inserted_count += 1
            
            start_str = beramming.get("startdato")
            slutt_str = beramming.get("sluttdato")
            sakstype = beramming.get("sakstype", "")
            
            if start_str and slutt_str:
                try:
                    start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    slutt_dt = datetime.datetime.fromisoformat(slutt_str.replace("Z", "+00:00"))
                    
                    if slutt_dt - start_dt == datetime.timedelta(hours=2) and sakstype == "Fengsling":
                        slack_msg = {
                            "text": f"⏱ *Ny 2-timers fengsling:* {beramming['saksnummer']}\n"
                        }
                        try:
                            requests.post(WEBHOOK_DSBV, json=slack_msg, timeout=10)
                        except Exception as e:
                            print(f"WARNING: Klarte ikke å sende Slack-varsel: {e}")
                except ValueError as e:
                    print(f"WARNING: Kunne ikke parse datoene for beramming {beramming_id}: {e}")

        time.sleep(0.5)

print("*" * 20)
print(f"Totalt hentet {total_hits_seen} treff i vinduet.")
print(f"Unike beramminger sjekket: {len(processed_ids)}")
print(f"Lagret {inserted_count} nye beramminger.")

try:
    webhook_response = requests.post(
        WEBHOOK_URL,
        json={"text": str(inserted_count)},
        timeout=10,
    )
    webhook_response.raise_for_status()
    print("Slack webhook sent.")
except Exception as e:
    print(f"WARNING: Failed to send Slack webhook: {e}")