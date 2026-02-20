import pymongo
import requests
import datetime
import time

db = pymongo.MongoClient("mongodb://localhost:27017/")["beramminger"]
collection = db["u18_beramminger"]

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