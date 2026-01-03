from collections import defaultdict
from datetime import datetime

# In-memory buffer
TICK_BUFFER = defaultdict(list)

def add_tick(tick: dict):
    """
    tick = {
        instrument_token,
        last_price,
        volume_traded_today,
        timestamp
    }
    """
    token = tick["instrument_token"]
    TICK_BUFFER[token].append(tick)


def flush_ticks():
    data = dict(TICK_BUFFER)
    TICK_BUFFER.clear()
    return data
