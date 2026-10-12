"""Тексты действий: LLM через LangChain -> OpenRouter, с fallback на шаблоны.

LLM не влияет на отбор и ранжирование действий (см. ADR-0001) — только на
формулировки. Любая ошибка сети/ключа незаметно переключает на шаблоны.
"""
from __future__ import annotations

import json
import logging

from app.config import get_settings
from app.models import Action

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — деловой ассистент фермера на маркетплейсе локальных продуктов. "
    "Тебе дают сигнал из данных магазина и расчёт эффекта. Напиши короткие, "
    "конкретные формулировки на русском языке, без канцелярита и без выдуманных "
    "фактов: используй только данные из сигнала. Ответ — строго JSON вида "
    '{"headline": "...", "why": "...", "plan": ["...", "...", "..."], "effect_note": "..."}. '
    "headline — до 70 знаков; why — 2 предложения о причине; plan — 3 коротких шага; "
    "effect_note — одна фраза про ожидаемый эффект в рублях в неделю."
)


def ensure_texts(action: Action) -> dict:
    if action.texts:
        return action.texts
    settings = get_settings()
    use_llm = settings.llm_enabled and bool(settings.openrouter_api_key)
    texts, source = (
        _llm_texts(action, settings)
        if use_llm
        else (_template_texts(action), "template")
    )
    action.texts = texts
    action.texts_source = source
    return texts


def _llm_texts(action: Action, settings) -> tuple[dict, str]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.llm_base_url,
            timeout=15,
            max_retries=1,
        )
        user = (
            f"Сигнал: {json.dumps(action.facts, ensure_ascii=False)}\n"
            f"Действие: {action.title}\n"
            f"Ожидаемый эффект: {action.effect_weekly:.0f} ₽/нед "
            f"(уверенность {action.confidence:.0%}, срочность {action.urgency}/3)."
        )
        raw = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]).content
        if isinstance(raw, list):  # некоторые модели возвращают список блоков
            raw = "".join(block.get("text", "") for block in raw if isinstance(block, dict))
        texts = json.loads(str(raw).strip().removeprefix("```json").removesuffix("```").strip())
        if not all(k in texts for k in ("headline", "why", "plan", "effect_note")):
            raise ValueError("неполный ответ LLM")
        return texts, "llm"
    except Exception as exc:  # сеть, ключ, формат — тихо падаем на шаблоны
        logger.warning("LLM недоступен, использую шаблоны: %s", exc)
        return _template_texts(action), "template"


def _template_texts(action: Action) -> dict:
    facts = action.facts
    tpl = _TEMPLATES.get(action.type, _generic_template)
    return tpl(action, facts)


def _fmt(v) -> str:
    return v if isinstance(v, str) else str(v)


def _generic_template(action: Action, facts: dict) -> dict:
    return {
        "headline": action.title,
        "why": "Данные магазина показывают: " + "; ".join(f"{k}: {_fmt(v)}" for k, v in list(facts.items())[:3]) + ".",
        "plan": ["Открыть раздел выполнения", "Проверить параметры действия", "Подтвердить и завершить"],
        "effect_note": f"Ожидаемый эффект ~{action.effect_weekly:.0f} ₽/нед.",
    }


_TEMPLATES: dict[str, callable] = {
    "weak_card": lambda a, f: {
        "headline": f"Усилить карточку «{f.get('Товар', '')}» — теряете покупки",
        "why": f"{f.get('Проблемы', 'Карточка слабая')}. Карточку смотрят, но до корзины покупатели не доходят.",
        "plan": [
            "Добавить 3–5 живых фото продукта и фермы",
            "Расширить описание до 400+ знаков: состав, вкус, как хранить",
            "Проверить, что цена и остатки актуальны",
        ],
        "effect_note": f"До +{a.effect_weekly:.0f} ₽/нед маржи за счёт роста конверсии карточки.",
    },
    "sales_drop": lambda a, f: {
        "headline": f"«{f.get('Товар', '')}»: продажи упали на {f.get('Падение', '')}",
        "why": (
            f"Было {f.get('Продажи 14 дней назад', '—')} за две недели, стало "
            f"{f.get('Продажи последние 14 дней', '—')}. Обычно так бывает после роста цены "
            "или когда карточку обгоняют конкуренты."
        ),
        "plan": [
            "Сверить цену с похожими товарами категории",
            "Обновить фото и первое предложение описания",
            "Включить акцию 10% на 7 дней для возврата позиций",
        ],
        "effect_note": f"Возврат ~{a.effect_weekly:.0f} ₽/нед маржи при восстановлении продаж.",
    },
    "expiry_risk": lambda a, f: {
        "headline": f"«{f.get('Товар', '')}»: {f.get('Под риском списания', '')} уйдут в списание",
        "why": (
            f"Срок годности до {f.get('Срок годности до', '—')}, осталось {f.get('Дней осталось', '—')} дн. "
            f"По текущей скорости продадим ~{f.get('Продадим по текущей скорости', '—')} из {f.get('Остаток', '—')}."
        ),
        "plan": [
            "Поставить уценку 30% на остаток партии",
            "Добавить товар в акцию дня на маркетплейсе",
            "Через 2 дня проверить остаток и снять уценку, если распродано",
        ],
        "effect_note": f"Спасаем ~{a.effect_weekly:.0f} ₽ выручки вместо списания.",
    },
    "stock_imbalance": lambda a, f: (
        {
            "headline": f"Пополнить «{f.get('Товар', '')}» — хватит на {f.get('Запаса хватит на', '—')}",
            "why": (
                f"Топ-товар: остаток {f.get('Остаток', '—')} при скорости {f.get('Скорость продаж', '—')}. "
                "Скоро дефицит — потеряете продажи и позиции в выдаче."
            ),
            "plan": [
                f"Пополнить партию на ~2 недели продаж",
                "Проверить план производства на неделю",
                "Следить за покрытием запаса в кабинете",
            ],
            "effect_note": f"Сохраняем ~{a.effect_weekly:.0f} ₽/нед маржи от недопродаж.",
        }
        if a.payload.get("mode") == "understock"
        else {
            "headline": f"Разгрузить склад: «{f.get('Товар', '')}» залежался",
            "why": (
                f"Запас покрывает {f.get('Покрытие запаса', '—')} продаж при норме до 30 дней. "
                "Деньги заморожены, а часть товара может не дождаться покупателя."
            ),
            "plan": [
                "Собрать набор из затовара с ходовым товаром",
                "Включить акцию 15% на 5 дней",
                "Приостановить пополнение этого товара",
            ],
            "effect_note": f"Освобождаем ~{a.effect_weekly:.0f} ₽/нед замороженных средств.",
        }
    ),
    "churn_risk": lambda a, f: {
        "headline": f"Вернуть {f.get('Клиентов в группе', '')} клиентов, которые от вас ушли",
        "why": (
            f"Постоянные клиенты не покупали от {f.get('Не покупали от', '—')} — это дольше их "
            "обычного цикла. Без напоминания они, скорее всего, уйдут к другим магазинам."
        ),
        "plan": [
            f"Собрать рассылку для сегмента с промокодом {10}%",
            "Отправить сегодня до 18:00 — вечернее время лучшее для отклика",
            "Через 3 дня посмотреть долю вернувшихся в журнале",
        ],
        "effect_note": f"Ожидаем ~{a.effect_weekly:.0f} ₽/нед от возврата 30% сегмента.",
    },
    "promo_gap": lambda a, f: {
        "headline": f"Присоединиться к акции «{f.get('Акция маркетплейса', '')}»",
        "why": (
            f"Маркетплейс даёт скидку {f.get('Скидка', '—')} на категорию «{f.get('Категория', '—')}», "
            f"но ваших {f.get('Товаров подходит', '—')} товаров в ней нет — конкуренты забирают ваш трафик. "
            f"Акция заканчивается {f.get('Закончится', '—')}."
        ),
        "plan": [
            "Выбрать товары категории для участия",
            "Подтвердить скидку и остатки",
            "Проверить рост заказов через 2 дня",
        ],
        "effect_note": f"До +{a.effect_weekly:.0f} ₽/нед маржи от праздничного трафика.",
    },
    "pricing": lambda a, f: (
        {
            "headline": f"«{f.get('Товар', '')}»: цена выше рынка на {f.get('Дороже рынка на', '')}",
            "why": (
                f"Ваша цена {f.get('Ваша цена', '—')} против {f.get('Медиана категории', '—')} в категории, "
                f"конверсия {f.get('Конверсия в корзину', '—')} — покупатели уходят к дешевле."
            ),
            "plan": [
                "Снизить цену до уровня чуть выше медианы",
                "Проверить, не выросла ли себестоимость",
                "Сравнить конверсию через 5 дней",
            ],
            "effect_note": f"~{a.effect_weekly:.0f} ₽/нед за счёт возврата конверсии.",
        }
        if a.payload.get("direction") == "down"
        else {
            "headline": f"«{f.get('Товар', '')}» продаётся ниже рынка",
            "why": (
                f"Цена {f.get('Ваша цена', '—')} при медиане категории {f.get('Медиана категории', '—')}, "
                f"спрос устойчивый ({f.get('Спрос устойчивый', '—')}). Вы отдаёте маржу зря."
            ),
            "plan": [
                "Поднять цену на 5%",
                "Следить за скоростью продаж 3 дня",
                "Откатить при падении продаж",
            ],
            "effect_note": f"+{a.effect_weekly:.0f} ₽/нед маржи почти без потери продаж.",
        }
    ),
}
