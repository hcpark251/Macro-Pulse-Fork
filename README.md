**Language:** **한국어** | [English](docs/README.en.md)

# Macro Pulse Bot

Macro Pulse Bot은 시장 매크로 지표와 지수 히트맵을 종합한 보고서를 텔레그램으로 발송하는 자동화 프로젝트입니다.

- 주요 지표를 수집합니다.
- HTML 리포트를 만듭니다.
- 텔레그램으로 보낼 수 있습니다.
- GitHub Actions로 정해진 시간에 자동 실행할 수 있습니다.

## 주요 기능

- 한국장(`KR`) 또는 미국장(`US`) 기준으로 리포트를 만듭니다.
- 주가지수, 환율, 금리, 원자재, 비트코인, 시장 심리(Fear & Greed Index, Put/Call Ratio) 같은 지표를 모읍니다.
- 텔레그램용 짧은 요약과 HTML 리포트를 함께 만듭니다.
- 시장 분위기를 보기 위한 스크린샷도 붙일 수 있습니다.
  - `KR`: KOSPI / KOSDAQ 히트맵
  - `US`: Finviz 맵

## 동작 방식

1. Yahoo Finance, CNBC quote page, CNN Fear & Greed API, CBOE에서 데이터를 가져옵니다.
2. 가져온 데이터를 정리합니다.
3. HTML 리포트와 텔레그램 요약 문구를 만듭니다.
4. 필요하면 텔레그램으로 전송합니다.

실제 실행 파일은 [`src/main.py`](src/main.py)입니다.

## 수집 항목

- 국내 지수: `KOSPI`, `KOSDAQ`
- 해외 지수: `S&P 500`, `Nasdaq`, `Russell 2000`, `Nikkei 225`, `Hang Seng`, `Euro Stoxx 50`, `FTSE 100` 등
- 채권: `US 2Y Treasury`, `US 10Y Treasury`, `US 10Y-2Y Spread`, `Korea 10Y Treasury`, `Japan 10Y Treasury`
- 원자재: `WTI Crude`, `Brent Crude`, `Natural Gas`, `Gold`, `Silver`, `Copper`, `Wheat`
- 환율: `USD/KRW`, `JPY/KRW`, `EUR/KRW`, `CNY/KRW`, `DXY (Dollar Index)`
- ETF: `TLT`, `GLD`, `HYG`, `SOXX`, `ARKK`, `ITA`, `XAR`
- 섹터 지수: `SOX` (필라델피아 반도체)
- 가상자산: `Bitcoin`, `Ethereum`, `Ripple`
- 변동성: `VIX`, `VKOSPI`
- 시장 심리: `Fear & Greed Index` (CNN), `Put/Call Ratio` (CBOE)

## GitHub Actions

이 저장소는 GitHub Actions를 사용합니다.

- 정해진 시간에 자동으로 리포트를 만듭니다.
- 최신 리포트를 GitHub Pages에 올릴 수 있습니다.
- 실행 로그와 결과 파일을 artifact로 저장합니다.
- 실패하면 Telegram으로 알림을 보내도록 설정할 수 있습니다.

TELEGRAM Token등 KEY 설정은 [`docs/SECRETS.md`](docs/SECRETS.md)에서 볼 수 있습니다.

## 포맷 설정

텔레그램 요약 순서, 스크린샷 종류, KR/US 스케줄은 [`config/report_formats.json`](config/report_formats.json)에서 바꿀 수 있습니다.

- 어떤 섹션을 먼저 보여줄지
- 어떤 항목을 포함할지
- 어떤 스크린샷을 붙일지
- KR/US 리포트가 실행될 cron 시간

코드를 몰라도 JSON만 조금 수정하면 순서를 바꿀 수 있습니다.

## Fork 설정

Fork해서 바로 쓰려면 아래만 먼저 설정하면 됩니다.

1. Fork한 저장소의 `Actions` 탭에서 워크플로를 활성화합니다.
2. `Settings > Secrets and variables > Actions`에서 Telegram Secret을 등록합니다.
3. 웹 리포트도 보고 싶다면 `Settings > Pages`에서 source를 `GitHub Actions`로 설정합니다.
4. 필요하면 [`config/report_formats.json`](config/report_formats.json)에서 KR/US 포맷과 스케줄을 바꿉니다.

## 로컬 / Docker 실행

자세한 실행 방법은 [`docs/LOCAL_RUN.md`](docs/LOCAL_RUN.md)에서 볼 수 있습니다.

> 빠른 미리보기
>
> - 설치: `uv sync --all-groups`
> - Python dry-run: `uv run python src/main.py --dry-run`
> - Docker build: `docker build -t macro-pulse .`
> - Docker dry-run: `docker run --rm --env-file .env -v "$PWD:/app" -w /app macro-pulse uv run --frozen python src/main.py --dry-run`

## 테스트

기본 테스트:

```bash
uv run python -m unittest discover tests
```

실제 외부 서비스까지 확인하는 스모크 테스트:

```bash
RUN_LIVE_SMOKE_TESTS=1 uv run python -m unittest discover tests
```

스크린샷 스모크 테스트:

```bash
RUN_SCREENSHOT_SMOKE_TESTS=1 uv run python -m unittest tests.test_screenshot
```

## 스크린샷 예시

### 미장 마감 예시

![미장 마감 보고서 예시](assets/us.png)

### 국장 마감 예시

![국장 마감 보고서 예시](assets/kr.png)

## 자주 보는 파일

- [`src/main.py`](src/main.py): 전체 실행 시작점
- [`src/macro_pulse/data/market_data.py`](src/macro_pulse/data/market_data.py): 데이터 수집 orchestration
- [`src/macro_pulse/data/providers/sentiment.py`](src/macro_pulse/data/providers/sentiment.py): 시장 심리 지표 수집 (Fear & Greed, Put/Call Ratio)
- [`src/macro_pulse/reporting/generator.py`](src/macro_pulse/reporting/generator.py): 리포트 생성
- [`src/macro_pulse/delivery/notifier.py`](src/macro_pulse/delivery/notifier.py): 텔레그램 전송
- [`config/report_formats.json`](config/report_formats.json): 요약 포맷 설정

## 문제 해결

- 스크린샷이 실패하면 Chrome/Chromium 실행 환경을 먼저 확인하세요.
- 텔레그램 메시지가 안 오면 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 확인하세요.
- 일부 데이터가 비어 있으면 외부 사이트 응답 문제일 수 있습니다.
- GitHub Pages가 안 보이면 `Settings > Pages`에서 source가 `GitHub Actions`로 설정되어 있는지 확인하세요.
