import asyncio
import os

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_session, create_async_engine, async_scoped_session, async_sessionmaker, \
    AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import URL
from dotenv import load_dotenv

load_dotenv()

db = os.getenv("DATABASE")
host = os.getenv("host")
port = os.getenv("port")
username = os.getenv("USERNAME_PG")
password = os.getenv("password")

print(username)

url = URL.create(
    database=db,
    host=host,
    port=5432,
    username=username,
    password=password,
    drivername="postgresql+asyncpg",

)

print(url)

engine = create_async_engine(url=url)

SessionLocal = async_sessionmaker(bind=engine)

Base = declarative_base()

async def get_session() -> AsyncSession:
    session = SessionLocal()
    try:
        yield session
    except:
        await session.rollback()
        raise
    finally:
        await session.close()
