#860A66F5-DDEB-4035-96DE-B2A77AD11718
import datetime

import requests

url = "https://rest.coinapi.io/v1/indexes"

payload={}
headers = {
  'Accept': 'application/json',
  'X-CoinAPI-Key': '860A66F5-DDEB-4035-96DE-B2A77AD11718'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.json()[0])

import requests

url = "https://rest.coinapi.io/v1/indexes/IDX_REFRATE_PRIMKT_00_USD/timeseries"

payload={
    "period_id": "1DAY",
    "time_end": datetime.datetime.now().isoformat().split("T")[0],
    "time_start": (datetime.datetime.now() - datetime.timedelta(days=365*5) ).isoformat().split("T")[0],

}
headers = {
  'Accept': 'application/json',
  'X-CoinAPI-Key': '860A66F5-DDEB-4035-96DE-B2A77AD11718'
}

response = requests.request("GET", url, headers=headers, params=payload)

print(response.json())