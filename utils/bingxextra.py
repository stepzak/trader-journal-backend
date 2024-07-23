import asyncio
import datetime
import hmac
import time
from hashlib import sha256

import httpx
import requests
APIURL = "https://open-api.bingx.com"


def get_full_order(api_key, secret_key, endTime = None, startTime = 0, limit = 500, symbol=""):
    payload = {}
    path = '/openApi/swap/v1/trade/fullOrder'
    method = "GET"
    paramsMap = {
    "endTime": endTime,
    "limit": limit,
    "startTime": startTime,
    "timestamp": int(time.time() * 10 ** 3),
        "symbol": symbol
}
    print(paramsMap)
    paramsStr = parseParam(paramsMap)
    return send_request(method, path, paramsStr, payload, api_key, secret_key)


def get_full_order1(api_key, secret_key, end_time, start_time, limit, symbol):
    orders = []
    while True:
        params = {
                "startTime": start_time,
                "endTime": end_time,
                "limit": limit,
                "symbol": symbol,
                "timestamp": int(time.time()*1000)
            }
        paramsStr = parseParam(params)
        response = send_request("GET", '/openApi/swap/v1/trade/fullOrder', paramsStr, {}, api_key, secret_key)
        print(response)
        new_orders = response["data"]["orders"]

        orders.extend(new_orders)

        if len(new_orders) > limit:
            break

        end_time = new_orders[-1]["time"] + 1  # Обновляем start_time для следующего запроса
        print(end_time)

        start_time = end_time - 1000*86400*7
        print(start_time)

    return {"data": {"orders": orders}}

async def fetch_orders(client, api_key, secret_key, start_time, end_time, limit, symbol, semaphore):
    async with semaphore:
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
            "symbol": symbol,
            "timestamp": int(time.time() * 1000)
        }
        paramsStr = parseParam(params)
        url = "%s%s?%s&signature=%s" % (APIURL, "/openApi/swap/v1/trade/fullOrder", paramsStr, get_sign(secret_key, paramsStr))
        headers = {
            'X-BX-APIKEY': api_key,
        }
        response = await client.get(url, headers=headers)
        try:
            print(response.json())
            return response.json()
        except Exception as ex:
            print(ex)

async def get_full_order(api_key, secret_key, end_time, start_time, limit, symbol):
    orders = []
    semaphore = asyncio.Semaphore(10)  # Ограничиваем количество одновременных запросов до 10
    async with httpx.AsyncClient() as client:
        tasks = []
        while start_time < end_time:
            next_end_time = min(start_time + 7 * 24 * 60 * 60 * 1000, end_time)  # Ограничение на 7 дней в миллисекундах
            tasks.append(fetch_orders(client, api_key, secret_key, start_time, next_end_time, limit, symbol, semaphore))
            start_time = next_end_time + 1

        responses = await asyncio.gather(*tasks)
        for response in responses:
            new_orders = response.get("data", {}).get("orders", [])
            orders.extend(new_orders)


    return {"data": {"orders": orders}}


def get_sign(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()
    #print("sign=" + signature)
    return signature




def send_request(method, path, urlpa, payload, APIKEY, SECRETKEY):
    url = "%s%s?%s&signature=%s" % (APIURL, path, urlpa, get_sign(SECRETKEY, urlpa))
    headers = {
        'X-BX-APIKEY': APIKEY,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.json()

def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "":
     return paramsStr+"&timestamp="+str(int(time.time() * 1000))
    else:
     return paramsStr+"timestamp="+str(int(time.time() * 1000))