from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farmer
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_farmer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Farmer:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
    farmer_id = decode_token(credentials.credentials)
    if farmer_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Сессия истекла")
    farmer = db.get(Farmer, farmer_id)
    if farmer is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Фермер не найден")
    return farmer
