import datetime
import json
import os
import socketio
import uvicorn
from fastapi import FastAPI, Depends
from fastapi_offline import FastAPIOffline
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
import models
from database import get_session, SessionLocal
from routes import auth, messages, analysis, widgets
from fastapi_socketio import SocketManager
import socketio
from fastapi.templating import Jinja2Templates
from schemas.messages_schema import MessageModel
from utils.basic_utils import db_dep

fast_app = FastAPIOffline()

fast_app.mount("/static", StaticFiles(directory=os.path.join("client", "dist", "spa")), name="static")
fast_app.mount("/assets", StaticFiles(directory=os.path.join("client", "dist", "spa", "assets")), name="assets")
templates = Jinja2Templates(os.path.join("client", "dist"))

fast_app.add_middleware(CORSMiddleware, allow_headers=["*"], allow_origins = ["*"], allow_methods = ["*"])

fast_app.include_router(auth.router)
fast_app.include_router(messages.router)
fast_app.include_router(analysis.router)
fast_app.include_router(widgets.router)


@fast_app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("spa/index.html", {"request": request})

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)
app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=fast_app,
    socketio_path='/socket.io'
)


@sio.on("message")
async def on_message(sid, environ):
    print(environ)
    session = SessionLocal()
    user = await auth.AuthUtils.get_user_by_token(environ.get("token"), session)
    print(user.username)
    d = {"content": environ["content"], "user_id": user.guid}
    msg = models.Messages(**d)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    msg_send = MessageModel.model_validate(msg, from_attributes=True).model_dump_json()
    msg_send = json.loads(msg_send)
    #msg_send["created_at"]=datetime.datetime.strftime("%Y-%m-%d ")
    await sio.emit("new_msg_front", msg_send)
    await session.close()

if __name__ == "__main__":
    uvicorn.run(app, port=5000)