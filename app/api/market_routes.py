from fastapi import APIRouter

router = APIRouter()

@router.post("/market/subscribe/{token}")
def subscribe(token: int):
    # frontend WS itself handles subscribe
    return {"status": "queued", "token": token}

@router.post("/market/unsubscribe/{token}")
def unsubscribe(token: int):
    return {"status": "noop", "token": token}
