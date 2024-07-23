import datetime

import yfinance
from pandas import DataFrame


def test(portfolio):
    tickers = [i["symbol"][:len(i["symbol"]) - 1] for i in portfolio]
    data = yfinance.download(tickers, start=datetime.datetime.now() - datetime.timedelta(days=365 * 5))["Adj Close"]
    last_prices = data.iloc[-1].to_dict()
    returns = data.pct_change()
    print(last_prices[tickers[0]])
    total = sum(list(map(lambda x: float(x["availableAmt"])*last_prices[x["symbol"][:len(x["symbol"]) - 1]], portfolio)))
    amts = dict(
        (i["symbol"][:len(i["symbol"]) - 1], i["availableAmt"]) for i in portfolio
    )
    if len(tickers) > 1:

        weights = {i: last_prices[i]*amts[i]/total
                           for i in tickers}

        print(weights)
        ret_mean = returns.mean()
        print(float(ret_mean["BTC-USD"]*weights["BTC-USD"]))

print(test([{"symbol": "BTC-USDT", "availableAmt": 0.001},{"symbol": "ETH-USDT", "availableAmt": 1}]))