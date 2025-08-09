from functools import wraps
from typing import List
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

import models
from routes.auth import user_dep
from schemas.widgets_schema import *
from utils.basic_utils import db_dep

router = APIRouter(prefix="/boards")


def check_board_permission(fn):
    @wraps(fn)
    async def decorator(*args, **kwargs):
        user = kwargs.get("user")
        db = kwargs.get("db")

        stmt = select(models.UserBoards).filter(models.UserBoards.user_id==user.guid)
        res = await db.execute(stmt)
        if res.first():
            return await fn(*args, **kwargs)
        else:
            return HTTPException(status_code=403)
    return decorator


@router.get("/", response_model=List[GetBoardModel])
async def get_boards(user: user_dep, db: db_dep):
    stmt = select(models.UserBoards).filter(models.UserBoards.user_id==user.guid)
    res = await db.execute(stmt)

    boards = res.all()
    
    if not boards or len(boards)==0:
        new_board = models.UserBoards(user_id = user.guid, widgets = [], name = "Дашборд по умолчанию")
        db.add(new_board)
        await db.commit()
        await db.refresh(new_board)
        boards = [(new_board,)]
    boards = list(map(lambda x: x[0], boards))
    ret_boards = []
    for b in boards:
        ret_boards.append(GetBoardModel.model_validate(b, from_attributes=True).model_dump())

    return ret_boards


@router.post("/", status_code=201, response_model=GetBoardModel)
async def add_board(user: user_dep, db: db_dep, board: PostBoardModel):
    new_board = board.model_dump()
    new_board["user_id"]=user.guid
    obj = models.UserBoards(**new_board)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return GetBoardModel.model_validate(obj, from_attributes=True).model_dump()


@router.post("/add_widget", response_model=GetBoardModel)
@check_board_permission
async def add_widget_to_board(user: user_dep, db: db_dep, widget: PostWidgetModel, board_id: int):
    stmt = select(models.UserBoards).filter(models.UserBoards.id == board_id, models.UserBoards.user_id==user.guid)
    res = await db.execute(stmt)
    board = res.first()[0]
    widg_dict = widget.model_dump()
    widg_dict["board_id"]=board_id
    widg = models.BoardsWidgets(**widg_dict)
    db.add(widg)
    await db.commit()
    await db.refresh(board)
    mod = GetBoardModel.model_validate(board, from_attributes=True)
    a = mod.model_dump(by_alias=True)
    return a


@router.delete("/{board_id}/{widget_id}", response_model=GetBoardModel)
@check_board_permission
async def delete_widget(user: user_dep, db: db_dep, board_id: int, widget_id: int):
    stmt = delete(models.BoardsWidgets).filter(
        models.BoardsWidgets.board_id==board_id, models.BoardsWidgets.i==widget_id
    )
    await db.execute(stmt)
    await db.commit()
    stmt_sel = select(models.UserBoards).filter(models.UserBoards.id==board_id)
    res = await db.execute(stmt_sel)
    return GetBoardModel.model_validate(res.first()[0], from_attributes=True).model_dump()


@router.put("/{board_id}")
@check_board_permission
async def update_board(user: user_dep, db: db_dep, board_id: int, board: PostBoardModel):
    res = await db.execute(
        select(models.UserBoards).filter(models.UserBoards.id==board_id)
    )

    b = res.first()[0]
    b.widgets = []
    widgets = []
    for x in board.widgets:

        #x = x.model_dump()
        x["board_id"]=board_id
        
        widget = UpdateWidgetsModel.model_validate(x).model_dump()

        widgets.append(models.BoardsWidgets(**widget))
    #widgets = [models.BoardsWidgets(x.model_dump()) for x in board.widgets]
        
    db.add_all(widgets)
    await db.commit()
    for i in widgets:
        await db.refresh(i)
    await db.commit()
    await db.refresh(b)
    
    return GetBoardModel.model_validate(b, from_attributes=True).model_dump()
