# Instagram Unfriender Bot

A Telegram bot that helps you track Instagram unfollowers.

## Updated Instagram Authentication

The Instagram authentication has been improved to handle verification challenges properly. The system now includes:

- Custom challenge handlers that can process Instagram verification requests
- Support for email verification code input during first login 
- Session persistence to avoid repeated verification requests
- Random delays between API requests to avoid rate limiting

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Set your environment variables in a `.env` file:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

3. Test the Instagram authentication:
```bash
python src/test_instagram_auth.py
```
   
   **Note:** On first login, you will be prompted to enter a verification code sent to your email. After successful verification, the session will be saved for future use.

4. Run the bot:
```bash
python src/main.py
```

## Docker Deployment

1. Build the Docker image:
```bash
docker build -t insta-unfriender .
```

2. Run the container:
```bash
docker run -d --name insta-unfriender \
  -e TELEGRAM_BOT_TOKEN=your_telegram_bot_token \
  -e INSTAGRAM_USERNAME=your_instagram_username \
  -e INSTAGRAM_PASSWORD=your_instagram_password \
  insta-unfriender
```

## Handling Instagram Verification Challenges

Instagram frequently requires verification when detecting automated access. This bot handles verification in two ways:

1. **Initial Setup (Manual):** When you first run the test script, you'll need to enter the verification code sent to your email/phone. This creates a persistent session.

2. **Production (Automated):** For the bot in production, you should:
   - Run the test script first to create a valid session
   - Copy the session file to your production environment
   - The bot will use this pre-authenticated session to avoid verification prompts

If Instagram challenges the bot in production:
1. Stop the bot
2. Delete the session file
3. Run the test script again to create a new valid session
4. Restart the bot

## Troubleshooting

If you encounter authentication issues:
1. Delete the session file in the `settings` directory
2. Make sure your Instagram credentials are correct 
3. Run the test script again to generate a new session, entering the verification code when prompted

If you're still having issues, try using a proxy or waiting a few hours before trying again, as Instagram may temporarily limit your account after failed login attempts.

## Features

- Track unfollows from public or private Instagram accounts
- Automated follow requests for private accounts
- Customizable check intervals
- Admin commands for technical account management
- Beautiful inline keyboard interface
- Persistent Instagram session management to avoid verification challenges

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

## License

See the [LICENSE](LICENSE) file for details. 