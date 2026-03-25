"""
Sentiment indicators provider.

- Fear & Greed Index : CNN Markets API (JSON endpoint)
- Put/Call Ratio     : CBOE 공개 데이터 CSV
"""
from __future__ import annotations

import csv
import io
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ...core.logging import get_logger
from ...domain.models import AssetSnapshot

logger = get_logger(__name__)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

# CNN Fear & Greed JSON API
_FEAR_GREED_URL = (
    "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
)

# CBOE 당일 Put/Call Ratio CSV (장중/마감 후 갱신)
_CBOE_PC_URL = "https://www.cboe.com/data/VolumePutCallRatios.csv"


# ──────────────────────────────────────────────
# Fear & Greed Index
# ──────────────────────────────────────────────

_FEAR_GREED_LABELS = {
    (0, 25):  "Extreme Fear",
    (25, 45): "Fear",
    (45, 55): "Neutral",
    (55, 75): "Greed",
    (75, 100): "Extreme Greed",
}


def _fear_greed_label(score: float) -> str:
    for (lo, hi), label in _FEAR_GREED_LABELS.items():
        if lo <= score <= hi:
            return label
    return "Unknown"


def fetch_fear_and_greed(attempts: int = 3, retry_delay: float = 1.0) -> AssetSnapshot | None:
    """
    CNN Fear & Greed Index를 가져옵니다.
    score 0~100, 전일 대비 변화 포함.
    반환값: AssetSnapshot (name="Fear & Greed Index", price=score)
    실패 시 None 반환.
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = Request(_FEAR_GREED_URL, headers={**REQUEST_HEADERS, "Accept": "application/json"})
            with urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            fng = raw.get("fear_and_greed", {})
            score = float(fng["score"])
            prev_score = float(fng.get("previous_close", score))
            change = score - prev_score
            change_pct = (change / prev_score * 100) if prev_score else 0.0

            # 히스토리: fear_and_greed_historical 배열 (최근 7일)
            history_raw = raw.get("fear_and_greed_historical", {}).get("data", [])
            history = [float(d["y"]) for d in history_raw[-7:]] if history_raw else [score]

            label = _fear_greed_label(score)
            logger.info("Fear & Greed: %.1f (%s)", score, label)

            return AssetSnapshot(
                name=f"Fear & Greed ({label})",
                price=score,
                change=change,
                change_pct=change_pct,
                history=history,
            )

        except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning("Fear & Greed fetch attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(retry_delay)
        except Exception:
            logger.exception("Unexpected error fetching Fear & Greed")
            return None

    logger.error("Fear & Greed fetch failed after %s attempts: %s", attempts, last_error)
    return None


# ──────────────────────────────────────────────
# Put/Call Ratio  (CBOE)
# ──────────────────────────────────────────────

def fetch_put_call_ratio(attempts: int = 3, retry_delay: float = 1.0) -> AssetSnapshot | None:
    """
    CBOE 총 Put/Call Ratio (Total P/C Ratio) 를 가져옵니다.
    CBOE CSV: DATE, P/C TOTAL, P/C INDEX, P/C EQUITY 순서.
    1.0 초과 → 풋 우세(공포), 1.0 미만 → 콜 우세(낙관).
    반환값: AssetSnapshot (name="Put/Call Ratio", price=total_ratio)
    실패 시 None 반환.
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = Request(_CBOE_PC_URL, headers=REQUEST_HEADERS)
            with urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", "ignore")

            rows = list(csv.DictReader(io.StringIO(content)))
            if not rows:
                raise ValueError("CBOE CSV returned empty data")

            # 헤더 키 정규화 (공백·대소문자 차이 대응)
            def _get(row: dict, *candidates: str) -> str:
                for key in row:
                    normalized = key.strip().upper()
                    for c in candidates:
                        if c.upper() in normalized:
                            return row[key].strip()
                raise KeyError(f"Column not found: {candidates}")

            # 최신 2행으로 당일/전일 계산
            latest = rows[-1]
            prev_row = rows[-2] if len(rows) >= 2 else latest

            ratio = float(_get(latest, "TOTAL", "P/C TOTAL", "TOTAL PUT/CALL"))
            prev_ratio = float(_get(prev_row, "TOTAL", "P/C TOTAL", "TOTAL PUT/CALL"))

            change = ratio - prev_ratio
            change_pct = (change / prev_ratio * 100) if prev_ratio else 0.0

            # 히스토리: 최근 7거래일
            history: list[float] = []
            for row in rows[-7:]:
                try:
                    history.append(float(_get(row, "TOTAL", "P/C TOTAL", "TOTAL PUT/CALL")))
                except (KeyError, ValueError):
                    pass

            logger.info("Put/Call Ratio: %.2f (prev: %.2f)", ratio, prev_ratio)

            return AssetSnapshot(
                name="Put/Call Ratio",
                price=ratio,
                change=change,
                change_pct=change_pct,
                history=history or [ratio],
            )

        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("Put/Call Ratio fetch attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(retry_delay)
        except Exception:
            logger.exception("Unexpected error fetching Put/Call Ratio")
            return None

    logger.error("Put/Call Ratio fetch failed after %s attempts: %s", attempts, last_error)
    return None
