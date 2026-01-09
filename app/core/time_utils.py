from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def ist_now():
    return datetime.now(IST)

def to_ist(dt: datetime):
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(IST)
