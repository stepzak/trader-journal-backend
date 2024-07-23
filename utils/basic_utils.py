import datetime
from typing import Annotated

from fastapi import Depends
from pandas import DataFrame, DatetimeIndex
from pandas.core.resample import Resampler
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session

db_dep = Annotated[AsyncSession, Depends(get_session)]

def resample_stmt_res(stmt_res: tuple) -> Resampler:
    arr = list(map(lambda x: {"profit": x[0], "time": datetime.datetime.fromtimestamp(x[1]/1000)}, stmt_res))
    df = DataFrame(arr)
    df.set_index(DatetimeIndex(df["time"]), drop=True, inplace=True)
    return df.resample("D")

