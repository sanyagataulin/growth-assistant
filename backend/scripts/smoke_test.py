import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # корень backend/

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke.db")
os.environ.setdefault("JWT_SECRET", "smoke")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

# login
r = client.post("/api/auth/login", json={"login": "farmer", "password": "farmer123"})
assert r.status_code == 200, r.text
token = r.json()["token"]
H = {"Authorization": f"Bearer {token}"}
print("LOGIN OK:", r.json()["farmer"]["shop_name"])

# overview + cabinet
r = client.get("/api/cabinet/overview", headers=H)
assert r.status_code == 200, r.text
print("OVERVIEW:", json.dumps(r.json(), ensure_ascii=False))

today_iso = date.today().isoformat()

for offset in (-2, -1, 0, 1, 2, 4):
    day = (date.today() + timedelta(days=offset)).isoformat()
    r = client.get(f"/api/assistant/today?day={day}", headers=H)
    assert r.status_code == 200, r.text
    data = r.json()
    print(f"\n=== TOP-3 на {day} (кандидатов {data['candidates_found']} -> прошло {data['candidates_passed']}) ===")
    for a in data["actions"]:
        print(
            f"  [{a['type']}] {a['title']} | эффект {a['effect_weekly']} ₽/нед | "
            f"уверенность {a['confidence']:.0%} | срочность {a['urgency']} | score {a['score']} | {a['texts_source']}"
        )
    if offset == 0:
        top0 = data["actions"]

# LLM fallback texts check
a0 = top0[0]
print("\nTEXTS[0]:", json.dumps({k: a0[k] for k in ("title", "why", "plan", "effect_note")}, ensure_ascii=False, indent=1))

# confirm flow
r = client.post(f"/api/assistant/{a0['id']}/confirm", headers=H)
assert r.status_code == 200, r.text
res = r.json()
print("CONFIRM OK ->", res["target_screen"]["key"], "/", res["target_screen"]["title"])
assert res["action"]["status"] == "completed"

# reject flow
r = client.post(f"/api/assistant/{top0[1]['id']}/reject", headers=H, json={"reason": "Не могу сейчас"})
assert r.status_code == 200, r.text
assert r.json()["action"]["status"] == "rejected"
print("REJECT OK")

# rejected must disappear from top-3 on same day
r = client.get(f"/api/assistant/today?day={today_iso}", headers=H)
titles = [a["title"] for a in r.json()["actions"]]
assert top0[1]["title"] not in titles, "отклонённое действие вернулось в топ-3!"
print("EXCLUSION OK — отклонённое не вернулось:", titles)

# feedback
r = client.post(f"/api/assistant/{top0[2]['id']}/feedback", headers=H, json={"feedback": "useful"})
assert r.status_code == 200

# journal
r = client.get("/api/assistant/journal", headers=H)
assert r.status_code == 200, r.text
print("\nJOURNAL METRICS:", json.dumps(r.json()["metrics"], ensure_ascii=False))

# rules
r = client.get("/api/assistant/rules", headers=H)
assert r.status_code == 200 and len(r.json()["rules"]) == 7
print("RULES OK: 7 правил")

# cabinet endpoints
for ep in ("products", "cards", "sales", "promotions", "clients"):
    r = client.get(f"/api/cabinet/{ep}", headers=H)
    assert r.status_code == 200, (ep, r.text)
print("CABINET ENDPOINTS OK")

# create + edit product
r = client.post(
    "/api/cabinet/products",
    headers=H,
    json={
        "name": "Смоук-сыр", "category": "Молочные продукты", "unit": "шт",
        "price": 250, "cost": 150, "stock": 15, "expires_at": None,
        "photo_count": 1, "description_len": 80, "views_14d": 400, "cart_14d": 20,
    },
)
assert r.status_code == 201, r.text
created = r.json()
pid = created["id"]
assert created["cover_days"] is None or created["cover_days"] >= 0
print("PRODUCT CREATE OK:", created["name"], "id", pid)

r = client.patch(f"/api/cabinet/products/{pid}", headers=H, json={"photo_count": 5, "description_len": 450, "price": 260})
assert r.status_code == 200, r.text
assert r.json()["photo_count"] == 5 and r.json()["description_len"] == 450 and r.json()["price"] == 260
print("PRODUCT PATCH OK")

r = client.patch(f"/api/cabinet/products/{pid}", headers=H, json={"price": -5})
assert r.status_code == 422, "negative price must be rejected"
r = client.patch("/api/cabinet/products/999999", headers=H, json={"price": 10})
assert r.status_code == 404, "foreign/missing product must 404"
print("PRODUCT VALIDATION OK")

# карточка нового товара дошла до карточек и в ассортимент
r = client.get("/api/cabinet/products", headers=H)
assert any(p["id"] == pid for p in r.json())
r = client.get("/api/cabinet/cards", headers=H)
row = next(c for c in r.json() if c["id"] == pid)
assert row["photo_count"] == 5 and row["description_len"] == 450
print("PRODUCT VISIBLE IN CABINET OK")

# --- замкнутый контур акции: подключение пишет joined=True и снимает сигнал promo_gap ---
r = client.get("/api/cabinet/promotions", headers=H)
promos = r.json()
unjoined = [p for p in promos if p["scope"] == "marketplace" and not p["joined"]]
active = [p for p in unjoined if p["status"] == "Активна"]
target_promo = (active or [p for p in unjoined if p["status"] == "Запланирована"])[0]

r = client.get(f"/api/assistant/today?day={today_iso}", headers=H)
candidates_before = r.json()["candidates_found"]

print("\nPROMO JOIN: цель —", target_promo["title"], f"({target_promo['status']})")
print("кандидатов от правил до подключения:", candidates_before)

r = client.post(f"/api/cabinet/promotions/{target_promo['id']}/join", headers=H)
assert r.status_code == 200, r.text
assert r.json()["joined"] is True
print("JOIN OK:", r.json()["title"])

r = client.get("/api/cabinet/promotions", headers=H)
assert next(p for p in r.json() if p["id"] == target_promo["id"])["joined"] is True
print("PROMOTIONS REFRESH OK — бейдж «вы не участвуете» уйдёт")

r = client.post(f"/api/cabinet/promotions/{target_promo['id']}/join", headers=H)
assert r.status_code == 409, "повторное подключение должно отклоняться"
shop_promo = next(p for p in promos if p["scope"] == "shop")
r = client.post(f"/api/cabinet/promotions/{shop_promo['id']}/join", headers=H)
assert r.status_code == 404, "акцию магазина подключать нельзя"
print("JOIN VALIDATION OK")

if active:
    # правило promo_gap читает joined при каждом расчёте: кандидат должен исчезнуть
    r = client.get(f"/api/assistant/today?day={today_iso}", headers=H)
    data = r.json()
    assert data["candidates_found"] == candidates_before - 1, (
        f"ожидали {candidates_before - 1} кандидатов после подключения, "
        f"получили {data['candidates_found']}"
    )
    for offset in (0, 1, 2):
        day = (date.today() + timedelta(days=offset)).isoformat()
        r = client.get(f"/api/assistant/today?day={day}", headers=H)
        assert not [a for a in r.json()["actions"] if a["type"] == "promo_gap"], \
            f"promo_gap вернулся после подключения на {day}!"
    print("LOOP CLOSED OK — движок потерял ровно 1 кандидата, promo_gap не возвращается")
else:
    print("LOOP CLOSED OK — активных акций не было, сигнал не генерировался")

print("\nSMOKE PASSED")
