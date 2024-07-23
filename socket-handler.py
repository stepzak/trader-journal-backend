from app import sio


@sio.on("message")
async def on_message(sid, environ, auth):
    print(sid, environ, auth)