import datetime
import os
import smtplib
import uuid
from email.message import EmailMessage
from email.mime.text import MIMEText
from typing import Dict, Annotated

from sqlalchemy import delete
from sqlalchemy import select, or_, update
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import count
from starlette.requests import Request

import models
from schemas.auth_schema import *
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from tasks.tasks import send_email
from utils.basic_utils import db_dep

load_dotenv()

ACCESS_EXP = float(os.environ.get("ACCESS_EXPIRE"))
REFRESH_EXP = float(os.environ.get("REFRESH_EXPIRE"))
KEY = os.environ.get("KEY")


router = APIRouter(prefix="/auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
cryptoctx = CryptContext(schemes="bcrypt")


class AuthUtils:
    @staticmethod
    def encrypt_pass(plain_pass):
        return cryptoctx.encrypt(plain_pass)

    @staticmethod
    def verify(plain_pass, hash_pass):
        return cryptoctx.verify(plain_pass, hash_pass)

    @staticmethod
    def create_token(payload: Dict):
        payload_refresh = payload.copy()
        payload_access = payload.copy()
        payload_access["type"]="access"
        payload_access["exp"]= datetime.datetime.now() + datetime.timedelta(minutes=ACCESS_EXP)

        payload_refresh["type"] = "refresh"
        payload_refresh["exp"] = datetime.datetime.now() + datetime.timedelta(minutes=REFRESH_EXP)

        access = jwt.encode(payload_access, key=KEY, algorithm="HS256")
        refresh = jwt.encode(payload_refresh, key = KEY, algorithm="HS256")
        return {
            "access_token": access,
            "refresh_token": refresh
        }

    @staticmethod
    async def get_user_by_token(token: Annotated[oauth2_scheme, Depends()], db: db_dep):
        try:
            print(token)
            payload = jwt.decode(token, key=KEY, algorithms=["HS256"])
            guid = payload["guid"]
            stmt = select(models.Users).filter_by(guid=guid)
            user = await db.execute(stmt)

            us = user.first()[0]
            return us
        except JWTError:
            return {"exception": True, "code": 401, "message": "Неверный токен"}


user_dep = Annotated[models.Users, Depends(AuthUtils.get_user_by_token)]


@router.post("/register", status_code=201)
async def register(user: UserRegister, db: db_dep):
    user_dict = user.dict()
    stmt = select(count(models.Users.id)).where(or_(
        models.Users.username==user.username,
        models.Users.email==user.email,
        models.Users.email==user.username)
    )

    print(stmt)

    user_dict["password"]=AuthUtils.encrypt_pass(user_dict["password"])
    user_dict["guid"]=str(uuid.uuid4())
    res = await db.execute(stmt)
    a=res.first()[0]
    print(a)
    if a>0:
        return {"status_code": 400, "message": "Данное имя пользователя или почта уже существуют"}

    new_user = models.Users(**user_dict)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserGetDTO.model_validate(new_user, from_attributes=True)


@router.post("/login", response_model=TokenModel)
async def login(login_form: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dep):
    username = login_form.username
    stmt = select(models.Users).filter(
        or_(
            models.Users.username==username,
            models.Users.email==username
            )
                                       )
    res = await db.execute(stmt)
    first = res.first()
    if not first:
        raise HTTPException(status_code = 403, detail="Неверный логин или пароль")

    user = first[0]

    if not AuthUtils.verify(login_form.password, user.password):
        raise HTTPException(status_code = 403, detail="Неверный логин или пароль")

    payload = {
        "guid": user.guid
    }

    return AuthUtils.create_token(payload)


@router.get("/profile", response_model=UserGetDTO | None)
async def get_user(user: user_dep):
    """Get user info by token"""


    return UserGetDTO.model_validate(user, from_attributes=True).dict()




@router.delete("/profile")
async def delete_user(user: user_dep, db: db_dep):
    db.delete(user)
    await db.commit()


@router.patch("/profile", response_model=UserGetDTO | Dict)
async def update_user(user: user_dep, vals: UserPutDTO, db: db_dep):
    stmt = update(models.Users).filter_by(guid = user.guid).values(vals.model_dump(exclude_unset=True))
    try:
        await db.execute(stmt)
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as ex:
        msg = str(ex.__dict__.get("orig", ""))
        if "users_email_key" in msg:
            ret = "Данный email уже существует!"
        elif "users_username_key" in msg:
            ret = "Данное имя пользователя уже занято!"
        else:
            ret = "Произошла неизвестная ошибка. Пожалуйста, попробуйте еще раз"
        return {"exception": True, "message": ret}


    return UserGetDTO.model_validate(user, from_attributes=True).dict()


@router.post("/refresh_token", response_model=TokenModel)
async def refresh_token(user: user_dep):
    return AuthUtils.create_token({"guid": user.guid})


@router.post("/reset_password")
async def reset_password(mail: str, db: db_dep):
    delete(models.ResetPassword).filter(models.ResetPassword.mail==mail)
    stmt = select(models.Users).filter_by(email=mail)
    res = await db.execute(stmt)
    user = res.first()
    if not user:
        return {"message": "Mail not found", "exception": True}

    stmt_del = delete(models.ResetPassword).filter(models.ResetPassword.mail == mail)
    stmt_del2 = delete(models.ResetPasswordFactor).filter(models.ResetPasswordFactor.mail == mail)
    await db.execute(stmt_del)
    await db.execute(stmt_del2)

    uid = str(uuid.uuid4())

    new_req = models.ResetPassword(mail=mail, code = uid)
    db.add(new_req)
    await db.commit()


    send_email.delay(uid, mail)
    return {"message": "Успешно"}


@router.post("/check_code")
async def check_code(code: str, mail: str, db: db_dep):
    stmt = select(models.ResetPassword).filter(models.ResetPassword.mail==mail, models.ResetPassword.code==code)
    res = await db.execute(stmt)
    ret = res.first()

    if ret:
        uid = str(uuid.uuid4())
        new_code = models.ResetPasswordFactor(mail=mail, code=uid)
        db.add(new_code)
        await db.commit()
        return {"factor": uid}
    raise HTTPException(status_code=403, detail="Введен неверный код")


@router.put("/change_password")
async def change_password(new_password, factor, db: db_dep):
    substmt = select(models.ResetPasswordFactor.mail.label("mail_factor")).filter(models.ResetPasswordFactor.code==factor).subquery()
    stmt = select(models.Users).filter(models.Users.email.in_(substmt))
    res = await db.execute(stmt)
    try:
        ret = res.first()[0]
    except:
        raise HTTPException(status_code=403, detail="Введен неверный код")
    new_pass = AuthUtils.encrypt_pass(new_password)
    ret.password = new_pass
    await db.commit()
    return {"message": "Успешно"}


@router.put("/set_api_keys")
async def set_api_keys(user: user_dep, db: db_dep, api_keys: ApiKeys):
    try:
        stmt = select(models.UserApiKeys).filter(models.UserApiKeys.user_id==user.guid, models.UserApiKeys.key_type==api_keys.key_type)
        res = await db.execute(stmt)
        key = res.first()
        if not key:
            d = api_keys.model_dump()
            d["user_id"] = user.guid
            new_ins = models.UserApiKeys(**d)
            db.add(new_ins)
            await db.commit()
        else:
            key[0].api_key = api_keys.api_key
            key[0].secret_key = api_keys.secret_key
            key[0].orders=[]
            await db.commit()
            db.refresh(key[0])
    except:
        await db.rollback()
        raise HTTPException(400, detail="Такие ключи уже существуют!")
    return {"message": "Успешно"}
