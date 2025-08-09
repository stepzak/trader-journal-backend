import base64
import os
import uuid
from fastapi import HTTPException
from typing import List

import yfinance
from coinmarketcapapi import CoinMarketCapAPI
from dotenv import load_dotenv
from fastapi.routing import APIRouter
from sqlalchemy import select

import models
import utils.backtestingutil as bt_utils
from routes.auth import user_dep
from schemas.backtesting_schemas import BackTestPostDto, BackTestPostResponse
from utils.basic_utils import db_dep
import cfg

router = APIRouter(
    prefix="/backtesting"
)

load_dotenv()
cmc = CoinMarketCapAPI(os.getenv("CMC_KEY"))

positions = tuple(map(lambda x: x["symbol"] + "-USD", cmc.cryptocurrency_listings_latest().data))


@router.post("/backtest", response_model=BackTestPostResponse)
async def backtest(user: user_dep, db: db_dep, backtest: BackTestPostDto):
    data = yfinance.download(backtest.position, start=backtest.startDate, end=backtest.endDate,
                             interval=backtest.timeframe)

    
    b_d = backtest.model_dump().copy()
    del b_d["startDate"]
    del b_d["endDate"]
    del b_d["position"]
    del b_d["timeframe"]
    # b_d["data"]=data
    
    bt = bt_utils.test_run(data=data, **b_d)
    stats = bt.run()
    guid = str(uuid.uuid4())
    filepath = os.path.join(cfg.ROOT_DIR, "backtesting_plots", str(backtest.strategyName + guid))
    bt.plot(open_browser=False, filename=filepath)
    
    new_strategy = models.BackTests(
        strategyName=backtest.strategyName,
        guid=guid,
        userId=user.guid,
        start=stats.iloc[0],
        end=stats.iloc[1],
        equityFinal=stats.iloc[4],
        equityPeak=stats.iloc[5],
        return_=stats.iloc[6],
        volatility=stats.iloc[8],
        sharpe=stats.iloc[9],
        sortino=stats.iloc[10],
        calmar=stats.iloc[11],
        maxDrowdown=stats.iloc[13],
        avgDrowdown=stats.iloc[14],
        winrate=stats.iloc[18],
        bestTrade=stats.iloc[19],
        worstTrade=stats.iloc[20],
        plotPath=filepath
    )

    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)
    try:
        return new_strategy
    except:
        raise HTTPException(status_code=400,
                            detail="При тестировании стратегии произошла ошибка. Проверьте, чтобы начальная сумма была не меньше средней стоимости актива")


@router.get("/get_plot_file_base64")
async def get_plot_file_by_id(guid: str, db: db_dep):
    filepath = await db.scalar(select(models.BackTests.plotPath).filter(models.BackTests.guid == guid))
    with open(filepath + ".html", "rb") as f:
        b64string = base64.b64encode(f.read())
    return {"base64": b64string.decode("utf-8"), "filename": filepath.split("/")[-1]+".html"}


@router.get("/available_positions_list", response_model=List[str])
async def available_positions_list():
    return positions


@router.get("/", response_model=BackTestPostResponse)
async def get_strategy_results(guid, db: db_dep):
    res = await db.scalar(select(models.BackTests).filter(models.BackTests.guid == guid))
    return BackTestPostResponse.model_validate(res, from_attributes=True).model_dump()
