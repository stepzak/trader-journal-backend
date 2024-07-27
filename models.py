import asyncio

from sqlalchemy import Integer, Column, String, JSON, func, DateTime, ForeignKey, text, select, BIGINT, Boolean, Float
from sqlalchemy.orm import relationship, selectinload
from database import engine, Base, get_session
#from sqlalchemy_views import CreateView, DropView

class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True)
    email = Column(String(60), unique=True)
    password = Column(String(144))
    guid = Column(String(100), unique=True)
    bio = Column(String(1024))
    url_image = Column(String(200), default="https://static.tildacdn.com/tild6338-3666-4133-a633-643664333838/photo.jpg")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    api_keys = relationship("UserApiKeys")
    #orders = relationship("UsersOrders", cascade="all,delete")
    boards = relationship("UserBoards", lazy="selectin", cascade="all,delete")
    strategies_backtest = relationship("BackTests", cascade="all,delete")

class Test(Base):
    __tablename__ = "test"
    id = Column(Integer, primary_key=True)
    js = Column(JSON)


class PublicUserView(Base):
    __tablename__ = "public_users_view"
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True)
    guid = Column(String(100), unique=True)
    bio = Column(String(1024))
    url_image = Column(String(200))


class Messages(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    content = Column(String(100))
    user_id = Column(String(100), ForeignKey(Users.guid))
    created_at = Column(DateTime, default=func.now())
    user = relationship(Users, lazy="selectin", backref="user")


class ResetPassword(Base):
    __tablename__ = "reset_password_requests"
    id = Column(Integer, primary_key=True)
    mail = Column(String(60), unique=True)
    code = Column(String(60), unique=True)


class ResetPasswordFactor(Base):
    __tablename__ = "reset_password_factor"
    id = Column(Integer, primary_key=True)
    mail = Column(String, unique=True)
    code = Column(String, unique=True)


class UserApiKeys(Base):
    __tablename__ = "users_api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), ForeignKey(Users.guid))
    api_key = Column(String(100), unique=True)
    secret_key = Column(String(100), unique=True)
    key_type = Column(String(100))
    orders = relationship("UsersOrders")

class UsersOrders(Base):
    __tablename__ = "users_orders"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(200), unique=True, nullable=False)
    api_id = Column(Integer, ForeignKey(UserApiKeys.id))
    order_json = Column(JSON)


class UserBoards(Base):
    __tablename__ = "users_boards"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), ForeignKey(Users.guid))
    name = Column(String(100))
    widgets = relationship("BoardsWidgets", lazy="selectin", cascade="all,delete")


class BoardsWidgets(Base):
    __tablename__ = "boards_widgets"
    i = Column(Integer, primary_key=True, autoincrement=True)
    templateId = Column(String(50))
    board_id = Column(Integer, ForeignKey(UserBoards.id))
    x = Column(Integer)
    y = Column(Integer)
    w = Column(Integer)
    h = Column(Integer)
    static = Column(Boolean)
    minW = Column(Integer)
    minH = Column(Integer)
    maxW = Column(Integer)
    maxH = Column(Integer)


class BackTests(Base):
    __tablename__ = "backtests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategyName = Column(String(100))
    guid = Column(String(100), unique=True)
    userId = Column(String(100), ForeignKey(Users.guid))
    start = Column(DateTime)
    end = Column(DateTime)
    equityFinal = Column(Float)
    equityPeak = Column(Float)
    return_ = Column(Float)
    volatility = Column(Float)
    sharpe = Column(Float)
    sortino = Column(Float)
    calmar = Column(Float)
    maxDrowdown = Column(Float)
    avgDrowdown = Column(Float)
    winrate = Column(Float)
    bestTrade = Column(Float)
    worstTrade = Column(Float)
    plotPath = Column(String(2048), unique=True)


async def create_tables():
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE OR REPLACE VIEW public_users_view AS SELECT id, username, guid, bio, url_image FROM users")
        )
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_tables())