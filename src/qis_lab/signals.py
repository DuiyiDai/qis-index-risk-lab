"""Close-t information only. Instructions carry explicit execution dates."""

import numpy as np
from .config import ASSETS, Config
from .data import month_ends


def decisions(prices, config=Config()):
    ends = month_ends(prices.index)
    values = prices.to_numpy()
    returns = values[1:] / values[:-1] - 1
    indicators = None
    out = {}
    for j, date in enumerate(prices.index):
        if date in ends and j >= config.lookback:
            indicators = (values[j] / values[j - config.lookback] - 1 > 0).astype(float)
        if indicators is None or j < config.vol_window:
            continue
        if config.strategy in {"equal", "trend"} and date not in ends:
            continue
        b = indicators / 3
        if config.strategy == "equal":
            b = np.ones(3) / 3
        elif config.strategy == "cash":
            b = np.zeros(3)
        cov = np.cov(returns[j - config.vol_window : j], rowvar=False, ddof=1)
        sigma = float(np.sqrt(max(0, 252 * b @ cov @ b)))
        scale = (
            min(1.0, config.vol_reference / max(sigma, config.vol_floor))
            if config.strategy == "overlay"
            else 1.0
        )
        out[str(date.date())] = {
            "decision_date": str(date.date()),
            "execution_date": str(prices.index[j + 1].date()) if j + 1 < len(prices) else None,
            "signals": indicators.tolist(),
            "sigma_base": sigma,
            "scale": scale,
            "forecast_target_vol": sigma * scale,
            "target": dict(zip(ASSETS, (scale * b).tolist())),
        }
    return out
