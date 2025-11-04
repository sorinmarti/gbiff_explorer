import requests

url = "https://api.gbif.org/v1/occurrence/search"
params = {
    "recordedBy": "Andrew Garrett",
    "limit": 300,
    "offset": 0
}

all_results = []

while True:
    r = requests.get(url, params=params)
    data = r.json()
    results = data.get("results", [])
    all_results.extend(results)

    print(f"Fetched {len(results)} results (total so far: {len(all_results)})")

    if len(results) < params["limit"]:
        break  # no more results
    params["offset"] += params["limit"]
