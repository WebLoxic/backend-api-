# import random
# import time

# class ZerodhaService:
#     """
#     Later: real kiteconnect logic
#     Abhi: live-like mock
#     """

#     def get_positions(self, user_id):
#         # Empty = "You have no active positions"
#         return []

#     def get_orders(self, user_id):
#         return []

#     def place_order(self, data):
#         return {
#             "order_id": f"ORD-{int(time.time())}",
#             "status": "SUCCESS"
#         }

#     def get_ltp(self, symbol):
#         return round(random.uniform(100, 2500), 2)



from datetime import datetime
from app.kite_client import kite_client


class ZerodhaService:
    """
    Zerodha REST helper (snapshot / non-live)
    NOTE:
    - Ye live tick nahi hai
    - Ye sirf "current market truth" deta hai
    """

    # ===============================
    # ACCOUNT HELPERS
    # ===============================
    def get_positions(self, user_id):
        kite = kite_client.get_user_kite(user_id=user_id)
        return kite.positions()

    def get_orders(self, user_id):
        kite = kite_client.get_user_kite(user_id=user_id)
        return kite.orders()

    def place_order(self, user_id, data):
        kite = kite_client.get_user_kite(user_id=user_id)
        return kite.place_order(**data)

    # ===============================
    # 🔥 IMPORTANT PART (SNAPSHOT)
    # ===============================
    def get_market_snapshot(self, user_id: int, instrument_token: int):
        """
        Returns LAST TRADED PRICE snapshot
        (NOT a live WebSocket tick)

        Used for:
        - syncing historical candles
        - building current running candle
        """

        kite = kite_client.get_user_kite(user_id=user_id)

        try:
            # Zerodha quote expects instrument_token
            quote = kite.quote([instrument_token])
            q = list(quote.values())[0]

            last_trade_time = (
                q.get("last_trade_time")
                or q.get("exchange_timestamp")
            )

            return {
                "ltp": q.get("last_price"),
                "last_trade_time": int(last_trade_time.timestamp())
                if last_trade_time
                else None,
                "ohlc": q.get("ohlc"),
                "volume": q.get("volume"),
            }

        except Exception as e:
            # Snapshot failure should NOT crash chart
            return None
