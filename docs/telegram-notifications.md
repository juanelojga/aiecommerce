# Telegram Notifications Setup

This guide explains how to configure Telegram notifications for the batch publishing command in the AI Ecommerce Django project.

## Overview

The `publish_ml_product_batch` management command automatically sends Telegram notifications after each execution, providing real-time feedback on:
- Number of products successfully published
- Number of errors encountered
- Number of products skipped
- MercadoLibre IDs of published products
- Execution mode (Production/Sandbox)
- Dry run indicator

## Prerequisites

- A Telegram account
- Access to create Telegram bots

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat with BotFather and send the command: `/newbot`
3. Follow the prompts to:
   - Choose a name for your bot (e.g., "AI Ecommerce Notifications")
   - Choose a username for your bot (must end in 'bot', e.g., "aiecommerce_notify_bot")
4. BotFather will provide you with a **bot token**. It looks like this:
   ```
   123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```
5. **Save this token securely** - you'll need it for configuration.

## Step 2: Get Your Chat ID

To receive notifications, you need to find your Telegram chat ID:

### Method 1: Using a Web Browser

1. Send any message to your newly created bot (e.g., "Hello")
2. Open this URL in your browser (replace `<YOUR_BOT_TOKEN>` with your actual token):
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. Look for the `"chat"` object in the response JSON. The `"id"` field is your chat ID:
   ```json
   {
     "update_id": 123456789,
     "message": {
       "chat": {
         "id": -1001234567890,  // <-- This is your chat ID
         "type": "private"
       }
     }
   }
   ```

### Method 2: Using curl

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

Look for the `"id"` field under `"chat"`.

### For Group Chats

If you want notifications sent to a group:

1. Add your bot to the Telegram group
2. Send a message in the group mentioning the bot
3. Use the same `getUpdates` method above
4. The chat ID will be negative (e.g., `-1001234567890`)

## Step 3: Configure Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
```

**Important Notes:**
- Both variables are **optional**. If not configured, the command will run normally without sending notifications
- Use your actual bot token and chat ID from the previous steps
- Chat IDs for groups are typically negative numbers
- Chat IDs for private chats can be positive or negative

## Step 4: Verify Configuration

Test that notifications work correctly:

### Option 1: Python Shell

```bash
python manage.py shell
```

```python
from aiecommerce.services.telegram_impl import TelegramNotificationService

service = TelegramNotificationService()
print(f"Configured: {service.is_configured()}")  # Should print True

# Send a test message
success = service.send_message("<b>Test</b> notification from AI Ecommerce!")
print(f"Sent: {success}")  # Should print True
```

### Option 2: Run a Dry Run

```bash
python manage.py publish_ml_product_batch --dry-run
```

You should receive a Telegram notification with dry run results.

## Notification Format

### Successful Batch (Production)
```
✅ Batch Publishing Complete

Timestamp: 2026-02-08 22:15:00
Mode: Production

Results:
✅ Success: 25
⏭️ Skipped: 5

Published IDs:
MLB123456789
MLB987654321
MLB111222333
...and 22 more
```

### Batch with Errors (Sandbox)
```
⚠️ Batch Publishing Complete (with errors)

Timestamp: 2026-02-08 22:15:00
Mode: Sandbox

Results:
✅ Success: 18
❌ Errors: 7
⏭️ Skipped: 3

Published IDs:
MLB123456789
MLB987654321
...and 16 more
```

### Dry Run
```
ℹ️ Batch Publishing Dry Run

Timestamp: 2026-02-08 22:15:00
Mode: Production (Dry Run)

Results:
✅ Would Publish: 30
⏭️ Would Skip: 2

No actual products were published.
```

## Troubleshooting

### No Notifications Received

1. **Check credentials are set:**
   ```bash
   python manage.py shell
   ```
   ```python
   import os
   print(os.environ.get('TELEGRAM_BOT_TOKEN'))
   print(os.environ.get('TELEGRAM_CHAT_ID'))
   ```

2. **Check Celery is running:**
   Notifications are sent asynchronously via Celery. Ensure the Celery worker is running:
   ```bash
   celery -A aiecommerce.config.celery worker -l info
   ```

3. **Check bot permissions:**
   - Ensure you've started a chat with the bot
   - For groups, ensure the bot is a member

4. **Check application logs:**
   ```bash
   tail -f logs/app.log | grep -i telegram
   ```

### Notification Sends But Command Still Works

This is expected behavior! Notification failures are logged but do not cause the command to fail. Check logs for details:
```bash
grep -i "telegram" logs/app.log
```

### Message Too Long Error

Telegram has a message length limit (4096 characters). If you publish many products, only the first 20 IDs are shown, with a count of remaining items.

## Security Best Practices

1. **Never commit `.env` file** - Add it to `.gitignore`
2. **Use separate bots for different environments** - Have different bots for production/staging
3. **Restrict bot access** - Only add bot to necessary groups/chats
4. **Rotate tokens periodically** - If a token is compromised, create a new bot

## Advanced Configuration

### Multiple Recipients

To send notifications to multiple chats:
1. Create a Telegram group
2. Add all recipients to the group
3. Add the bot to the group
4. Use the group chat ID in `TELEGRAM_CHAT_ID`

### Custom Formatting

To customize notification messages, edit:
```
aiecommerce/services/telegram_impl/formatters.py
```

The `format_batch_publish_stats()` function controls message content and formatting.

### Disabling Notifications

Simply remove or comment out the environment variables:
```bash
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

The command will continue to work normally without sending notifications.

## References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [BotFather Commands](https://core.telegram.org/bots#6-botfather)
- [HTML Formatting in Telegram](https://core.telegram.org/bots/api#html-style)
