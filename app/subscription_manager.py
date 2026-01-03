# app/subscription_manager.py
class SubscriptionManager:
    def __init__(self, market_ws):
        self.market_ws = market_ws
        self.active_tokens = set()

    def subscribe(self, instrument_token: int):
        if instrument_token not in self.active_tokens:
            self.active_tokens.add(instrument_token)
            self.market_ws.subscribe([instrument_token])
            self.market_ws.set_mode("full", [instrument_token])

    def unsubscribe(self, instrument_token: int):
        if instrument_token in self.active_tokens:
            self.active_tokens.remove(instrument_token)
            self.market_ws.unsubscribe([instrument_token])
