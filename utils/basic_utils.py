import datetime
from typing import Annotated

import numpy as np
import yfinance
from fastapi import Depends
from pandas import DataFrame, DatetimeIndex
from pandas.core.resample import Resampler
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from utils import mathutils

db_dep = Annotated[AsyncSession, Depends(get_session)]


def resample_stmt_res(stmt_res: tuple, freq: str = "D") -> Resampler:
    arr = list(map(lambda x: {"profit": x[0], "time": datetime.datetime.fromtimestamp(x[1]/1000)}, stmt_res))
    df = DataFrame(arr)
    df.set_index(DatetimeIndex(df["time"]), drop=True, inplace=True)
    return df.resample("D")


def generate_introduction(profit, previous_profit):
    trend = "upward" if profit > previous_profit else "downward"
    introduction = f"Your portfolio currently shows a {trend} trend with a total profit of {profit:.2f} USD. Compared to the previous period, the profit has { 'increased' if profit > previous_profit else 'decreased' } by {abs(profit - previous_profit):.2f} USD."

    return introduction


def generate_recommendations(sharpe_ratio, var, alpha, beta):

    recommendations = f"Based on your portfolio's performance, with a Sharpe ratio of {sharpe_ratio:.2f}, we recommend maintaining your current strategy. However, be cautious of potential risks as indicated by a Value at Risk (VAR) of {var:.2f} USD. Your portfolio's Alpha of {alpha:.2f} suggests it is performing {'better' if alpha > 0 else 'worse'} than the market, and a Beta of {beta:.3f} indicates {'higher' if beta > 1 else 'lower'} volatility compared to the market."

    return recommendations


def generate_report(profit, previous_profit, positions):
    #profit = calculate_total_profit(data)

    #previous_profit = get_previous_period_profit(data)
    var = sharpe_ratio = alpha = beta = 0
    introduction = generate_introduction(profit, previous_profit)
    
    if len(positions)>0:
        tickers = [i["symbol"] for i in positions]
        data = yfinance.download(tickers, start=datetime.datetime.now() - datetime.timedelta(days=365 * 5))["Adj Close"]
        
        last_prices = data.iloc[-1]
        returns = data.pct_change()
        ret_mean = returns.mean()

        if len(tickers) > 1:
            total = sum(
                list(map(lambda x: float(x["availableAmt"]) * last_prices[x["symbol"][:len(x["symbol"]) - 1]],
                         positions)))
            amts = dict(
                (i["symbol"][:len(i["symbol"]) - 1], i["availableAmt"]) for i in positions
            )
            weights = {i: float(last_prices[i]) * float(amts[i]) / total
                       for i in tickers}

            rets = [ret_mean[k] * weights[k] for k in tickers]


        else:

            rets = np.array(returns.dropna().to_list())
        var = mathutils.calculate_var(positions, 0.95)

        sharpe_ratio = mathutils.sharpe_ratio(rets, 252, 0.01)

    #max_drawdown = calculate_max_drawdown(data)



        alpha, beta = mathutils.alpha_and_beta(positions)

    recommendations = generate_recommendations(sharpe_ratio, var, alpha, beta)

    report = {

        "intro": introduction,
        "profit": profit,
        "sharpe": sharpe_ratio,
        "var": var,
        "alpha": alpha,
        "beta": beta,
        "conclusion": recommendations

    }

    return report
