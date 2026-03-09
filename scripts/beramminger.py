import datetime
import os
import sys
import time
import pymongo
import requests
from dotenv import load_dotenv

load_dotenv()

# CONNECT TO MONGODB
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()

try:
    client = pymongo.MongoClient(MONGODB_URI)
    client.admin.command('ping')
    print(f"Successfully connected to MongoDB!")
except Exception as e:
    print(f"ERROR: Failed to connect to MongoDB: {e}")
    sys.exit(1)

db = client["beramminger"]
collection = db["alle_beramminger"]

# SCRIPT FOR SCRAPING BERAMMINGER FROM DOMSTOL.NO
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

        # A case can appear on multiple days in the window; process each id only once per run.
        if beramming_id in processed_ids:
            continue
        processed_ids.add(beramming_id)

        print(f"Sjekker {beramming_id}...")

        # Skip if already exists in the database
        if collection.find_one({'id': beramming_id}):
            print(f"- Skipping {beramming_id} (already exists).")
            continue

        # Fetch extra data for the beramming
        sak_id = beramming["sakId"]
        sak_response = requests.get(
            'https://www.domstol.no/api/episerver/v3/beramming/{}'.format(sak_id),
            headers=headers,
            timeout=30,
        )
        sak_response.raise_for_status()
        sak_data = sak_response.json()

        # Add extra data to the beramming
        beramming["sakstype"] = sak_data["sakstype"]
        beramming["saksinfo"] = sak_data

        # Insert or update the beramming
        result = collection.update_one({'id': beramming_id}, {'$set': beramming}, upsert=True)

        if result.matched_count == 0:
            print(f"- Inserted new beramming with id {beramming_id}.")
            inserted_count += 1

        time.sleep(0.5)

print("*" * 20)
print(f"Totalt hentet {total_hits_seen} treff i vinduet.")
print(f"Unike beramminger sjekket: {len(processed_ids)}")
print(f"Lagret {inserted_count} nye beramminger.")

# SEND SLACK WEBHOOK WITH INSERTED COUNT
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

if WEBHOOK_URL:
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
else:
    print("WEBHOOK_URL is not set, skipping Slack webhook.")