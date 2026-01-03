from decimal import Decimal

def calculate_quantity(
    capital: Decimal,
    risk_percent: Decimal,
    entry_price: Decimal,
    stoploss_price: Decimal | None = None
):
    """
    Institutional logic:
    - Risk based position sizing
    """

    if stoploss_price:
        risk_amount = capital * (risk_percent / Decimal("100"))
        risk_per_unit = abs(entry_price - stoploss_price)

        if risk_per_unit <= 0:
            return 0

        qty = risk_amount / risk_per_unit
    else:
        # fallback: full capital based
        qty = capital / entry_price

    return int(qty)
