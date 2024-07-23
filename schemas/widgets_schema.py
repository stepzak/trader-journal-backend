from typing import List

from pydantic import BaseModel, Field, AliasPath


class PostWidgetModel(BaseModel):
    templateId: str
    x: int
    y: int
    w: int
    h: int
    minH: int
    minW: int
    maxW: int
    maxH: int
    static: bool


class GetWidgetModel(PostWidgetModel):
    i: int


class PostBoardModel(BaseModel):
    name: str
    widgets: List[PostWidgetModel] | List = []


class UpdateWidgetsModel(PostWidgetModel):
    board_id: int


class GetBoardModel(PostBoardModel):
    id: int
    widgets: List[GetWidgetModel]