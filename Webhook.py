import os
from flask import Flask, request
from telegram import Update
from bot import main  # Import the bot function from bot.py

# Initialize Flask app for the webhook
app = Flask(__name__)

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Error: BOT_TOKEN and WEBHOOK_URL must be set")

# Webhook endpoint for Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.dispatcher.process_update(update)
    return 'ok'

# Set webhook route
@app.route('/set_webhook', methods=['GET'])
def set_webhook() -> str:
    app.bot.setWebhook(WEBHOOK_URL)
    return f'Webhook set to {WEBHOOK_URL}'

if __name__ == '__main__':
    # Start the bot application using the webhook
    main()
  
