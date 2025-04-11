# Instagram Unfriender Bot

A Telegram bot that tracks unfollows from specified Instagram accounts and sends notifications.

## Features

- Track unfollows from public or private Instagram accounts
- Automated follow requests for private accounts
- Customizable check intervals
- Admin commands for technical account management
- Beautiful inline keyboard interface

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/insta-unfriender.git
   cd insta-unfriender
   ```

2. Create and configure `.env` file (use `.env.example` as a template):
   ```
   cp .env.example .env
   # Edit .env with your values
   ```

3. Run with Docker:
   ```
   ./build_and_run.sh
   ```

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `ADMIN_CHAT_ID`: Telegram chat ID of admin user
- `INSTAGRAM_USERNAME`: Technical Instagram account username for private profiles
- `INSTAGRAM_PASSWORD`: Technical Instagram account password
- `CHECK_INTERVAL_MINUTES`: How often to check for unfollows (default: 60)
- `DATABASE_URL`: Database connection string

## Admin Commands

- `/set_tech_account` - Change technical Instagram account credentials
- `/set_check_interval` - Change the frequency of unfollower checks
- `/stats` - Show bot statistics

## Troubleshooting

### Instagrapi Exceptions
If you encounter issues with imports from the instagrapi library, check the available exceptions using the included utility script:

```bash
python check_exceptions.py
```

This will print all available exception classes in your installed instagrapi version. You may need to update the code to use the correct exception names.

### System Dependencies
Make sure all system dependencies for Pillow are installed if you're running outside of Docker:
- libjpeg-dev
- zlib1g-dev
- libpng-dev

## License

See the [LICENSE](LICENSE) file for details. 