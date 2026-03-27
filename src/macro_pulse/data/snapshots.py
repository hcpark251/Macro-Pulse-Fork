from __future__ import annotations

from collections.abc import Sequence

from ..domain.models import AssetSnapshot, ValueFormat


def build_snapshot(
    name: str,
    price: float | int | None = None,
    change: float | int | None = None,
    change_pct: float | int | None = None,
    history: Sequence[float | int] | None = None,
    *,
    ticker: str | None = None,
    dates: Sequence[str] | None = None,
    value_format: ValueFormat = ValueFormat.STANDARD_2,
    ma_signal: str = "",
) -> AssetSnapshot:
    normalized_history = [float(value) for value in history] if history else []
    if not normalized_history and price is not None:
        normalized_history = [float(price)]

    return AssetSnapshot(
        name=name,
        ticker=ticker,
        price=float(price) if price is not None else None,
        change=float(change) if change is not None else None,
        change_pct=float(change_pct) if change_pct is not None else None,
        history=normalized_history,
        dates=[str(value) for value in (dates or [])],
        value_format=value_format,
        ma_signal=ma_signal,
    )
