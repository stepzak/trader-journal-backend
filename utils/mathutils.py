import datetime
import os
from typing import Annotated, List, Dict
from coinmarketcapapi import CoinMarketCapAPI
import yfinance
from dotenv import load_dotenv
from pandas import DataFrame
from pandas_datareader import data as pdr
import binance as b_client
import numpy as np
import pandas as pd
import scipy.stats as stats
from bingX import BingX
from bingX.perpetual.v2.types import HistoryOrder, ProfitLossFundFlow
import yfinance as yf

#bingx_client = BingX(api_key="xN6UqmsKgVOvjn2wWHxgWesA75rvkenSgxMhFvVG9Xy67NcIUuO3Hsydob40ZKstuKmkT58sIdwKoKBznvw", secret_key="agHtcfckQdwBUJHWB6OlFF9Q2JHxQDjMydtYTkZT4mUNoCrc78LR71ms47jsbhrOdh6Z0Kpr7UVvoXFh3Q")

load_dotenv()
cmc = CoinMarketCapAPI(os.getenv("CMC_KEY"))

# 
#dict: {symbol, price}

def calculate_var(symbols: List, confidence_level):
     
    tickers = [i["symbol"] for i in symbols]


    data = yf.download(tickers, start=datetime.date.today() - datetime.timedelta(days=365*5), end=datetime.date.today())["Close"]
    d_prices = data.to_dict()
    if len(tickers)>1:
        try:
            for k in d_prices.keys():
                obj = list(filter(lambda x: x["symbol"]==k, symbols))[0]
                last_key = list(d_prices[k])[-1]
                obj["price"]=d_prices[k][last_key]
        except:
            k = tickers[0]
            last_key = list(d_prices)[-1]
            symbols[0]["price"]= d_prices[last_key]

        total = sum(float(i["price"]) * float(i["amount"]) for i in symbols)
        returns = data.pct_change()

        weights = np.array(
            [float(i["price"]) * float(i["amount"]) / total for i in symbols]
        )
        cov_matrix = returns.cov()
        avg_returns = returns.mean()
        dot = avg_returns.dot(weights)
        port_stdev = np.sqrt(weights.T.dot(cov_matrix).dot(weights))
        mean_investment = (1 + dot) * total
        stdev_investment = total * port_stdev
        cutoff1 =stats.norm.ppf(1 - confidence_level, mean_investment, stdev_investment)
        var_1d1 = total - cutoff1
        return var_1d1
    returns = data.pct_change()
    last_key = list(d_prices)[-1]
    total = d_prices[last_key]
    mean_investment = (1 + returns.mean()) * total
    std = returns.std()
    cutoff1 = stats.norm.ppf(1 - confidence_level, mean_investment, std)
    var_1d1 = total - cutoff1
    return var_1d1


def sharpe_ratio(return_series, N, rf):
    try:
        m = np.mean(return_series) * N - rf


        s = np.std(return_series) * np.sqrt(N)

        return m / s
    except:
        return 0


def calculate_vol(symbols):
     

    tickers = [i["symbol"] for i in symbols]

    data = \
    yf.download(tickers, start=datetime.date.today() - datetime.timedelta(days=365*5), end=datetime.date.today())[
        "Close"]
    d_prices = data.to_dict()
    if len(tickers)>1:
        for k in d_prices.keys():
            obj = list(filter(lambda x: x["symbol"] == k, symbols))[0]
            last_key = list(d_prices[k])[-1]
            obj["price"] = d_prices[k][last_key]

        total = sum(i["price"] * i["amount"] for i in symbols)
        returns = data.pct_change()

        weights = np.array(
            [i["price"] * i["amount"] / total for i in symbols]
        )

        portfolio_vol = np.sqrt(np.dot(weights.T,np.dot(returns.cov()*255,weights)))
        return portfolio_vol
    else:
        returns = data.pct_change()
        vol = returns.rolling(3).std()*np.sqrt(3)
         
        return np.mean(vol.dropna().to_list())

def calculate_weights(s: dict):
    pass


def alpha_and_beta(symbols: List):
    tickers = [i["symbol"] for i in symbols]
    data = yfinance.download(tickers, start=datetime.date.today() - datetime.timedelta(days=365*5))["Adj Close"]


    d_prices = data.to_dict()
    benchmark_price = yf.download("BTC-USD", start=datetime.date.today() - datetime.timedelta(days=365 * 5))

    benchmark_ret = benchmark_price["Adj Close"].pct_change()[1:]
    if len(tickers)>1:
        try:
            for k in d_prices.keys():
                obj = list(filter(lambda x: x["symbol"] == k, symbols))[0]
                last_key = list(d_prices[k])[-1]
                obj["price"] = d_prices[k][last_key]
        except:
            k = tickers[0]
            last_key = list(d_prices)[-1]
            symbols[0]["price"] = d_prices[last_key]

        total = sum(float(i["price"]) * float(i["amount"]) for i in symbols)
        returns = data.pct_change()[1:]

        weights = np.array(
            [float(i["price"]) * float(i["amount"]) / total for i in symbols]
        )

        portfolio_returns = (returns*weights).sum(axis = 1)
        lng = stats.linregress(benchmark_ret.values,
                                         portfolio_returns.values)
        alpha = lng.intercept
        beta = lng.slope

    else:
        returns = data.pct_change()[1:]
        conc = pd.concat([returns, benchmark_ret], axis=1).fillna(0)
        returns_c = conc.iloc[:,0]
        bench_c = conc.iloc[:,1]
        lng = stats.linregress(bench_c.values,
                                         returns_c.values)
        alpha = lng.intercept
        beta = lng.slope

    return float(beta), float(alpha)


def calculate_beta_deprecated(symbols, symb_benchmark):
    tickers = [i["symbol"] for i in symbols]
    df_bench = yf.download(symb_benchmark, start=datetime.date.today() - datetime.timedelta(days=365 * 5), end=datetime.date.today())["Close"]

    market_returns = df_bench.pct_change()[1:]

    data = \
        yf.download(tickers, start=datetime.date.today() - datetime.timedelta(days=365 * 5), end=datetime.date.today())[
            "Close"]

    d_prices = data.to_dict()
    if len(tickers) > 1:
        for k in d_prices.keys():
            obj = list(filter(lambda x: x["symbol"] == k, symbols))[0]
            last_key = list(d_prices[k])[-1]
            obj["price"] = d_prices[k][last_key]

        total = sum(i["price"] * i["amount"] for i in symbols)
        returns = data.pct_change()
        weights = np.array(
            [float(i["price"]) * float(i["amount"]) / total for i in symbols]
        )
        portfolio_returns = (returns * weights).sum(axis=1)
        covariance = portfolio_returns.cov(market_returns)
        variance = market_returns.var()
    else:
        portfolio_returns = data.pct_change()


        covariance = portfolio_returns.cov(market_returns)
        variance = market_returns.var()

    beta = covariance / variance

    return beta


def get_categories_weight(symbols: List):
    tickers = [i["symbol"].split("-")[0] for i in symbols]
    ticks = [i["symbol"] for i in symbols]
    data = \
        yf.download(ticks, start=datetime.date.today() - datetime.timedelta(days=1) )["Adj Close"].iloc[-1]

    if len(tickers)>1:
        tick_category = []
         
        for i in tickers:
            ticker = cmc.cryptocurrency_info(symbol=i).data
            tick_category.append({"weights": float(data[i+"-USD"])*float(list(filter(lambda x: x["symbol"]==i+"-USD", symbols))[0]["amount"]), "category": ticker[i][0]["category"]})

         
        df = DataFrame(tick_category)
        a = df.groupby("category").sum()
         
        return a.to_dict()
    else:
        ticker = cmc.cryptocurrency_info(symbol=tickers[0]).data
        a =  yf.Ticker(ticks[0]).history()["Close"]
         
        return {"weights": {
            ticker[tickers[0]][0]["category"]: a.iloc[-1]*symbols[0]["amount"]
        }}

#playground
if __name__ == "__main__":
    now = datetime.datetime.now().timestamp()
   #  

     
        [{"symbol": "MAV-USD"}]
    ))
