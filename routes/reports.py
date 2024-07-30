import datetime
from typing import Literal, List

from bingX import BingX
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, Float, BIGINT

import models
from routes.analysis import apis_dep
from routes.auth import user_dep
from schemas.report_schema import ReportModel
from utils import basic_utils
from utils.basic_utils import db_dep

router = APIRouter(
    prefix="/reports"
)


@router.get("/", response_model=ReportModel)
async def get_report(user: user_dep, db: db_dep, apis_stmt: apis_dep, day_offset: Literal['7', '30', '365'] = "7"):
    stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id == user.guid,
                                             models.UserApiKeys.key_type == "bingx")

    res = await db.execute(stmt)
    api = res.first()[0]
    day_offset = int(day_offset)
    date_start = int((datetime.datetime.now()-datetime.timedelta(days=int(day_offset))).timestamp()*1000)
    stmt_pr = select(
        func.sum(models.UsersOrders.order_json["profit"].as_string().cast(Float)),

    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0,
    models.UsersOrders.order_json["time"].as_string().cast(BIGINT)<date_start)

    res_pr = await db.scalar(stmt_pr)
    print(res_pr)
    if not res_pr:
        raise HTTPException(status_code=400, detail="Сделки не найдены")
    stmt_now = select(
        func.sum(models.UsersOrders.order_json["profit"].as_string().cast(Float)),

    ).filter(
        models.UsersOrders.api_id.in_(apis_stmt),
        models.UsersOrders.order_json["profit"].as_string().cast(Float) != 0,
    models.UsersOrders.order_json["time"].as_string().cast(BIGINT)>=date_start)

    res_now = await db.scalar(stmt_now)
    print(res_now)
    bingx_client = BingX(api.api_key, api.secret_key)

    portfolio = bingx_client.perpetual_v2.account.get_swap_positions()
    portfolio_map = list(
        map(lambda x: {"symbol": x["symbol"][:len(x["symbol"]) - 1], "amount": float(x["availableAmt"])}, portfolio))
    report = basic_utils.generate_report(res_now, res_pr, portfolio_map)

    report["user_id"]=user.guid
    report["day_period"]=day_offset
    new_report = models.UserReports(**report)
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report


@router.get("/all", response_model=List[ReportModel])
async def get_all_reports(user: user_dep, db: db_dep):
    reports = user.reports[::-1]
    ret_reports = []
    for r in reports:
        ret_reports.append(ReportModel.model_validate(r, from_attributes=True).model_dump())
    return ret_reports
