from typing import List

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import models
from schemas.messages_schema import MessageModel
from utils.basic_utils import db_dep

router = APIRouter(prefix="/chat")

@router.get("/", response_model=List[MessageModel])
async def get_messages(db: db_dep):
    stmt = select(models.Messages).order_by(models.Messages.created_at.asc())\
        .options(selectinload(models.Messages.user))
    res = await db.execute(stmt)

    msgs = res.all()
    msgs = [MessageModel.model_validate(i[0], from_attributes=True).__dict__ for i in msgs]
    print(msgs)
    return msgs

