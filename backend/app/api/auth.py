from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_farmer
from app.models import Farmer
from app.security import create_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    login: str
    password: str


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    farmer = db.query(Farmer).filter(Farmer.login == body.login).first()
    if farmer is None or not verify_password(body.password, farmer.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return {
        "token": create_token(farmer.id),
        "farmer": {
            "id": farmer.id,
            "login": farmer.login,
            "full_name": farmer.full_name,
            "shop_name": farmer.shop_name,
            "region": farmer.region,
        },
    }


@router.get("/me")
def me(farmer: Farmer = Depends(get_current_farmer)):
    return {
        "id": farmer.id,
        "login": farmer.login,
        "full_name": farmer.full_name,
        "shop_name": farmer.shop_name,
        "region": farmer.region,
    }
