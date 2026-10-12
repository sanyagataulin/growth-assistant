"""Точка входа сида: наполняет БД, если она пуста (вызывается при старте контейнера)."""
from app.database import SessionLocal
from app.models import Farmer


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Farmer).count() > 0:
            print("Данные уже есть — сид пропущен")
            return
        from app.seed import seed

        seed(db)
        print("Демо-данные засеяны")
    finally:
        db.close()


if __name__ == "__main__":
    main()
