from dataclasses import dataclass
import math

ASSETS = ("equity", "treasury", "gold")
METHODOLOGY = "QIS-1.0"


@dataclass(frozen=True)
class Config:
    lookback: int = 252
    vol_window: int = 63
    vol_reference: float = 0.10
    vol_floor: float = 0.01
    cost_bps: float = 5.0
    strategy: str = "overlay"

    def __post_init__(self):
        if self.lookback < 1 or self.vol_window < 2:
            raise ValueError("lookback >= 1 and covariance window >= 2 required")
        if self.strategy not in {"overlay", "trend", "equal", "cash"}:
            raise ValueError("unknown strategy")
        if not all(math.isfinite(x) for x in (self.vol_reference, self.vol_floor, self.cost_bps)):
            raise ValueError("finite configuration required")
        if self.vol_reference <= 0 or self.vol_floor <= 0 or not 0 <= self.cost_bps < 10000:
            raise ValueError("invalid risk reference, floor or cost")
