import os
from flask import Flask, request
from telebot import TeleBot, types
from dotenv import load_dotenv
from instaloader import Instaloader, Post

# Load environment variables
load_dotenv()

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8443))  # Default port
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Initialize bot and Flask app
bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Initialize Instaloader
loader = Instaloader()

# Login to Instagram
def instagram_login():
    try:
        # Try loading session from cookies
        loader.load_session_from_file(INSTAGRAM_USERNAME, "cookies.txt")
        print("Logged in using cookies.")
    except Exception as cookie_error:
        print(f"Cookies login failed: {cookie_error}")
        try:
            # Fall back to username/password login
            loader.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            print("Logged in using username and password.")
            # Save the session for future use
            loader.save_session_to_file("cookies.txt")
        except Exception as login_error:
            print(f"Username/password login failed: {login_error}")

# Perform login
instagram_login()

# Function to download Instagram media
def download_instagram_media(url, chat_id):
    output_path = f"downloads/{chat_id}"  # Save per user
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    try:
        # Extract the shortcode from the URL
        shortcode = url.split("/")[-2]
        post = Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=output_path)
        return f"{output_path}/{shortcode}"
    except Exception as e:
        print(f"Error downloading Instagram media: {e}")
        return f"Error: {str(e)}"

# Telegram bot handlers
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me an Instagram post URL to download it.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "Downloading media, please wait...")
    file_path = download_instagram_media(url, message.chat.id)
    if os.path.isdir(file_path):  # Check if it's a directory
        for root, dirs, files in os.walk(file_path):
            for file in files:
                with open(os.path.join(root, file), "rb") as media:
                    bot.send_document(message.chat.id, media)
        # Clean up after sending
        for root, dirs, files in os.walk(file_path):
            for file in files:
                os.remove(os.path.join(root, file))
        os.rmdir(file_path)
    else:
        bot.send_message(message.chat.id, f"Error: {file_path}")

# Flask route for webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    json_update = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "OK", 200

# Main function
if __name__ == "__main__":
    # Set webhook
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # Run Flask app
    app.run(host="0.0.0.0", port=PORT)