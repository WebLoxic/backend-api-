from zoneinfo import ZoneInfo
from datetime import datetime

IST = ZoneInfo("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)

def is_market_open():
    now = ist_now()
    mins = now.hour * 60 + now.minute
    return 555 <= mins <= 930   # 09:15–15:30
