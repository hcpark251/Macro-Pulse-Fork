import os
import tempfile

import yfinance as yf

from ..core.logging import get_logger
from ..domain.models import (
    ReportDataset,
    TickerDefinition,
    ValueFormat,
    coerce_cnbc_quote,
)
from .exchange_rates import build_exchange_snapshots
from .providers.cnbc import CNBC_FX_SYMBOLS, CNBC_MARKET_SYMBOLS, fetch_cnbc_data
from .providers.sentiment import fetch_fear_and_greed, fetch_put_call_ratio
from .snapshots import build_snapshot


logger = get_logger(__name__)


YF_TICKERS = {
    "indices_domestic": (
        TickerDefinition("KOSPI", "^KS11"),
        TickerDefinition("KOSDAQ", "^KQ11"),
    ),
    "indices_overseas": (
        TickerDefinition("S&P 500", "^GSPC"),
        TickerDefinition("Nasdaq", "^IXIC"),
        TickerDefinition("Russell 2000", "^RUT"),
        TickerDefinition("Euro Stoxx 50", "^STOXX50E"),
        TickerDefinition("FTSE 100", "^FTSE"),
        TickerDefinition("Nikkei 225", "^N225"),
        TickerDefinition("Hang Seng", "^HSI"),
        TickerDefinition("Shanghai Composite", "000001.SS"),
    ),
    "commodities_rates": (
        TickerDefinition("Gold", "GC=F"),
        TickerDefinition("Silver", "SI=F"),
        TickerDefinition("Copper", "HG=F"),
        TickerDefinition("WTI Crude", "CL=F"),
        TickerDefinition("Brent Crude", "BZ=F"),
        TickerDefinition("Natural Gas", "NG=F"),
        TickerDefinition("Wheat", "ZW=F"),
        TickerDefinition("US 2Y Treasury", "^IRX", value_format=ValueFormat.YIELD_3),
        TickerDefinition("US 10Y Treasury", "^TNX", value_format=ValueFormat.YIELD_3),
    ),
    "etf": (
        TickerDefinition("TLT", "TLT"),
        TickerDefinition("GLD", "GLD"),
        TickerDefinition("HYG", "HYG"),
        TickerDefinition("SOXX", "SOXX"),
        TickerDefinition("ARKK", "ARKK"),
    ),
    "crypto": (
        TickerDefinition("Bitcoin", "BTC-USD"),
        TickerDefinition("Ethereum", "ETH-USD"),
    ),
    "volatility": (TickerDefinition("VIX", "^VIX"),),
}

YF_RATES_HISTORY = {
    "USD/KRW": "KRW=X",
    "JPY/KRW": "JPYKRW=X",
    "EUR/KRW": "EURKRW=X",
}

YF_DXY_TICKER = TickerDefinition("DXY (Dollar Index)", "DX-Y.NYB")


def fetch_all_data() -> ReportDataset:
    _configure_runtime_cache()
    results = _empty_report_dataset()

    yf_rates_data = _fetch_rate_histories()

    logger.info("Fetching CNBC data...")
    cnbc_data = fetch_cnbc_data([*CNBC_MARKET_SYMBOLS, *CNBC_FX_SYMBOLS])
    results["exchange"].extend(build_exchange_snapshots(cnbc_data, yf_rates_data))
    _append_cnbc_market_snapshots(results, cnbc_data)

    logger.info("Fetching Yahoo Finance data...")
    _append_yahoo_snapshots(results)
    _append_dxy_snapshot(results)
    _reorder_bond_snapshots(results["commodities_rates"])
    _append_yield_spread(results["commodities_rates"])

    logger.info("Fetching sentiment indicators...")
    _append_sentiment_snapshots(results)

    logger.info(
        "Completed fetch cycle with %s populated categories",
        sum(1 for items in results.values() if items),
    )

    return results


def _empty_report_dataset() -> ReportDataset:
    return {
        "indices_domestic": [],
        "indices_overseas": [],
        "volatility": [],
        "commodities_rates": [],
        "exchange": [],
        "crypto": [],
        "etf": [],
        "sentiment": [],
    }


def _fetch_rate_histories():
    histories = {}
    logger.info("Fetching YF rates history...")
    for name, ticker in YF_RATES_HISTORY.items():
        try:
            history = yf.Ticker(ticker).history(period="1mo")
            if not history.empty:
                histories[name] = history
        except Exception as exc:
            logger.error("Error fetching YF history for %s: %s", name, exc)
    return histories


def _append_cnbc_market_snapshots(results: ReportDataset, cnbc_data) -> None:
    for symbol, category, value_format in (
        (".KSVKOSPI", "volatility", ValueFormat.STANDARD_2),
        ("JP10Y", "commodities_rates", ValueFormat.YIELD_3),
        ("KR10Y", "commodities_rates", ValueFormat.YIELD_3),
    ):
        quote = cnbc_data.get(symbol)
        if quote is None:
            continue

        item = coerce_cnbc_quote(quote)
        results[category].append(
            build_snapshot(
                item.name,
                item.price,
                item.change,
                item.change_pct,
                value_format=value_format,
            )
        )


def _append_yahoo_snapshots(results: ReportDataset) -> None:
    for category, definitions in YF_TICKERS.items():
        for definition in definitions:
            try:
                data = yf.Ticker(definition.symbol).history(period="1mo")
                if data.empty:
                    logger.warning(
                        "Yahoo Finance returned no history for %s (%s)",
                        definition.name,
                        definition.symbol,
                    )
                    continue

                last_price = float(data["Close"].iloc[-1])
                if len(data) > 1:
                    previous_price = float(data["Close"].iloc[-2])
                    change = last_price - previous_price
                    change_pct = (change / previous_price) * 100
                else:
                    change = 0.0
                    change_pct = 0.0

                results[category].append(
                    build_snapshot(
                        definition.name,
                        last_price,
                        change,
                        change_pct,
                        history=data["Close"].tail(7).tolist(),
                        ticker=definition.symbol,
                        dates=[date.strftime("%m-%d") for date in data.tail(7).index],
                        value_format=definition.value_format,
                    )
                )
            except Exception as exc:
                logger.error("Error fetching YF %s: %s", definition.name, exc)


def _append_dxy_snapshot(results: ReportDataset) -> None:
    """DXY 달러인덱스를 exchange 섹션에 추가"""
    try:
        definition = YF_DXY_TICKER
        data = yf.Ticker(definition.symbol).history(period="1mo")
        if data.empty:
            logger.warning("Yahoo Finance returned no history for DXY")
            return

        last_price = float(data["Close"].iloc[-1])
        if len(data) > 1:
            previous_price = float(data["Close"].iloc[-2])
            change = last_price - previous_price
            change_pct = (change / previous_price) * 100
        else:
            change = 0.0
            change_pct = 0.0

        results["exchange"].append(
            build_snapshot(
                definition.name,
                last_price,
                change,
                change_pct,
                history=data["Close"].tail(7).tolist(),
                ticker=definition.symbol,
                dates=[date.strftime("%m-%d") for date in data.tail(7).index],
            )
        )
    except Exception as exc:
        logger.error("Error fetching DXY: %s", exc)


def _append_yield_spread(commodities_rates: list) -> None:
    """US 10Y - 2Y 장단기 스프레드 계산 후 추가"""
    us_2y = next((item for item in commodities_rates if item.name == "US 2Y Treasury"), None)
    us_10y = next((item for item in commodities_rates if item.name == "US 10Y Treasury"), None)

    if us_2y is None or us_10y is None or us_2y.price is None or us_10y.price is None:
        logger.warning("Cannot compute yield spread: missing 2Y or 10Y data")
        return

    spread = us_10y.price - us_2y.price
    prev_2y = (us_2y.price - us_2y.change) if us_2y.change is not None else us_2y.price
    prev_10y = (us_10y.price - us_10y.change) if us_10y.change is not None else us_10y.price
    prev_spread = prev_10y - prev_2y
    spread_change = spread - prev_spread
    spread_change_pct = (spread_change / abs(prev_spread) * 100) if prev_spread != 0 else 0.0

    commodities_rates.append(
        build_snapshot(
            "US 10Y-2Y Spread",
            spread,
            spread_change,
            spread_change_pct,
            value_format=ValueFormat.YIELD_3,
        )
    )
    logger.info("Yield spread (10Y-2Y): %.3f", spread)


def _append_sentiment_snapshots(results: ReportDataset) -> None:
    """Fear & Greed Index 및 Put/Call Ratio를 sentiment 카테고리에 추가"""
    fng = fetch_fear_and_greed()
    if fng is not None:
        results["sentiment"].append(fng)

    pcr = fetch_put_call_ratio()
    if pcr is not None:
        results["sentiment"].append(pcr)


def _reorder_bond_snapshots(commodities_rates) -> None:
    us_10y_index = next(
        (
            index
            for index, item in enumerate(commodities_rates)
            if item.name == "US 10Y Treasury"
        ),
        None,
    )
    korea_10y_index = next(
        (
            index
            for index, item in enumerate(commodities_rates)
            if item.name == "Korea 10Y Treasury"
        ),
        None,
    )

    if us_10y_index is None or korea_10y_index is None:
        return

    us_10y_snapshot = commodities_rates.pop(us_10y_index)
    korea_10y_index = next(
        (
            index
            for index, item in enumerate(commodities_rates)
            if item.name == "Korea 10Y Treasury"
        ),
        None,
    )
    if korea_10y_index is None:
        commodities_rates.append(us_10y_snapshot)
        return

    commodities_rates.insert(korea_10y_index + 1, us_10y_snapshot)


def _configure_runtime_cache() -> None:
    cache_dir = os.environ.get(
        "YFINANCE_CACHE_DIR",
        os.path.join(tempfile.gettempdir(), "macro-pulse-yfinance"),
    )
    os.makedirs(cache_dir, exist_ok=True)
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(cache_dir)
