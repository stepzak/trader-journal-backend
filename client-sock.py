import asyncio

from socketio import AsyncClient

client = AsyncClient()

async def connect():
    await client.connect(url = "http://127.0.0.1:5000", socketio_path="socket.io")

asyncio.run(connect())