from fastapi import APIRouter, Depends, HTTPException
import httpx
from app.core.config import get_settings

router = APIRouter(prefix="/telephony", tags=["telephony"])
settings = get_settings()

TELEPHONY_URL = "http://localhost:8003"  # или имя сервиса в Docker

@router.post("/numbers/purchase")
async def purchase_number(country: str, city: str = None, client_id: int = None):
    """Купить телефонный номер"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TELEPHONY_URL}/api/numbers/purchase",
            json={"country": country, "city": city, "client_id": client_id}
        )
        return response.json()

@router.get("/numbers")
async def get_numbers():
    """Получить все номера"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{TELEPHONY_URL}/api/numbers")
        return response.json()

@router.post("/calls/make")
async def make_call(from_number_id: str, to_number: str, client_id: int):
    """Совершить звонок"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TELEPHONY_URL}/api/calls/make",
            json={
                "from_number_id": from_number_id,
                "to_number": to_number,
                "client_id": client_id
            }
        )
        return response.json()