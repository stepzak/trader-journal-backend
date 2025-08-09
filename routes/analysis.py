import datetime
import time
from functools import wraps
from typing import Literal, Annotated

import numpy as np
import pandas as pd
import yfinance
from bingX import BingX
from fastapi import Depends
from fastapi.routing import APIRouter
from pandas import DatetimeIndex
from sqlalchemy import select, Float, BIGINT, func, Subquery, ScalarSelect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
import utils.mathutils as mathutils
from routes.auth import user_dep
from schemas.analysis_schema import *
from utils import basic_utils
from utils.basic_utils import db_dep
from utils.bingxextra import get_full_order

router = APIRouter(
    prefix="/analysis"
)


async def user_apis(user: user_dep, db: db_dep):
    apis_stmt = select(models.UserApiKeys.id).filter(models.UserApiKeys.user_id == user.guid).scalar_subquery()
     
    return apis_stmt

apis_dep = Annotated[ScalarSelect, Depends(user_apis)]


async def get_orders_by_user(guid: str, db: AsyncSession) -> List:
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == guid).options(
        selectinload(models.UserApiKeys.orders))
    res = await db.execute(stmt)
    res = res.all()

    orders = list(
        map(
            lambda y: {"type": y[0].key_type, "orders": y[0].orders}, res
        )
    )
    return orders


def refresh_data_bingx(fn):
    @wraps(fn)
    async def decorator(*args, **kwargs):
        user = kwargs.get("user")
        db = kwargs.get("db")

        orders = await get_orders_by_user(user.guid, db)

        orders = list(filter(lambda x: x["type"] == "bingx", orders))
        orders = list(map(lambda y: y["orders"], orders))[0]
         
        if not orders:
            start_time = int((datetime.datetime.now() - datetime.timedelta(days=90)).timestamp()) * 1000

        else:
            start_time = orders[0].order_json["time"] + 1
        # start_time = round((datetime.datetime.now() - datetime.timedelta(days=365 * 10)).timestamp())
        # a = bingx_client.perpetual_v2.account.get_profit_loss_fund_flow(ProfitLossFundFlow(start_time=0, end_time=int(time.time()*1000)))
        try:
            stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                                     models.UserApiKeys.key_type == "bingx")
            api_key = await db.execute(stmt)
            api_key = api_key.first()[0]
            a = await get_full_order(api_key.api_key, api_key.secret_key, int(time.time() * 1000), start_time, 1000, "")
             
            insts = []
            #  
            ords_ids = list(map(lambda x: x.order_id.split("_")[0], orders))
            # ords_ids.extend(list(map(lambda x: x["orderId"], a["data"]["orders"])))
            for order in a["data"]["orders"]:
                try:
                    if not str(order["orderId"]) in ords_ids:
                        instance = models.UsersOrders(order_json=order, order_id=str(order["orderId"])+"_bingx", api_id = api_key.id)
                        insts.append(instance)
                        ords_ids.append(str(order["orderId"]))
                except Exception as ex:
                    await db.rollback()
                     
                    continue

            db.add_all(insts)
            await db.commit()
            await db.refresh(user)
        except Exception as ex:
             
        kwargs["user"] = user

        return await fn(*args, **kwargs)

    return decorator


@router.get("/sharpe", )
async def get_sharpe(user: user_dep, db: db_dep):
    try:
        stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                                 models.UserApiKeys.key_type == "bingx")

        res = await db.execute(stmt)
        api = res.first()[0]

        bingx_client = BingX(api.api_key, api.secret_key)
        portfolio = bingx_client.perpetual_v2.account.get_swap_positions()

        tickers = [i["symbol"][:len(i["symbol"]) - 1] for i in portfolio]
        data = yfinance.download(tickers, start=datetime.datetime.now() - datetime.timedelta(days=365 * 5))["Adj Close"]
        last_prices = data.iloc[-1]
        returns = data.pct_change()
        ret_mean = returns.mean()

        if len(tickers) > 1:
            total = sum(
                list(map(lambda x: float(x["availableAmt"]) * last_prices[x["symbol"][:len(x["symbol"]) - 1]],
                         portfolio)))
            amts = dict(
                (i["symbol"][:len(i["symbol"]) - 1], i["availableAmt"]) for i in portfolio
            )
            weights = {i: float(last_prices[i]) * float(amts[i]) / total
                       for i in tickers}

            rets = [ret_mean[k] * weights[k] for k in tickers]
            return {"sharpe": float(mathutils.sharpe_ratio(rets, 255, 0.05))}

        else:

            mean = np.array(returns.dropna().to_list())
            return {"sharpe": float(mathutils.sharpe_ratio(mean, 255, 0.05))}
    except:
        return {"sharpe": 0}


@router.get("/calculate_var", response_model=VaRModel)
async def calculate_var(user: user_dep, db: db_dep, trust: float):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]

    bingx_client = BingX(api.api_key, api.secret_key)
    # orders = bingx_client.perpetual_v2.trade.get_open_orders()["orders"]
    # orders_map = map(lambda x: {"symbol": x["symbol"][:len(x["symbol"])-1], "amount": x["originalQty"]})
    try:
        portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
        portfolio_map = list(
            map(lambda x: {"symbol": x["symbol"][:len(x["symbol"]) - 1], "amount": float(x["availableAmt"])},
                portfolio))
        var = mathutils.calculate_var(portfolio_map, trust)

        return {"var": var}
    except:
        return {"var": 0}


@router.get("/avg_profit_loss", response_model=AvgProfitModel)
@refresh_data_bingx
async def mean_profit_or_loss(user: user_dep, db: db_dep,  apis_stmt: apis_dep):


    stmt = select(
        func.avg(
            models.UsersOrders.order_json["profit"].as_string().cast(Float)
        )
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt)
    )

    res = await db.execute(stmt)
    mean = res.scalar()

    return {"avg_profit_loss": mean}


@router.get("/portfolio_weights", response_model=Dict[str, float])
@refresh_data_bingx
async def get_portfolio_positions_weights(user: user_dep, db: db_dep):
    try:
        stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id==user.guid, models.UserApiKeys.key_type=="bingx")

        res = await db.execute(stmt)
        api = res.first()[0]

        bingx_client = BingX(api.api_key, api.secret_key)

        portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
        # sum_porfolio = sum(list(map(lambda x: float(x["availableAmt"])*float(x["markPrice"]), portfolio)))
        # weights = list(map(lambda x: {"symbol": x["symbol"], "weight": float(x["availableAmt"])*float(x["avgPrice"])/sum_porfolio}, portfolio))
        # amt = list(map(lambda x: {"symbol": x["symbol"]}, portfolio))
        tickers = [i["symbol"][:len(i["symbol"]) - 1] for i in portfolio]
        data = yfinance.download(tickers, start=datetime.datetime.now() - datetime.timedelta(days=1))["Adj Close"].iloc[
            -1]
        amts = dict(
            (i["symbol"][:len(i["symbol"]) - 1], i["availableAmt"]) for i in portfolio
        )
         
        try:
            return {i: float(data[i]) * float(amts[i]) for i in tickers}
        except:
            return {portfolio[0]["symbol"]: data * float(portfolio[0]["availableAmt"])}
    except:
        return {"": 0}


@router.get("/volatility", response_model=VolatilityModel)
@refresh_data_bingx
async def volatility(user: user_dep, db: db_dep):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]

    bingx_client = BingX(api.api_key, api.secret_key)

    portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
    portfolio_map = list(
        map(lambda x: {"symbol": x["symbol"][:len(x["symbol"]) - 1], "amount": float(x["availableAmt"])}, portfolio))

    return {"volatility": mathutils.calculate_vol(portfolio_map)}


@router.get("/deals", response_model=List[DealsModel])
@refresh_data_bingx
async def get_deals(user: user_dep, db: db_dep,apis_stmt: apis_dep, endTime: int = None, startTime: int = 0, symbol: str = "", ):

    # Получение сделок с использованием API BingX
    if not endTime:
        endTime = int(time.time() * 1000)
    stmt = select(models.UsersOrders.order_json).filter(
        startTime <= models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT) <= endTime,
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["symbol"].as_string() == symbol or len(symbol) == 0)
    res = await db.execute(stmt)
    deals = res.all()
    deals_arr = list(map(lambda x: x[0], deals))
    return deals_arr


@router.get("/positions", response_model=List[PositionsModel])
@refresh_data_bingx
async def get_positions(user: user_dep, db: db_dep):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]

    bingx_client = BingX(api.api_key, api.secret_key)

    portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
    return portfolio


@router.get("/winrate", response_model=WinrateModel)
@refresh_data_bingx
async def get_winrate(user: user_dep, db: db_dep,  apis_stmt: apis_dep):
    # bingx_client = BingX(user.api_key, user.secret_key)
    try:
        stmt = select(models.UsersOrders.order_json).filter(models.UsersOrders.api_id.in_(apis_stmt),
                                                            models.UsersOrders.order_json["profit"].as_string().cast(
                                                                Float) != 0)
        res = await db.execute(stmt)
        alls = res.all()
        stmt2 = select(models.UsersOrders.order_json).filter(models.UsersOrders.api_id.in_(apis_stmt),
                                                             models.UsersOrders.order_json["profit"].as_string().cast(
                                                                 Float) > 0)
        res2 = await db.execute(stmt2)
        plus = res2.all()
        winrate = len(plus) / len(alls)
    except ZeroDivisionError as ex:
         
        winrate = 0
    return {"winrate": winrate}


@router.get("/profit_plot", response_model=Dict[datetime.datetime, float])
@refresh_data_bingx
async def get_profit_by_period(user: user_dep, db: db_dep, apis_stmt: apis_dep, days_offset: int = 365, frequency: str = "auto"):
    start_time = int(
        (datetime.datetime.now() - datetime.timedelta(days=days_offset)).timestamp() * 1000
    )
    """bingx_client = BingX(user.api_key, user.secret_key)

    profits = bingx_client.perpetual_v2.account.get_profit_loss_fund_flow(ProfitLossFundFlow(start_time=start_time, limit=1000, end_time=int(time.time())*1000))
     
    arr = list(
            map(
                lambda x: {
                    "income": float(x["income"]),
                   'timestamp': datetime.datetime.fromtimestamp(float(x["time"])/1000)},
                filter(lambda x: x["incomeType"] == "REALIZED_PNL"
                                 and
                                 (datetime.datetime.now() -datetime.timedelta(days=days_offset)).timestamp()*1000<=float(x["time"]), profits))
        )"""
    stmt = select(
        models.UsersOrders.order_json["profit"].as_string().cast(Float),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT),

    ).filter(start_time <= models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
             models.UsersOrders.order_json["time"].as_string().cast(BIGINT) <= time.time() * 1000,
             models.UsersOrders.api_id.in_(apis_stmt),
             models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0)

    res = await db.execute(stmt)
    orders = res.all()

    arr = list(
        map(lambda x: {"profit": x[0], "timestamp": datetime.datetime.fromtimestamp(x[1] / 1000)}, orders)
    )

    df = pd.DataFrame(arr)
    df.set_index(DatetimeIndex(df["timestamp"]), inplace=True, drop=True)
    freq = {365: "ME", 30: "W", 7: "D", 1: '1h'}
    f = freq.get(days_offset) if frequency == "auto" else frequency
     
     
    test = df.resample(f)["profit"].sum()
    test = test.dropna()
     
    return test.to_dict()


@router.get("/alpha_and_beta", response_model=AlphaBetaModel)
async def alpha_beta(user: user_dep, db: db_dep):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]

    bingx_client = BingX(api.api_key, api.secret_key)

    portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
    portfolio_map = list(
        map(lambda x: {"symbol": x["symbol"][:len(x["symbol"]) - 1], "amount": float(x["availableAmt"])}, portfolio))
     
     
    beta, alpha = mathutils.alpha_and_beta(portfolio_map)

    return {"alpha": alpha, "beta": beta}


@router.get("/weights_categories", response_model=CategoryWeightModel)
async def get_weights_categories(user: user_dep, db: db_dep):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]

    bingx_client = BingX(api.api_key, api.secret_key)

    portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
    portfolio_map = list(
        map(lambda x: {"symbol": x["symbol"][:len(x["symbol"]) - 1], "amount": float(x["availableAmt"])}, portfolio))

     
    try:
        return mathutils.get_categories_weight(portfolio_map)
    except:
        return {"": 0}


@router.get("/change_by_period")
@refresh_data_bingx
async def get_change_by_period(user: user_dep, db: db_dep, apis_stmt: apis_dep, endTime: int = int(time.time() * 1000), startTime: int = 0):
     
    stmt = select(
        func.sum(
            models.UsersOrders.order_json["profit"].as_string().cast(Float)
        ),
    ).filter(startTime <= models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
             models.UsersOrders.order_json["time"].as_string().cast(BIGINT) <= endTime,
             models.UsersOrders.api_id.in_(apis_stmt),
             models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0)

    res = await db.execute(stmt)
    change = res.scalar()
     
    return {"change": change}


@router.get("/profit_factor")
async def profit_factor(user: user_dep, db: db_dep, apis_stmt: apis_dep):
    stmt = select(

        models.UsersOrders.order_json["profit"].as_string().cast(Float),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) > 0)

    stmt2 = select(
        models.UsersOrders.order_json["profit"].as_string().cast(Float),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT)
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) < 0)

    res = await db.execute(stmt)
    res2 = await db.execute(stmt2)

    res = res.all()
    res2 = res2.all()
     
     

    df_p = basic_utils.resample_stmt_res(res)
    df_n = basic_utils.resample_stmt_res(res2)

    df_r_p = df_p['profit'].sum()
    df_r_n = df_n['profit'].sum()
    ret = (df_r_p / df_r_n).abs().dropna(how=0)
    ret.replace([np.inf, -np.inf], np.nan, inplace=True)
    ret = ret.dropna(how=None)
     
    #  
    return ret.to_dict()


@router.get("/deals_count")
async def deals_count(user: user_dep, db: db_dep, apis_stmt: apis_dep):
    stmt = select(
        models.UsersOrders.id,
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0)

    res = await db.execute(stmt)
    res = res.all()

    df_res = basic_utils.resample_stmt_res(res)
     
    count = df_res["profit"].count()
     
    return count.to_dict()


@router.get("/avg_deal_profit")
async def average_deal_profit(user: user_dep, db: db_dep, apis_stmt: apis_dep):

    stmt = select(

        models.UsersOrders.order_json["profit"].as_string().cast(Float),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT),
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0)

    res = await db.execute(stmt)
    res = res.all()
    df = basic_utils.resample_stmt_res(res)
    resampled = df["profit"].mean().dropna()
     
    return resampled.to_dict()


@router.get('/std_mean_loss')
@refresh_data_bingx
async def std_mean_loss(user: user_dep, db: db_dep, apis_stmt: apis_dep):
    stmt2 = select(
        models.UsersOrders.order_json["profit"].as_string().cast(Float),
        models.UsersOrders.order_json["time"].as_string().cast(BIGINT)
    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) < 0)

    res = await db.execute(stmt2)
    res = res.all()

    resampled = basic_utils.resample_stmt_res(res)["profit"].mean()

    arr = list(map(lambda x: x[0], res))
    std = np.std(arr)
    std_mean = (std / resampled).abs().dropna(how=None)
     
    return std_mean * 100
