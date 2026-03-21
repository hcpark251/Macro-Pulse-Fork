**Language:** **한국어** | [English](SECRETS.en.md)

# GitHub Secrets

GitHub Actions에서 Macro Pulse Bot을 정상적으로 실행하려면 저장소에 아래 Secret 값을 등록해야 합니다.

경로:
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

## 필수 항목

### Telegram

- `TELEGRAM_BOT_TOKEN`: BotFather로 만든 텔레그램 봇의 토큰
- `TELEGRAM_CHAT_ID`: 리포트를 받을 채팅방 또는 채널의 ID

## 선택 항목

### Email

이메일로도 리포트를 받고 싶을 때만 필요합니다.

- `SMTP_USERNAME`: 발신 이메일 주소
- `SMTP_PASSWORD`: 이메일 앱 비밀번호
- `RECIPIENT_EMAIL`: 리포트를 받을 이메일 주소

## 주의 사항

- Secret 이름은 위와 정확히 같아야 합니다.
- `SMTP_PASSWORD`에는 일반 로그인 비밀번호가 아니라 앱 비밀번호를 넣는 것이 안전합니다.
- 이메일을 쓰지 않으면 SMTP 관련 값은 비워도 됩니다.
