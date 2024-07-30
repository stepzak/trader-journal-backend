import datetime

from pydantic import BaseModel


class ReportModel(BaseModel):
    id: int
    intro: str
    day_period: int
    created_at: datetime.datetime
    var: float
    sharpe: float
    profit: float
    alpha: float
    beta: float
    conclusion: str
