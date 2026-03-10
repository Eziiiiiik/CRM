from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from typing import Dict, Any

router = APIRouter(prefix="", tags=["frontend"])

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

users_db: Dict[int, Dict[str, Any]] = {}
next_id = 1

logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )

#страница чата
@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse(
        "support-chat.html",
        {"request": request}
    )

@router.post("/register")
async def register_user(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...)
):
    global next_id

    try:
        for user in users_db.values():
            if user["email"] == email:
                return templates.TemplateResponse(
                    "register.html",
                    {
                        "request": request,
                        "error": "Пользователь с таким email уже существует",
                        "username": username,
                        "email": email
                    }
                )

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
            url="/?registered=true",
            status_code=303
        )

    except Exception as e:
        logger.error(f"❌ Ошибка регистрации: {e}")
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Произошла ошибка при регистрации"
            }
        )


@router.get("/api/users")
async def get_users():
    return {
        "total": len(users_db),
        "users": [
            {"id": uid, "username": user["username"], "email": user["email"]}
            for uid, user in users_db.items()
        ]
    }
