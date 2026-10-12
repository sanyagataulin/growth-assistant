from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assistant, auth, cabinet

app = FastAPI(title="Помощник роста — ИИ-советник фермера", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cabinet.router)
app.include_router(assistant.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
