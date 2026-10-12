"""API помощника: топ-3 на день, подтверждение, отклонение, обратная связь, журнал, правила."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_farmer
from app.engine.prioritize import _serialize, build_today, complete_action, reject_action
from app.models import Action, Farmer

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

TARGET_SCREENS = {
    "card_editor": "Редактор карточки товара",
    "markdown_form": "Уценка партии",
    "mailing_form": "Рассылка клиентам",
    "promo_join": "Подключение к акции",
    "product_diag": "Диагностика товара",
    "bundle_form": "Сборка набора",
    "restock_form": "Пополнение запаса",
    "price_form": "Изменение цены",
}


@router.get("/today")
def today(
    day: str | None = Query(None, description="демо-дата YYYY-MM-DD"),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    today_date = date.today()
    target = today_date
    if day:
        try:
            target = date.fromisoformat(day)
        except ValueError:
            raise HTTPException(400, "Дата должна быть в формате YYYY-MM-DD")
        if abs((target - today_date).days) > 7:
            raise HTTPException(400, "Демо-дата не дальше ±7 дней от сегодня")
    return build_today(db, farmer, target)


@router.post("/{action_id}/confirm")
def confirm(action_id: int, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    action = _get_action(db, action_id, farmer)
    if action.status == "rejected":
        raise HTTPException(409, "Действие отклонено и не может быть выполнено")
    action = complete_action(db, action)
    payload = dict(action.payload)
    return {
        "action": _serialize(action, action.texts or {}),
        "target_screen": {
            "key": payload.get("screen", "generic"),
            "title": TARGET_SCREENS.get(payload.get("screen", ""), "Выполнение действия"),
            "params": payload,
        },
    }


class RejectIn(BaseModel):
    reason: str


REJECT_REASONS = ["Не согласен с расчётом эффекта", "Не могу сейчас", "Уже сделал по-своему", "Не актуально"]


@router.post("/{action_id}/reject")
def reject(action_id: int, body: RejectIn, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    if body.reason not in REJECT_REASONS:
        raise HTTPException(400, f"Причина должна быть одной из: {', '.join(REJECT_REASONS)}")
    action = _get_action(db, action_id, farmer)
    action = reject_action(db, action, body.reason)
    return {"action": _serialize(action, action.texts or {})}


class FeedbackIn(BaseModel):
    feedback: str  # useful | not_useful


@router.post("/{action_id}/feedback")
def feedback(action_id: int, body: FeedbackIn, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    if body.feedback not in ("useful", "not_useful"):
        raise HTTPException(400, "feedback должен быть useful или not_useful")
    action = _get_action(db, action_id, farmer)
    action.feedback = body.feedback
    db.commit()
    return {"action": _serialize(action, action.texts or {})}


@router.get("/journal")
def journal(
    days: int = Query(14, ge=1, le=90),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(Action)
        .filter(Action.farmer_id == farmer.id, Action.day >= start)
        .order_by(Action.day.desc(), Action.score.desc())
        .all()
    )
    status_names = {"proposed": "Предложено", "completed": "Выполнено", "rejected": "Отклонено"}
    completed_effect = sum(a.effect_weekly for a in rows if a.status == "completed")
    decisions = [a for a in rows if a.status in ("completed", "rejected")]
    accepted_rate = (
        round(100 * len([a for a in decisions if a.status == "completed"]) / len(decisions))
        if decisions
        else 0
    )
    useful = len([a for a in rows if a.feedback == "useful"])
    return {
        "metrics": {
            "proposed": len(rows),
            "completed": len([a for a in rows if a.status == "completed"]),
            "rejected": len([a for a in rows if a.status == "rejected"]),
            "completed_effect_weekly": round(completed_effect),
            "accepted_rate": accepted_rate,
            "useful_votes": useful,
        },
        "actions": [
            {
                **_serialize(a, a.texts or {}),
                "status_name": status_names.get(a.status, a.status),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.astimezone(timezone.utc).isoformat() if a.completed_at else None,
            }
            for a in rows
        ],
    }


@router.get("/rules")
def rules():
    """Прозрачность: что помощник умеет замечать и как ранжирует."""
    settings = get_settings()
    return {
        "formula": "Score = Ожидаемый эффект (₽/нед) × Уверенность (0–1) × Срочность (1–3)",
        "filters": [
            f"Действие проходит, если эффект ≥ {settings.effect_threshold:.0f} ₽/нед",
            f"Уверенность ≥ {settings.confidence_threshold:.0%}, иначе правило молчит",
            "Не более одного действия каждого типа в топ-3",
            "Отклонённое не возвращается 14 дней, выполненное — 7 дней",
            "Одно действие не дублируется по объекту (товар или сегмент)",
        ],
        "top_size": 3,
        "rules": [
            {
                "key": "weak_card",
                "name": "Слабая карточка",
                "signal": "Мало фото, короткое описание или конверсия в корзину сильно ниже медианы категории",
                "data": "Карточки товаров: фото, описание, просмотры, корзины за 14 дней",
                "effect": "Доп. заказы (рост конверсии до нормы) × цена × маржинальность",
            },
            {
                "key": "sales_drop",
                "name": "Падение продаж",
                "signal": "Продажи за последние 14 дней упали на 25%+ против предыдущих 14",
                "data": "История продаж по дням",
                "effect": "Возврат 50% потерянной недельной маржи",
            },
            {
                "key": "expiry_risk",
                "name": "Скоропорт к списанию",
                "signal": "Остатки не будут проданы до конца срока годности (окно ≤ 3 дней)",
                "data": "Остатки, сроки годности, скорость продаж",
                "effect": "Выручка спасённых уценкой единиц (−30% к цене)",
            },
            {
                "key": "stock_imbalance",
                "name": "Затоваривание и дефицит",
                "signal": "Покрытие запаса > 45 дней у обычных товаров или < 3 дней у топ-5",
                "data": "Остатки, скорость продаж, выручка товаров",
                "effect": "Замороженные средства (затовар) или сохранённая маржа топ-товара (дефицит)",
            },
            {
                "key": "churn_risk",
                "name": "Отток клиентов",
                "signal": "Постоянные клиенты не покупали дольше двух своих обычных интервалов",
                "data": "Клиентская база: последние заказы, интервалы, средний чек",
                "effect": "Клиентов × средний чек × 30% (возврат рассылкой)",
            },
            {
                "key": "promo_gap",
                "name": "Неучастие в акции маркетплейса",
                "signal": "Идёт акция маркетплейса в вашей категории, а вы к ней не подключились",
                "data": "Календарь акций маркетплейса, выручка по категории",
                "effect": "Выручка категории × 25% (рост в акции) × маржинальность",
            },
            {
                "key": "pricing",
                "name": "Ценовой сигнал",
                "signal": "Цена выше медианы категории при слабой конверсии — или заметно ниже при устойчивом спросе",
                "data": "Цены всех товаров категории, конверсия карточек",
                "effect": "Возврат конверсии или дополнительная маржа от выравнивания цены",
            },
        ],
    }


def _get_action(db: Session, action_id: int, farmer: Farmer) -> Action:
    action = db.get(Action, action_id)
    if action is None or action.farmer_id != farmer.id:
        raise HTTPException(404, "Действие не найдено")
    return action
