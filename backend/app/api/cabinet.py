"""Данные кабинета фермера: обзор, ассортимент, карточки, продажи, акции, клиенты."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_farmer
from app.engine.signals import velocity
from app.models import Action, Client, Farmer, Product, Promotion, Sale

router = APIRouter(prefix="/api/cabinet", tags=["cabinet"])


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    unit: str = Field("шт", max_length=16)
    price: float = Field(gt=0)
    cost: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    expires_at: date | None = None
    photo_count: int = Field(default=0, ge=0, le=20)
    description_len: int = Field(default=0, ge=0, le=5000)
    views_14d: int = Field(default=400, ge=0)
    cart_14d: int = Field(default=20, ge=0)


class ProductUpdate(BaseModel):
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    photo_count: int | None = Field(default=None, ge=0, le=20)
    description_len: int | None = Field(default=None, ge=0, le=5000)


@router.get("/overview")
def overview(
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    today = date.today()
    rev7 = _revenue(db, farmer.id, today - timedelta(days=6), today)
    rev7_prev = _revenue(db, farmer.id, today - timedelta(days=13), today - timedelta(days=7))
    orders7 = _orders(db, farmer.id, today - timedelta(days=6), today)
    new_clients = (
        db.query(func.count(Client.id))
        .filter(Client.farmer_id == farmer.id, Client.first_order_at >= today - timedelta(days=30))
        .scalar()
    )
    repeat_clients = (
        db.query(func.count(Client.id))
        .filter(Client.farmer_id == farmer.id, Client.segment == "repeat")
        .scalar()
    )
    avg_check = round(rev7 / orders7) if orders7 else 0
    completed = (
        db.query(func.coalesce(func.sum(Action.effect_weekly), 0))
        .filter(Action.farmer_id == farmer.id, Action.status == "completed")
        .scalar()
    )
    return {
        "revenue_7d": round(rev7),
        "revenue_7d_prev": round(rev7_prev),
        "revenue_trend": _trend(rev7, rev7_prev),
        "orders_7d": orders7,
        "avg_check": avg_check,
        "new_clients_30d": new_clients,
        "repeat_clients": repeat_clients,
        "assistant_effect": round(float(completed or 0)),
    }


def _trend(current: float, prev: float) -> float:
    if not prev:
        return 0.0
    return round((current / prev - 1) * 100, 1)


def _revenue(db: Session, farmer_id: int, start: date, end: date) -> float:
    return float(
        db.query(func.coalesce(func.sum(Sale.revenue), 0))
        .filter(Sale.farmer_id == farmer_id, Sale.day >= start, Sale.day <= end)
        .scalar()
    )


def _orders(db: Session, farmer_id: int, start: date, end: date) -> int:
    return int(
        db.query(func.count(Sale.id))
        .filter(Sale.farmer_id == farmer_id, Sale.day >= start, Sale.day <= end)
        .scalar()
    )


def _serialize_product(db: Session, p: Product) -> dict:
    today = date.today()
    vel = velocity(db, p.id, today)
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "unit": p.unit,
        "price": p.price,
        "stock": p.stock,
        "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        "velocity": round(vel, 1),
        "cover_days": round(p.stock / vel) if vel > 0 else None,
        "description_len": p.description_len,
        "photo_count": p.photo_count,
    }


def _get_own_product(db: Session, product_id: int, farmer: Farmer) -> Product:
    p = db.get(Product, product_id)
    if p is None or p.farmer_id != farmer.id:
        raise HTTPException(404, "Товар не найден")
    return p


@router.get("/products")
def products(farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.farmer_id == farmer.id).order_by(Product.category, Product.name).all()
    return [_serialize_product(db, p) for p in rows]


@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    p = Product(
        farmer_id=farmer.id,
        name=body.name.strip(),
        category=body.category.strip(),
        unit=body.unit,
        price=body.price,
        cost=body.cost,
        stock=body.stock,
        produced_at=date.today(),
        expires_at=body.expires_at,
        description_len=body.description_len,
        photo_count=body.photo_count,
        views_14d=body.views_14d,
        cart_14d=body.cart_14d,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serialize_product(db, p)


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    p = _get_own_product(db, product_id, farmer)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _serialize_product(db, p)


@router.get("/cards")
def cards(farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.farmer_id == farmer.id).all()
    result = []
    for p in rows:
        ctr = p.cart_14d / p.views_14d if p.views_14d else 0
        quality = 100
        quality -= 25 if p.photo_count < 3 else 0
        quality -= 20 if p.description_len < 200 else 0
        quality -= max(0, 30 - int(ctr * 500))
        result.append(
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "photo_count": p.photo_count,
                "description_len": p.description_len,
                "views_14d": p.views_14d,
                "cart_14d": p.cart_14d,
                "ctr": round(ctr * 100, 1),
                "quality": max(15, min(100, quality)),
            }
        )
    result.sort(key=lambda r: r["quality"])
    return result


@router.get("/sales")
def sales(
    days: int = Query(30, ge=7, le=90),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    by_day = (
        db.query(Sale.day, func.sum(Sale.revenue), func.count(Sale.id))
        .filter(Sale.farmer_id == farmer.id, Sale.day >= start)
        .group_by(Sale.day)
        .order_by(Sale.day)
        .all()
    )
    by_product = (
        db.query(Product.name, Product.category, func.sum(Sale.qty), func.sum(Sale.revenue))
        .join(Sale, Sale.product_id == Product.id)
        .filter(Sale.farmer_id == farmer.id, Sale.day >= start)
        .group_by(Product.name, Product.category)
        .order_by(func.sum(Sale.revenue).desc())
        .limit(10)
        .all()
    )
    by_category = (
        db.query(Product.category, func.sum(Sale.revenue))
        .join(Sale, Sale.product_id == Product.id)
        .filter(Sale.farmer_id == farmer.id, Sale.day >= start)
        .group_by(Product.category)
        .order_by(func.sum(Sale.revenue).desc())
        .all()
    )
    return {
        "by_day": [
            {"day": d.isoformat(), "revenue": round(float(r)), "orders": int(n)} for d, r, n in by_day
        ],
        "top_products": [
            {"name": n, "category": c, "qty": int(q), "revenue": round(float(r))} for n, c, q, r in by_product
        ],
        "by_category": [{"category": c, "revenue": round(float(r))} for c, r in by_category],
    }


def _serialize_promotion(p: Promotion, today: date) -> dict:
    if p.starts_at > today:
        status = "Запланирована"
    elif p.ends_at >= today:
        status = "Активна"
    else:
        status = "Завершена"
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "scope": p.scope,
        "discount_pct": p.discount_pct,
        "category": p.category,
        "starts_at": p.starts_at.isoformat(),
        "ends_at": p.ends_at.isoformat(),
        "joined": p.joined,
        "status": status,
        "result_revenue": p.result_revenue,
        "result_uplift_pct": p.result_uplift_pct,
    }


@router.get("/promotions")
def promotions(farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    today = date.today()
    rows = (
        db.query(Promotion)
        .filter(
            (Promotion.scope == "marketplace")
            | (Promotion.farmer_id == farmer.id)
        )
        .order_by(Promotion.starts_at.desc())
        .all()
    )
    return [_serialize_promotion(p, today) for p in rows]


@router.post("/promotions/{promotion_id}/join")
def join_promotion(
    promotion_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Подтверждённое подключение к акции маркетплейса: пишет флаг joined."""
    p = db.get(Promotion, promotion_id)
    if p is None or p.scope != "marketplace":
        raise HTTPException(404, "Акция маркетплейса не найдена")
    today = date.today()
    if p.ends_at < today:
        raise HTTPException(409, "Акция уже завершена — подключиться нельзя")
    if p.joined:
        raise HTTPException(409, "Вы уже участвуете в этой акции")
    p.joined = True
    db.commit()
    return _serialize_promotion(p, today)


@router.get("/clients")
def clients(farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    today = date.today()
    segments = (
        db.query(Client.segment, func.count(Client.id), func.sum(Client.total_spent))
        .filter(Client.farmer_id == farmer.id)
        .group_by(Client.segment)
        .all()
    )
    lapsed = (
        db.query(Client)
        .filter(
            Client.farmer_id == farmer.id,
            Client.segment == "repeat",
            Client.last_order_at <= today - timedelta(days=21),
            Client.last_order_at >= today - timedelta(days=90),
        )
        .order_by(Client.last_order_at)
        .all()
    )
    top = (
        db.query(Client)
        .filter(Client.farmer_id == farmer.id)
        .order_by(Client.total_spent.desc())
        .limit(10)
        .all()
    )
    segment_names = {"new": "Новые", "repeat": "Постоянные", "single": "Разовые"}
    return {
        "segments": [
            {"key": s, "name": segment_names.get(s, s), "count": int(n), "spent": round(float(sp or 0))}
            for s, n, sp in segments
        ],
        "lapsed_count": len(lapsed),
        "lapsed_avg_silence": (
            round(sum((today - c.last_order_at).days for c in lapsed) / len(lapsed)) if lapsed else 0
        ),
        "top": [
            {
                "ext_ref": c.ext_ref,
                "segment": segment_names.get(c.segment, c.segment),
                "orders": c.total_orders,
                "spent": round(c.total_spent),
                "last_order": c.last_order_at.isoformat(),
            }
            for c in top
        ],
    }
