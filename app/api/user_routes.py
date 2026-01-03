from fastapi import APIRouter, Depends
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["User"])

@router.get("")
def profile(user=Depends(get_current_user)):
    return user
