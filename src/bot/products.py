"""Product specification registry (config/products.yaml)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProductSpec:
    product_code: str
    market_type: str          # Spot / FX
    min_size: float
    taker_fee_pct: float
    shortable: bool
    leverage: float
    swap_daily_pct: float

    @property
    def is_margin(self) -> bool:
        return self.market_type != "Spot"


def load_products(root: str | Path = ".") -> dict[str, ProductSpec]:
    path = Path(root) / "config" / "products.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        code: ProductSpec(
            product_code=code,
            market_type=str(spec["market_type"]),
            min_size=float(spec["min_size"]),
            taker_fee_pct=float(spec["taker_fee_pct"]),
            shortable=bool(spec["shortable"]),
            leverage=float(spec["leverage"]),
            swap_daily_pct=float(spec["swap_daily_pct"]),
        )
        for code, spec in raw.items()
    }
