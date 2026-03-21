**Language:** [한국어](SECRETS.md) | **English**

# GitHub Secrets

To run Macro Pulse Bot correctly through GitHub Actions, add the following repository secrets.

Path:
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

## Required

### Telegram

- `TELEGRAM_BOT_TOKEN`: the token from BotFather for your Telegram bot
- `TELEGRAM_CHAT_ID`: the chat or channel ID that should receive the report

## Optional

### Email

These are only needed if you also want to receive the report by email.

- `SMTP_USERNAME`: sender email address
- `SMTP_PASSWORD`: email app password
- `RECIPIENT_EMAIL`: destination email address

## Notes

- Secret names must match exactly.
- For `SMTP_PASSWORD`, use an app password rather than your normal login password.
- If you do not use email delivery, you can leave the SMTP-related secrets unset.
