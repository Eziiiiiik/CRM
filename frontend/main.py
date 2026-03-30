from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import logging
from typing import Dict, Any

router = APIRouter(prefix="", tags=["frontend"])

users_db: Dict[int, Dict[str, Any]] = {}
next_id = 1

logger = logging.getLogger(__name__)


# Читаем HTML файлы напрямую
def read_html(filename: str) -> str:
    path = Path(__file__).parent / "templates" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    registered = request.query_params.get("registered")
    username = request.query_params.get("username", "")

    html = read_html("index.html")

    if registered == "true":
        success = f'<div style="color: green; padding: 10px;">✅ Регистрация успешна, {username}!</div>'
        html = html.replace("<!-- REGISTER_SUCCESS -->", success)

    return HTMLResponse(content=html)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return HTMLResponse(content=read_html("register.html"))


@router.post("/register")
async def register_user(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...)
):
    global next_id

    for user in users_db.values():
        if user["email"] == email:
            html = read_html("register.html")
            error = '<div style="color: red;">❌ Пользователь с таким email уже существует</div>'
            html = html.replace("<!-- ERROR -->", error)
            return HTMLResponse(content=html, status_code=400)

    user_id = next_id
    next_id += 1

    users_db[user_id] = {
        "id": user_id,
        "username": username,
        "email": email,
        "password": password
    }

    logger.info(f"✅ Новый пользователь: {username} ({email})")

    return RedirectResponse(
        url=f"/?registered=true&username={username}",
        status_code=303
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    html = read_html("profile.html")
    return HTMLResponse(content=html)


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return HTMLResponse(content=read_html("chat.html"))


@router.get("/api/users")
async def get_users():
    return {
        "total": len(users_db),
        "users": [
            {"id": uid, "username": user["username"], "email": user["email"]}
            for uid, user in users_db.items()
        ]
    }