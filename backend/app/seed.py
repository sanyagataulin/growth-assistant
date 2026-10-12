"""Детерминированный генератор обезличенных данных одного магазина фермера.

Anchor-дата = дата сеяния. Все «сегодняшние» проблемы зашиты относительно неё,
поэтому переключатель дня на фронте показывает живое изменение топ-3.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Action, Client, Farmer, Product, Promotion, Sale
from app.security import hash_password

SEED = 42

# name, category, unit, price, margin, velocity, stock, expires_offset, photo, desc_len, views, cart
CATALOG = [
    # молочные напитки: молоко с зашитым падением продаж и завышенной ценой
    ("Молоко 2,5%", "Молочные напитки", "л", 119, 0.35, 10, 45, 5, 4, 350, 800, 19),
    ("Кефир 1%", "Молочные напитки", "л", 95, 0.35, 6, 30, 5, 5, 420, 400, 26),
    ("Ряженка 4%", "Молочные напитки", "л", 99, 0.35, 5, 28, 5, 4, 380, 300, 19),
    # молочные продукты: творог — скоропорт под уценку, сметана — затовар
    ("Творог 5%", "Молочные продукты", "шт", 149, 0.36, 5, 60, 2, 5, 480, 520, 31),
    ("Сметана 20%", "Молочные продукты", "шт", 129, 0.34, 2, 95, 6, 5, 460, 260, 15),
    ("Масло сливочное", "Молочные продукты", "шт", 259, 0.34, 2, 26, None, 5, 520, 180, 11),
    ("Сыр молодой", "Молочные продукты", "шт", 289, 0.34, 3, 34, None, 6, 540, 320, 19),
    # овощи и зелень — большая категория под акцию маркетплейса
    ("Картофель", "Овощи и зелень", "кг", 49, 0.4, 10, 120, None, 4, 300, 700, 42),
    ("Морковь", "Овощи и зелень", "кг", 45, 0.4, 8, 90, None, 4, 320, 560, 34),
    ("Свёкла", "Овощи и зелень", "кг", 42, 0.4, 6, 70, None, 4, 300, 420, 25),
    ("Капуста белокочанная", "Овощи и зелень", "шт", 55, 0.38, 5, 60, None, 4, 310, 350, 21),
    ("Лук репчатый", "Овощи и зелень", "кг", 38, 0.4, 7, 85, None, 4, 290, 490, 29),
    ("Огурцы", "Овощи и зелень", "уп", 120, 0.42, 5, 40, 6, 5, 380, 380, 23),
    ("Помидоры", "Овощи и зелень", "уп", 140, 0.42, 4, 36, 5, 5, 390, 320, 18),
    # мёд: гречишный — слабая карточка
    ("Мёд гречишный", "Мёд и пасека", "б", 450, 0.76, 3, 50, None, 1, 80, 900, 14),
    ("Мёд цветочный", "Мёд и пасека", "б", 420, 0.75, 2, 30, None, 5, 450, 500, 30),
    ("Прополис настойка", "Мёд и пасека", "фл", 350, 0.57, 1, 12, None, 4, 400, 200, 8),
    # мясо и яйцо
    ("Фарш говяжий", "Мясо и яйцо", "уп", 390, 0.38, 4, 30, 5, 5, 480, 460, 28),
    ("Яйцо куриное С0", "Мясо и яйцо", "дес", 110, 0.32, 8, 70, 12, 4, 330, 640, 40),
    ("Крыло куриное", "Мясо и яйцо", "кг", 220, 0.36, 6, 55, 7, 4, 350, 480, 29),
    # выпечка и прочее: хлеб — дефицит топ-товара
    ("Хлеб на закваске", "Выпечка", "бух", 95, 0.42, 9, 12, None, 4, 360, 720, 43),
    ("Варенье яблочное", "Консервация", "б", 180, 0.58, 2, 40, None, 4, 420, 240, 14),
    ("Тыквенные семечки", "Консервация", "уп", 130, 0.54, 2, 45, None, 4, 400, 260, 13),
]

# 16 отточных постоянных клиентов — не покупают с day0-25..day0-45
CHURNED_COUNT = 16
CLIENTS_TOTAL = 200


def seed(db: Session) -> None:
    rng = random.Random(SEED)
    day0 = date.today()

    farmer = Farmer(
        login="farmer",
        password_hash=hash_password("farmer123"),
        full_name="Сергей Ковалёв",
        shop_name="Ферма «Луговое»",
        region="Ленинградская область",
    )
    db.add(farmer)
    db.flush()

    products: list[Product] = []
    for name, cat, unit, price, margin, vel, stock, exp_off, photo, desc_len, views, cart in CATALOG:
        p = Product(
            farmer_id=farmer.id,
            name=name,
            category=cat,
            unit=unit,
            price=price,
            cost=round(price * (1 - margin), 2),
            stock=stock,
            produced_at=day0 - timedelta(days=3) if exp_off is not None else None,
            expires_at=day0 + timedelta(days=exp_off) if exp_off is not None else None,
            description_len=desc_len,
            photo_count=photo,
            views_14d=views,
            cart_14d=cart,
        )
        db.add(p)
        products.append(p)
    db.flush()

    # ---- клиенты -------------------------------------------------------
    clients: list[Client] = []
    for i in range(1, CLIENTS_TOTAL + 1):
        churned = i <= CHURNED_COUNT
        if churned:
            first = day0 - timedelta(days=rng.randint(50, 89))
            last = day0 - timedelta(days=rng.randint(25, 45))
            orders = rng.randint(4, 12)
        elif i <= CHURNED_COUNT + 45:  # новые
            first = day0 - timedelta(days=rng.randint(2, 30))
            last = max(first, day0 - timedelta(days=rng.randint(0, 14)))
            orders = rng.randint(1, 2)
        else:
            first = day0 - timedelta(days=rng.randint(40, 89))
            last = day0 - timedelta(days=rng.randint(0, 16))
            orders = rng.randint(2, 18)
        c = Client(
            farmer_id=farmer.id,
            ext_ref=f"Клиент #{1000 + i}",
            segment="new",
            first_order_at=first,
            last_order_at=max(last, first),
            total_orders=orders,
            total_spent=0.0,
        )
        db.add(c)
        clients.append(c)
    db.flush()

    # пул клиентов, из которого берём продажи: отточные исчезают после day0-25
    active_until = {c.id: (day0 - timedelta(days=25)) for c in clients[:CHURNED_COUNT]}

    # ---- продажи за 90 дней --------------------------------------------
    sales: list[Sale] = []
    weights = [70, 20, 10]  # repeat / new / single — примерно
    for p, row in zip(products, CATALOG):
        base_vel = row[5]
        for offset in range(89, 0, -1):
            day = day0 - timedelta(days=offset)
            vel = base_vel
            if p.name == "Молоко 2,5%" and offset <= 15:
                vel = 5  # зашитое падение продаж
            n = max(0, int(rng.gauss(vel, max(1, vel * 0.35))))
            for _ in range(n):
                bucket = rng.choices(["repeat", "new", "single"], weights=weights)[0]
                pool = [
                    c
                    for c in clients
                    if (c.id not in active_until or day <= active_until[c.id])
                    and (
                        (bucket == "repeat" and c.total_orders >= 3)
                        or (bucket == "new" and c.total_orders <= 2 and c.first_order_at <= day)
                        or (bucket == "single" and c.total_orders >= 3)
                    )
                ]
                client = rng.choice(pool or clients)
                qty = rng.choices([1, 2, 3], weights=[70, 22, 8])[0]
                sales.append(
                    Sale(
                        farmer_id=farmer.id,
                        product_id=p.id,
                        client_id=client.id,
                        day=day,
                        qty=qty,
                        unit_price=p.price,
                        revenue=round(qty * p.price, 2),
                    )
                )
    for chunk in range(0, len(sales), 1000):
        db.bulk_save_objects(sales[chunk : chunk + 1000])
    db.flush()

    # агрегаты клиентов из фактических продаж
    from sqlalchemy import func

    stats = (
        db.query(
            Sale.client_id,
            func.count(Sale.id),
            func.min(Sale.day),
            func.max(Sale.day),
            func.sum(Sale.revenue),
        )
        .filter(Sale.farmer_id == farmer.id)
        .group_by(Sale.client_id)
        .all()
    )
    for client_id, orders, first, last, spent in stats:
        c = next(c for c in clients if c.id == client_id)
        c.total_orders = orders
        c.first_order_at = first
        c.last_order_at = last
        c.total_spent = round(float(spent), 2)
        if (day0 - first).days <= 30:
            c.segment = "new"
        elif orders >= 3:
            c.segment = "repeat"
        else:
            c.segment = "single"
    db.flush()

    # ---- акции ----------------------------------------------------------
    db.add_all(
        [
            Promotion(
                scope="marketplace",
                title="Неделя урожая",
                description="Осенняя акция маркетплейса: скидки на овощи и зелень local-производителей.",
                discount_pct=15,
                category="Овощи и зелень",
                starts_at=day0 - timedelta(days=3),
                ends_at=day0 + timedelta(days=11),
                joined=False,
            ),
            Promotion(
                scope="marketplace",
                title="Зимняя ярмарка",
                description="Предновогодняя распродажа local-продуктов.",
                discount_pct=20,
                category=None,
                starts_at=day0 + timedelta(days=20),
                ends_at=day0 + timedelta(days=30),
                joined=False,
            ),
            Promotion(
                farmer_id=farmer.id,
                scope="shop",
                title="Дегустация сыра",
                description="Скидка 10% на сырную линейку.",
                discount_pct=10,
                category="Молочные продукты",
                starts_at=day0 - timedelta(days=40),
                ends_at=day0 - timedelta(days=33),
                joined=True,
                result_revenue=38000.0,
                result_uplift_pct=22.0,
            ),
            Promotion(
                farmer_id=farmer.id,
                scope="shop",
                title="Овощная неделя",
                description="Скидка 8% на овощи при заказе от 500 ₽.",
                discount_pct=8,
                category="Овощи и зелень",
                starts_at=day0 - timedelta(days=60),
                ends_at=day0 - timedelta(days=53),
                joined=True,
                result_revenue=21000.0,
                result_uplift_pct=15.0,
            ),
        ]
    )

    # ---- предыстория журнала (чтобы журнал не был пустым) ---------------
    def product_by_name(name: str) -> Product:
        return next(p for p in products if p.name == name)

    history = [
        Action(
            farmer_id=farmer.id,
            day=day0 - timedelta(days=3),
            rule_key="weak_card",
            type="weak_card",
            title="Улучшить карточку «Мёд цветочный»",
            product_id=product_by_name("Мёд цветочный").id,
            facts={
                "Товар": "Мёд цветочный",
                "Конверсия в корзину": "6.0%",
                "Медиана категории": "5.0%",
                "Проблемы": "мало фото в карточке",
            },
            effect_weekly=1200,
            confidence=0.7,
            urgency=1,
            score=840,
            payload={"screen": "card_editor", "product_name": "Мёд цветочный"},
            texts={
                "headline": "Усилить карточку «Мёд цветочный»",
                "why": "В карточке мало фото — покупатели не доверяют и уходят.",
                "plan": ["Добавить фото", "Расширить описание", "Проверить цену"],
                "effect_note": "До +1200 ₽/нед маржи.",
            },
            texts_source="template",
            status="completed",
            feedback="useful",
            completed_at=datetime_utc(day0 - timedelta(days=3), 12),
        ),
        Action(
            farmer_id=farmer.id,
            day=day0 - timedelta(days=2),
            rule_key="expiry_risk",
            type="expiry_risk",
            title="Уценить «Огурцы» до истечения срока",
            product_id=product_by_name("Огурцы").id,
            facts={
                "Товар": "Огурцы",
                "Остаток": "40 уп",
                "Срок годности до": "12.10",
                "Под риском списания": "~18 уп",
            },
            effect_weekly=940,
            confidence=0.75,
            urgency=3,
            score=2115,
            payload={"screen": "markdown_form", "product_name": "Огурцы", "suggested_discount_pct": 30},
            texts={
                "headline": "Уценить «Огурцы» до истечения срока",
                "why": "Партия не успевает распродаться — уценка спасёт выручку.",
                "plan": ["Поставить уценку 30%", "Добавить в акцию дня", "Проверить остаток через 2 дня"],
                "effect_note": "Спасаем ~940 ₽ выручки вместо списания.",
            },
            texts_source="template",
            status="completed",
            feedback="useful",
            completed_at=datetime_utc(day0 - timedelta(days=2), 10),
        ),
        Action(
            farmer_id=farmer.id,
            day=day0 - timedelta(days=2),
            rule_key="sales_drop",
            type="sales_drop",
            title="Разобраться с падением продаж «Морковь»",
            product_id=product_by_name("Морковь").id,
            facts={"Товар": "Морковь", "Падение": "30%"},
            effect_weekly=520,
            confidence=0.6,
            urgency=2,
            score=624,
            payload={"screen": "product_diag", "product_name": "Морковь"},
            texts={
                "headline": "Разобраться с падением продаж «Морковь»",
                "why": "Продажи упали на 30% за две недели.",
                "plan": ["Проверить цену", "Обновить карточку", "Включить акцию"],
                "effect_note": "Возврат ~520 ₽/нед маржи.",
            },
            texts_source="template",
            status="rejected",
            rejection_reason="Не согласен с расчётом эффекта",
        ),
        Action(
            farmer_id=farmer.id,
            day=day0 - timedelta(days=1),
            rule_key="pricing",
            type="pricing",
            title="Поднять цену «Прополис настойка» до рынка",
            product_id=product_by_name("Прополис настойка").id,
            facts={"Товар": "Прополис настойка", "Ваша цена": "350 ₽", "Медиана категории": "430 ₽"},
            effect_weekly=350,
            confidence=0.55,
            urgency=1,
            score=193,
            payload={"screen": "price_form", "product_name": "Прополис настойка", "direction": "up"},
            texts={
                "headline": "Поднять цену «Прополис настойка» до рынка",
                "why": "Товар продаётся заметно дешевле рынка при устойчивом спросе.",
                "plan": ["Поднять цену на 5%", "Следить 3 дня", "Откатить при падении"],
                "effect_note": "+350 ₽/нед маржи.",
            },
            texts_source="template",
            status="completed",
            feedback="useful",
            completed_at=datetime_utc(day0 - timedelta(days=1), 9),
        ),
        Action(
            farmer_id=farmer.id,
            day=day0 - timedelta(days=1),
            rule_key="stock_imbalance",
            type="stock_imbalance",
            title="Разгрузить склад: затовар «Тыквенные семечки»",
            product_id=product_by_name("Тыквенные семечки").id,
            facts={"Товар": "Тыквенные семечки", "Покрытие запаса": "48 дней"},
            effect_weekly=340,
            confidence=0.6,
            urgency=1,
            score=204,
            payload={"screen": "bundle_form", "product_name": "Тыквенные семечки", "mode": "overstock"},
            texts={
                "headline": "Разгрузить склад: затовар «Тыквенные семечки»",
                "why": "Запас покрывает 48 дней продаж при норме до 30.",
                "plan": ["Собрать набор", "Акция 15% на 5 дней", "Приостановить пополнение"],
                "effect_note": "Освобождаем ~340 ₽/нед замороженных средств.",
            },
            texts_source="template",
            status="rejected",
            rejection_reason="Не могу сейчас",
        ),
    ]
    db.add_all(history)
    db.commit()


def datetime_utc(day: date, hour: int):
    from datetime import datetime, timezone

    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)
