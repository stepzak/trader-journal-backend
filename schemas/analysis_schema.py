from typing import List, Dict

from pydantic import BaseModel


class VaRModel(BaseModel):
    var: float


class AvgProfitModel(BaseModel):
    avg_profit_loss: float


class VolatilityModel(BaseModel):
    volatility: float


class WinrateModel(BaseModel):
    winrate: float


class AlphaBetaModel(BaseModel):
    alpha: float
    beta: float


class CategoryWeightModel(BaseModel):
    weights : Dict[str, float]


class TakeProfit(BaseModel):
    type: str
    quantity: float
    stopPrice: float
    price: float
    workingType: str
    stopGuaranteed: str


class StopLoss(BaseModel):
    type: str
    quantity: float
    stopPrice: float
    price: float
    workingType: str
    stopGuaranteed: str


class DealsModel(BaseModel):
    symbol: str
    orderId: int
    side: str
    positionSide: str
    type: str
    origQty: float
    price: float
    executedQty: float
    avgPrice: float
    cumQuote: str
    stopPrice: str
    profit: float
    commission: float
    status: str
    time: int
    updateTime: int
    clientOrderId: str
    leverage: str
    takeProfit: TakeProfit
    stopLoss: StopLoss
    advanceAttr: int
    positionID: int
    takeProfitEntrustPrice: int
    stopLossEntrustPrice: int
    orderType: str
    workingType: str
    onlyOnePosition: bool
    reduceOnly: bool
    postOnly: bool
    stopGuaranteed: str
    triggerOrderId: int
    trailingStopRate: int
    trailingStopDistance: int


class PositionsModel(BaseModel):
    symbol: str
    availableAmt: float
    markPrice: float
    realisedProfit: float