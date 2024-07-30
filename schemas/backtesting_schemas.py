import datetime
from typing import Dict, Literal, List

from pydantic import BaseModel
import os

from coinmarketcapapi import CoinMarketCapAPI
from dotenv import load_dotenv

load_dotenv()
cmc = CoinMarketCapAPI(os.getenv("CMC_KEY"))

positions = tuple(map(lambda x: x["symbol"]+"-USD", cmc.cryptocurrency_listings_latest().data))


class ExpressionModel(BaseModel):
    tie_to: str
    expression: str
    value: float | None = None


class LogicalModel(BaseModel):
    signal: float
    signal_false: float = 0
    expressions: List["ExpressionModel"]


class BacktestIndicator(BaseModel):
    indicator: str
    kwargs: Dict[str, float]
    positive_signal: float
    negative_signal: float
    # logical: List[LogicalModel]


class BackTestPostDto(BaseModel):
    strategyName: str = 'myStrategy'
    position: Literal[positions]
    cash: float = 10_000
    margin: float = 1/10
    commission: float = .0007
    tp: float = 0.02
    sl: float = 0.02
    buy_size: float = 0.02
    sell_size: float = 0.02
    indicators: List[BacktestIndicator]
    startDate: datetime.datetime
    endDate: datetime.datetime
    timeframe: str = "1d"
    buy_signal: float = 0.1
    sell_signal: float = -0.1


class BackTestPostResponse(BaseModel):
    id: int
    strategyName: str
    guid: str
    userId: str
    start: datetime.datetime
    end: datetime.datetime
    equityFinal: float
    equityPeak: float
    return_: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    maxDrowdown: float
    avgDrowdown: float
    winrate: float
    bestTrade: float
    worstTrade: float
    plotPath: str
