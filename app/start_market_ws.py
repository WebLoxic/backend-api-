# from sqlalchemy import text
# from app.db import SessionLocal
# from app.market_ws import MarketWebSocket


# def get_latest_access_token():
#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("""
#                 SELECT access_token
#                 FROM zerodha_broker_token
#                 ORDER BY login_time DESC
#                 LIMIT 1
#             """)
#         ).fetchone()

#         if not row:
#             raise RuntimeError("No Zerodha access token found")

#         return row.access_token
#     finally:
#         db.close()


# if __name__ == "__main__":
#     access_token = get_latest_access_token()
#     ws = MarketWebSocket(access_token)
#     ws.start()


import logging

from app.kite_client import kite_client
from app.market_ws import MarketWebSocket

logging.basicConfig(level=logging.INFO)

def main():
    kite = kite_client.get_user_kite(user_id=1)

    ws = MarketWebSocket(kite.access_token)
    ws.start()


if __name__ == "__main__":
    main()
