import pymongo
import requests
import datetime
import time
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Get MongoDB URI from environment variable
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()

# Validate MongoDB URI
if not MONGODB_URI:
    print("ERROR: MONGODB_URI environment variable is not set!")
    sys.exit(1)

try:
    client = pymongo.MongoClient(MONGODB_URI)
    # Test the connection
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

params = {
    'fraDato': today.strftime('%Y-%m-%d'),
    'tilDato': today.strftime('%Y-%m-%d'),
    'domstolid': '',
    'sortTerm': 'startdato',
    'sortAscending': 'true',
    'pageSize': '1000',
    'query': '',
}

response = requests.get('https://www.domstol.no/api/episerver/v3/beramming', params=params, headers=headers)

beramminger = response.json()

print(f"Found {len(beramminger['hits'])} beramminger.")

inserted_count = 0

# Insert each item into the MongoDB collection, using the 'id' field as the unique identifier. Do not count updates as inserts, only new items should be counted. Use upsert to avoid duplicates.
for beramming in beramminger['hits']:

    print(f"Sjekker {beramming['id']}...")

    # Skip if already exists in the database
    if collection.find_one({'id': beramming['id']}):
        print(f"– Skipping {beramming['id']} (already exists).")
        continue

    # Fetch extra data for the beramming
    sak_id = beramming["sakId"]
    sak_response = requests.get(
        'https://www.domstol.no/api/episerver/v3/beramming/{}'.format(sak_id),
        headers=headers,
    )
    sak_data = sak_response.json()

    # Add extra data to the beramming
    beramming["sakstype"] = sak_data["sakstype"]
    beramming["saksinfo"] = sak_data

    # Insert or update the beramming in the database
    result = collection.update_one({'id': beramming['id']}, {'$set': beramming}, upsert=True)

    if result.matched_count == 0:
        print(f"– Inserted new beramming with id {beramming['id']}.")
        inserted_count += 1

    time.sleep(0.5)

print("*" * 20)
print(f"Lagret {inserted_count} nye beramminger.")

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