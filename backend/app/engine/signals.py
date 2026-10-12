"""Детерминированные правила выявления сигналов.

Каждое правило возвращает список кандидатов в действия. Кандидат несёт:
факты (сигнал), расчёт ожидаемого эффекта (₽/нед), уверенность и срочность.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Action, Client, Product, Promotion, Sale

MARGIN_RATE_FALLBACK = 0.35


@dataclass
class Candidate:
    rule_key: str
    type: str
    title: str
    effect_weekly: float
    confidence: float
    urgency: int
    facts: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    product_id: int | None = None
    segment: str | None = None

    @property
    def score(self) -> float:
        return self.effect_weekly * self.confidence * self.urgency

    @property
    def object_key(self) -> tuple:
        return (self.type, self.product_id, self.segment)


# ---------------------------------------------------------------- queries

def margin_rate(p: Product) -> float:
    if p.price <= 0:
        return MARGIN_RATE_FALLBACK
    return max(0.05, min(0.9, (p.price - p.cost) / p.price))


def sales_qty(db: Session, product_id: int, start: date, end: date) -> int:
    q = (
        db.query(func.coalesce(func.sum(Sale.qty), 0))
        .filter(Sale.product_id == product_id, Sale.day >= start, Sale.day <= end)
        .scalar()
    )
    return int(q or 0)


def velocity(db: Session, product_id: int, today: date, days: int = 14) -> float:
    """Средние продажи товара, шт/день."""
    return sales_qty(db, product_id, today - timedelta(days=days - 1), today) / days


def weekly_revenue(db: Session, farmer_id: int, start: date, end: date) -> float:
    q = (
        db.query(func.coalesce(func.sum(Sale.revenue), 0))
        .filter(Sale.farmer_id == farmer_id, Sale.day >= start, Sale.day <= end)
        .scalar()
    )
    return float(q or 0)


def category_median_price(db: Session, category: str) -> float | None:
    prices = [
        row[0]
        for row in db.query(Product.price).filter(Product.category == category).all()
    ]
    if not prices:
        return None
    prices.sort()
    n = len(prices)
    mid = n // 2
    return prices[mid] if n % 2 else (prices[mid - 1] + prices[mid]) / 2


def category_median_ctr(db: Session, category: str) -> float | None:
    ctrs = []
    for views, carts in (
        db.query(Product.views_14d, Product.cart_14d).filter(Product.category == category).all()
    ):
        if views >= 30:
            ctrs.append(carts / views)
    if not ctrs:
        return None
    ctrs.sort()
    n = len(ctrs)
    mid = n // 2
    return ctrs[mid] if n % 2 else (ctrs[mid - 1] + ctrs[mid]) / 2


# ---------------------------------------------------------------- rules

def rule_weak_card(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Слабая карточка: мало фото/короткое описание/низкая конверсия в корзину."""
    out = []
    products = db.query(Product).filter(Product.farmer_id == farmer_id).all()
    for p in products:
        if p.views_14d < 50:
            continue
        ctr = p.cart_14d / p.views_14d
        median_ctr = category_median_ctr(db, p.category) or 0.06
        issues = []
        if p.photo_count < 3:
            issues.append(f"в карточке {p.photo_count} фото (норма от 3)")
        if p.description_len < 200:
            issues.append(f"описание {p.description_len} символов (норма от 400)")
        if ctr < 0.6 * median_ctr:
            issues.append(
                f"конверсия в корзину {ctr:.1%} против {median_ctr:.1%} в категории"
            )
        if len(issues) < 2:
            continue
        target_ctr = max(ctr * 1.5, median_ctr * 0.9)
        extra_orders = (p.views_14d / 2) * (target_ctr - ctr)
        effect = extra_orders * p.price * margin_rate(p)
        out.append(
            Candidate(
                rule_key="weak_card",
                type="weak_card",
                title=f"Усилить карточку «{p.name}»",
                effect_weekly=round(effect),
                confidence=min(0.85, 0.55 + 0.15 * (p.photo_count < 3) + 0.1 * (p.description_len < 200)),
                urgency=1,
                facts={
                    "Товар": p.name,
                    "Просмотры за 14 дней": p.views_14d,
                    "Конверсия в корзину": f"{ctr:.1%}",
                    "Медиана категории": f"{median_ctr:.1%}",
                    "Проблемы": "; ".join(issues),
                },
                payload={
                    "screen": "card_editor",
                    "product_id": p.id,
                    "product_name": p.name,
                    "photo_count": p.photo_count,
                    "description_len": p.description_len,
                    "fixes": issues,
                },
                product_id=p.id,
            )
        )
    return out


def rule_sales_drop(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Падение продаж: последние 14 дней против предыдущих 14."""
    out = []
    products = db.query(Product).filter(Product.farmer_id == farmer_id).all()
    for p in products:
        w0 = sales_qty(db, p.id, today - timedelta(days=28), today - timedelta(days=15))
        w1 = sales_qty(db, p.id, today - timedelta(days=14), today)
        if w0 < 20:
            continue
        drop = 1 - w1 / w0
        if drop < 0.25:
            continue
        lost_weekly_margin = ((w0 - w1) / 2) * p.price * margin_rate(p)
        effect = lost_weekly_margin * 0.5  # восстанавливаем половину потери
        out.append(
            Candidate(
                rule_key="sales_drop",
                type="sales_drop",
                title=f"Разобраться с падением продаж «{p.name}»",
                effect_weekly=round(effect),
                confidence=min(0.85, 0.6 + (drop - 0.25)),
                urgency=2,
                facts={
                    "Товар": p.name,
                    "Продажи 14 дней назад": f"{w0} шт",
                    "Продажи последние 14 дней": f"{w1} шт",
                    "Падение": f"{drop:.0%}",
                },
                payload={
                    "screen": "product_diag",
                    "product_id": p.id,
                    "product_name": p.name,
                    "drop_pct": round(drop * 100),
                    "checks": [
                        "Проверить, не поднялась ли цена выше конкурентов",
                        "Сверить актуальность фото и описания карточки",
                        "Запустить акцию на 10% для восстановления позиций",
                    ],
                },
                product_id=p.id,
            )
        )
    return out


def rule_expiry_risk(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Скоропорт: остатки не успеваем продать до конца срока годности."""
    out = []
    products = (
        db.query(Product)
        .filter(Product.farmer_id == farmer_id, Product.expires_at.isnot(None))
        .all()
    )
    for p in products:
        days_left = (p.expires_at - today).days
        if not 0 < days_left <= 3:
            continue
        vel = velocity(db, p.id, today)
        can_sell = vel * days_left
        excess = p.stock - can_sell
        if excess < 5:
            continue
        # уценка 30% удваивает скорость продаж — спасённая выручка:
        saved_units = min(excess, vel * days_left)
        effect = saved_units * p.price * 0.7
        out.append(
            Candidate(
                rule_key="expiry_risk",
                type="expiry_risk",
                title=f"Уценить «{p.name}» до истечения срока",
                effect_weekly=round(effect),
                confidence=0.75,
                urgency=3 if days_left <= 2 else 2,
                facts={
                    "Товар": p.name,
                    "Остаток": f"{p.stock} шт",
                    "Срок годности до": p.expires_at.strftime("%d.%m"),
                    "Дней осталось": days_left,
                    "Продадим по текущей скорости": f"~{can_sell:.0f} шт",
                    "Под риском списания": f"~{excess:.0f} шт",
                },
                payload={
                    "screen": "markdown_form",
                    "product_id": p.id,
                    "product_name": p.name,
                    "stock": p.stock,
                    "excess": round(excess),
                    "days_left": days_left,
                    "price": p.price,
                    "suggested_discount_pct": 30,
                },
                product_id=p.id,
            )
        )
    return out


def rule_stock_imbalance(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Затоваривание (покрытие > 45 дней) и дефицит топ-товара (< 3 дней)."""
    out = []
    products = db.query(Product).filter(Product.farmer_id == farmer_id).all()
    for p in products:
        vel = velocity(db, p.id, today)
        if vel < 0.2 or p.stock <= 0:
            continue
        cover_days = p.stock / vel
        if cover_days >= 45:
            excess_capital = (cover_days - 30) * vel * p.cost
            effect = excess_capital * 0.03  # стоимость замороженных оборотных средств
            out.append(
                Candidate(
                    rule_key="stock_imbalance",
                    type="stock_imbalance",
                    title=f"Разгрузить склад: затовар «{p.name}»",
                    effect_weekly=round(effect),
                    confidence=0.6,
                    urgency=1,
                    facts={
                        "Товар": p.name,
                        "Остаток": f"{p.stock} {p.unit}",
                        "Скорость продаж": f"{vel:.1f} шт/день",
                        "Покрытие запаса": f"{cover_days:.0f} дней",
                        "Норма": "до 30 дней",
                    },
                    payload={
                        "screen": "bundle_form",
                        "product_id": p.id,
                        "product_name": p.name,
                        "cover_days": round(cover_days),
                        "mode": "overstock",
                    },
                    product_id=p.id,
                )
            )
    # дефицит — только для товаров из топ-5 по выручке
    top_ids = [
        row[0]
        for row in (
            db.query(Sale.product_id, func.sum(Sale.revenue))
            .filter(Sale.farmer_id == farmer_id)
            .group_by(Sale.product_id)
            .order_by(func.sum(Sale.revenue).desc())
            .limit(5)
            .all()
        )
    ]
    for p in products:
        if p.id not in top_ids:
            continue
        vel = velocity(db, p.id, today)
        if vel <= 0 or p.stock > 3 * vel:
            continue
        effect = vel * 3 * p.price * margin_rate(p)
        out.append(
            Candidate(
                rule_key="stock_imbalance",
                type="stock_imbalance",
                title=f"Пополнить запас «{p.name}» — товар закончится",
                effect_weekly=round(effect),
                confidence=0.7,
                urgency=3,
                facts={
                    "Товар": p.name,
                    "Остаток": f"{p.stock} {p.unit}",
                    "Скорость продаж": f"{vel:.1f} шт/день",
                    "Запаса хватит на": f"{p.stock / vel:.1f} дней",
                },
                payload={
                    "screen": "restock_form",
                    "product_id": p.id,
                    "product_name": p.name,
                    "stock": p.stock,
                    "velocity": round(vel, 1),
                    "reorder_qty": int(vel * 14),
                    "mode": "understock",
                },
                product_id=p.id,
            )
        )
    return out


def rule_churn_risk(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Отток: повторные клиенты не покупали дольше двух своих обычных интервалов."""
    clients = (
        db.query(Client)
        .filter(Client.farmer_id == farmer_id, Client.segment == "repeat")
        .all()
    )
    lapsed: list[Client] = []
    for c in clients:
        interval = (c.last_order_at - c.first_order_at).days / max(c.total_orders, 1)
        silence = (today - c.last_order_at).days
        if silence >= max(21, 2 * interval) and silence <= 90:
            lapsed.append(c)
    if len(lapsed) < 5:
        return []
    avg_order = sum(c.total_spent / max(c.total_orders, 1) for c in lapsed) / len(lapsed)
    effect = len(lapsed) * avg_order * 0.3  # вернём 30% через рассылку с промокодом
    return [
        Candidate(
            rule_key="churn_risk",
            type="churn_risk",
            title=f"Вернуть {len(lapsed)} клиентов рассылкой с промокодом",
            effect_weekly=round(effect),
            confidence=0.7,
            urgency=2,
            facts={
                "Сегмент": "Постоянные клиенты",
                "Не покупали от": f"{min((today - c.last_order_at).days for c in lapsed)} дней",
                "Клиентов в группе": len(lapsed),
                "Средний чек клиента": f"{avg_order:.0f} ₽",
                "Ожидаемая доля возвратов": "30%",
            },
            payload={
                "screen": "mailing_form",
                "segment": "repeat_lapsed",
                "client_count": len(lapsed),
                "avg_order": round(avg_order),
                "suggested_discount_pct": 10,
                "sample_refs": [c.ext_ref for c in lapsed[:5]],
            },
            segment="repeat_lapsed",
        )
    ]


def rule_promo_gap(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Активная акция маркетплейса, к которой фермер ещё не присоединился."""
    promos = (
        db.query(Promotion)
        .filter(
            Promotion.scope == "marketplace",
            Promotion.joined.is_(False),
            Promotion.starts_at <= today,
            Promotion.ends_at >= today,
        )
        .all()
    )
    out = []
    for promo in promos:
        products = db.query(Product).filter(
            Product.farmer_id == farmer_id, Product.category == promo.category
        ).all()
        if not products:
            continue
        cat_revenue_weekly = sum(
            sales_qty(db, p.id, today - timedelta(days=13), today) * p.price / 2
            for p in products
        )
        if cat_revenue_weekly < 1000:
            continue
        days_left = (promo.ends_at - today).days
        margin = sum(margin_rate(p) * sales_qty(db, p.id, today - timedelta(days=13), today) * p.price / 2 for p in products) / cat_revenue_weekly
        effect = cat_revenue_weekly * 0.25 * margin  # рост продаж акций +25%
        out.append(
            Candidate(
                rule_key="promo_gap",
                type="promo_gap",
                title=f"Подключиться к акции «{promo.title}»",
                effect_weekly=round(effect),
                confidence=0.65,
                urgency=3 if days_left <= 7 else 2,
                facts={
                    "Акция маркетплейса": promo.title,
                    "Скидка": f"{promo.discount_pct}%",
                    "Категория": promo.category,
                    "Закончится": promo.ends_at.strftime("%d.%m"),
                    "Ваша выручка в категории": f"{cat_revenue_weekly:.0f} ₽/нед",
                    "Товаров подходит": len(products),
                },
                payload={
                    "screen": "promo_join",
                    "promo_id": promo.id,
                    "promo_title": promo.title,
                    "discount_pct": promo.discount_pct,
                    "category": promo.category,
                    "product_ids": [p.id for p in products],
                    "product_names": [p.name for p in products],
                    "ends_at": promo.ends_at.isoformat(),
                },
            )
        )
    return out


def rule_pricing(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    """Цена выше медианы категории при слабой конверсии — или заметно ниже."""
    out = []
    products = db.query(Product).filter(Product.farmer_id == farmer_id).all()
    for p in products:
        median = category_median_price(db, p.category)
        if not median or p.views_14d < 50:
            continue
        ctr = p.cart_14d / max(p.views_14d, 1)
        median_ctr = category_median_ctr(db, p.category) or 0.06
        vel = velocity(db, p.id, today)
        if p.price > 1.15 * median and ctr < 0.8 * median_ctr and vel >= 0.2:
            suggested = round(p.price * 0.93)
            effect = vel * p.price * margin_rate(p) * 0.15
            out.append(
                Candidate(
                    rule_key="pricing",
                    type="pricing",
                    title=f"Скорректировать цену «{p.name}»",
                    effect_weekly=round(effect),
                    confidence=0.55,
                    urgency=1,
                    facts={
                        "Товар": p.name,
                        "Ваша цена": f"{p.price:.0f} ₽",
                        "Медиана категории": f"{median:.0f} ₽",
                        "Дороже рынка на": f"{(p.price / median - 1):.0%}",
                        "Конверсия в корзину": f"{ctr:.1%} при {median_ctr:.1%} в категории",
                    },
                    payload={
                        "screen": "price_form",
                        "product_id": p.id,
                        "product_name": p.name,
                        "current_price": p.price,
                        "median_price": round(median),
                        "suggested_price": suggested,
                        "direction": "down",
                    },
                    product_id=p.id,
                )
            )
        elif p.price < 0.85 * median and vel >= 0.5:
            suggested = round(p.price * 1.05)
            effect = vel * p.price * 0.05 * 0.97
            out.append(
                Candidate(
                    rule_key="pricing",
                    type="pricing",
                    title=f"Поднять цену «{p.name}» до рынка",
                    effect_weekly=round(effect),
                    confidence=0.55,
                    urgency=1,
                    facts={
                        "Товар": p.name,
                        "Ваша цена": f"{p.price:.0f} ₽",
                        "Медиана категории": f"{median:.0f} ₽",
                        "Дешевле рынка на": f"{(1 - p.price / median):.0%}",
                        "Спрос устойчивый": f"{vel:.1f} шт/день",
                    },
                    payload={
                        "screen": "price_form",
                        "product_id": p.id,
                        "product_name": p.name,
                        "current_price": p.price,
                        "median_price": round(median),
                        "suggested_price": suggested,
                        "direction": "up",
                    },
                    product_id=p.id,
                )
            )
    return out


RULES = [
    rule_weak_card,
    rule_sales_drop,
    rule_expiry_risk,
    rule_stock_imbalance,
    rule_churn_risk,
    rule_promo_gap,
    rule_pricing,
]


def collect_candidates(db: Session, farmer_id: int, today: date) -> list[Candidate]:
    candidates: list[Candidate] = []
    for rule in RULES:
        candidates.extend(rule(db, farmer_id, today))
    return candidates
