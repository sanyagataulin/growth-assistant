"""Приоритизация: фильтры -> скоринг -> топ-3 с ограничениями."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.signals import Candidate, collect_candidates
from app.llm.texts import ensure_texts
from app.models import Action, Farmer


def _excluded_object_keys(db: Session, farmer_id: int, today: date) -> set[tuple]:
    """Объекты, которые недавно отклонили (14 дней) или уже выполнили (7 дней)."""
    keys: set[tuple] = set()
    rows = (
        db.query(Action)
        .filter(Action.farmer_id == farmer_id, Action.status.in_(["rejected", "completed"]))
        .all()
    )
    for a in rows:
        age = (today - a.day).days
        if a.status == "rejected" and age <= 14:
            keys.add((a.type, a.product_id, a.segment))
        if a.status == "completed" and age <= 7:
            keys.add((a.type, a.product_id, a.segment))
    return keys


def _persist(db: Session, farmer: Farmer, today: date, cand: Candidate) -> Action:
    row = (
        db.query(Action)
        .filter(
            Action.farmer_id == farmer.id,
            Action.day == today,
            Action.rule_key == cand.rule_key,
            Action.product_id == cand.product_id,
            Action.segment == cand.segment,
        )
        .first()
    )
    if row is None:
        row = Action(
            farmer_id=farmer.id,
            day=today,
            rule_key=cand.rule_key,
            type=cand.type,
            title=cand.title,
            product_id=cand.product_id,
            segment=cand.segment,
            facts=cand.facts,
            effect_weekly=cand.effect_weekly,
            confidence=cand.confidence,
            urgency=cand.urgency,
            score=cand.score,
            payload=cand.payload,
            status="proposed",
        )
        db.add(row)
        db.flush()
    return row


def build_today(db: Session, farmer: Farmer, today: date) -> dict:
    settings = get_settings()
    candidates = collect_candidates(db, farmer.id, today)

    # фильтр достаточности: эффект и уверенность выше порога
    enough = [
        c
        for c in candidates
        if c.effect_weekly >= settings.effect_threshold
        and c.confidence >= settings.confidence_threshold
    ]

    # дедупликация: одно действие на объект (тип + товар/сегмент)
    best: dict[tuple, Candidate] = {}
    for c in enough:
        key = c.object_key
        if key not in best or c.score > best[key].score:
            best[key] = c

    # исключаем недавно отклонённое и выполненное
    excluded = _excluded_object_keys(db, farmer.id, today)
    pool = sorted(
        (c for c in best.values() if c.object_key not in excluded),
        key=lambda c: c.score,
        reverse=True,
    )

    # топ-3: не более одного действия каждого типа, добираем лучшими оставшимися
    top: list[Candidate] = []
    seen_types: set[str] = set()
    for c in pool:
        if c.type in seen_types:
            continue
        top.append(c)
        seen_types.add(c.type)
        if len(top) == 3:
            break
    if len(top) < 3:
        chosen = {(c.type, c.product_id, c.segment) for c in top}
        for c in pool:
            if (c.type, c.product_id, c.segment) in chosen:
                continue
            top.append(c)
            chosen.add((c.type, c.product_id, c.segment))
            if len(top) == 3:
                break

    actions = []
    for cand in top:
        row = _persist(db, farmer, today, cand)
        texts = ensure_texts(row)
        db.commit()
        actions.append(_serialize(row, texts))

    return {
        "date": today.isoformat(),
        "actions": actions,
        "candidates_found": len(candidates),
        "candidates_passed": len(pool),
        "llm": {
            "enabled": bool(settings.openrouter_api_key) and settings.llm_enabled,
            "model": settings.llm_model,
        },
    }


def _serialize(row: Action, texts: dict) -> dict:
    return {
        "id": row.id,
        "day": row.day.isoformat(),
        "rule_key": row.rule_key,
        "type": row.type,
        "title": texts.get("headline") or row.title,
        "why": texts.get("why", ""),
        "plan": texts.get("plan", []),
        "effect_note": texts.get("effect_note", ""),
        "effect_weekly": row.effect_weekly,
        "confidence": row.confidence,
        "urgency": row.urgency,
        "score": round(row.score),
        "facts": row.facts,
        "payload": row.payload,
        "texts_source": row.texts_source,
        "status": row.status,
        "rejection_reason": row.rejection_reason,
        "feedback": row.feedback,
    }


def complete_action(db: Session, action: Action) -> Action:
    action.status = "completed"
    action.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action


def reject_action(db: Session, action: Action, reason: str) -> Action:
    action.status = "rejected"
    action.rejection_reason = reason
    db.commit()
    db.refresh(action)
    return action
