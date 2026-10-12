from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(128))
    shop_name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), index=True)
    unit: Mapped[str] = mapped_column(String(16), default="шт")
    price: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    produced_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # метрики карточки товара
    description_len: Mapped[int] = mapped_column(Integer, default=0)
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    views_14d: Mapped[int] = mapped_column(Integer, default=0)
    cart_14d: Mapped[int] = mapped_column(Integer, default=0)

    farmer: Mapped["Farmer"] = relationship()
    sales: Mapped[list["Sale"]] = relationship(back_populates="product")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    ext_ref: Mapped[str] = mapped_column(String(32))
    segment: Mapped[str] = mapped_column(String(32), default="repeat")
    first_order_at: Mapped[date] = mapped_column(Date)
    last_order_at: Mapped[date] = mapped_column(Date)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    revenue: Mapped[float] = mapped_column(Float)
    promo_id: Mapped[int | None] = mapped_column(ForeignKey("promotions.id"), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="sales")
    client: Mapped["Client"] = relationship()


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int | None] = mapped_column(ForeignKey("farmers.id"), nullable=True)
    scope: Mapped[str] = mapped_column(String(16))  # marketplace | shop
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512), default="")
    discount_pct: Mapped[int] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    starts_at: Mapped[date] = mapped_column(Date)
    ends_at: Mapped[date] = mapped_column(Date)
    joined: Mapped[bool] = mapped_column(default=False)
    result_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_uplift_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)  # на какую дату предложено
    rule_key: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32))  # weak_card, expiry_risk, ...
    title: Mapped[str] = mapped_column(String(256))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    facts: Mapped[dict] = mapped_column(JSON, default=dict)
    effect_weekly: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    urgency: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    texts: Mapped[dict] = mapped_column(JSON, default=dict)  # LLM-формулировки (или fallback)
    texts_source: Mapped[str] = mapped_column(String(16), default="template")  # llm | template
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)  # useful | not_useful
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship()
