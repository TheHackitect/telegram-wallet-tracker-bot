from flask import Flask, render_template, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Updater, MessageHandler, Filters, CommandHandler, CallbackQueryHandler
import sqlite3
import requests
import threading
import logging
from werkzeug.serving import run_simple
from telegram import Bot, Update
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)  # Set to WARNING to suppress errors, change as needed

app = Flask(__name__)

# Replace these with your actual API tokens
BLOCKCYPHER_API_TOKEN = os.getenv("BLOCKCYPHER_API_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Base URLs for API requests
BLOCKCYPHER_BASE_URL = "https://api.blockcypher.com/v1"
SOLANA_BASE_URL = "https://api.mainnet-beta.solana.com"
VPS_HOST = "https://94.156.69.29"
PORT = 8080

# SQLite3 Database
conn = sqlite3.connect("wallets.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS wallets (telegram_id INTEGER, coin TEXT, address TEXT)")
conn.commit()

# Telegram Commands
# Telegram Buttons
def get_buttons():
    buttons = [
        [InlineKeyboardButton("Add Wallet", callback_data='add_wallet')],
        [InlineKeyboardButton("Delete Wallet", callback_data='delete_wallet')],
        [InlineKeyboardButton("Check My Wallets", callback_data='check_wallets')]
    ]
    return buttons

# Telegram Inline Keyboard
def get_inline_keyboard():
    return InlineKeyboardMarkup(get_buttons())

# Telegram Commands
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome! How can I help you?", reply_markup=get_inline_keyboard())

def add_wallet(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Please use the 'Add Wallet' button.")

def delete_wallet(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Please use the 'Delete Wallet' button.")

def check_wallets(update: Update, context: CallbackContext) -> None:
    if update.message:
        user_id = update.message.from_user.id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
    else:
        # Handle the case when user_id cannot be determined
        return

    with sqlite3.connect("wallets.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT coin, address FROM wallets WHERE telegram_id = ?", (user_id,))
        wallets = cursor.fetchall()

    if wallets:
        message = "Your wallets:\n"
        for wallet in wallets:
            message += f"{wallet[0]}: {wallet[1]}\n"
    else:
        message = "You haven't added any wallets yet."

    if update.message:
        update.message.reply_text(message, reply_markup=get_inline_keyboard())
    elif update.callback_query:
        update.callback_query.edit_message_text(text=message, reply_markup=get_inline_keyboard())


# Inline Button Callbacks
def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'add_wallet':
        query.edit_message_text(text="To add a wallet, use the command /addwallet <coin> <address>")
    elif query.data == 'delete_wallet':
        query.edit_message_text(text="To delete a wallet, use the command /deletewallet <address>")
    elif query.data == 'check_wallets':
        check_wallets(update, context)



def send_bot_message(user_id, coin_type, amount, transaction_type):
    # Replace "YOUR_BOT_TOKEN" with your actual bot token
    bot_token = TELEGRAM_BOT_TOKEN
    bot = Bot(token=bot_token)
    
    message_text = f"Transaction Update\n\nCoin: {coin_type}\nAmount: {amount}\nType: {transaction_type.capitalize()}"

    try:
        bot.send_message(chat_id=user_id, text=message_text)
    except Exception as e:
        print(f"Error sending message to user {user_id}: {str(e)}")


# Telegram Message Handler
def message_handler(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("I'm a bot, please use the provided buttons.")

def address_exists_for_user(user_id, address):
    try:
        # Ensure user_id is an integer
        user_id = int(user_id)

        with sqlite3.connect("wallets.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wallets WHERE telegram_id = ? AND address = ?", (user_id, address))
            count = cursor.fetchone()[0]
            return count > 0
    except ValueError:
        print("Error: user_id must be an integer.")
        return False
    except Exception as e:
        print(f"Error checking address existence: {e}")
        return False



def add_wallet_action(update: Update, context: CallbackContext) -> None:
    # Create a new SQLite connection and cursor inside the function
    with sqlite3.connect("wallets.db") as conn:
        cursor = conn.cursor()

        user_id = update.message.from_user.id
        args = context.args

        if len(args) != 2:
            update.message.reply_text("Usage: /addwallet <coin> <address>")
            return

        coin, address = args
        cursor.execute("INSERT INTO wallets (telegram_id, coin, address) VALUES (?, ?, ?)", (user_id, coin.upper(), address))
        conn.commit()

        # Create webhook based on the coin type
        if coin.upper() in ["BTC", "ETH"]:
            create_blockcypher_webhook(user_id, coin.upper(), address)
        elif coin.upper() == "SOLANA":
            create_solana_webhook(user_id, address)

        update.message.reply_text(f"Wallet for {coin.upper()} at {address} added successfully!")

def delete_wallet_action(update: Update, context: CallbackContext) -> None:
    # Create a new SQLite connection and cursor inside the function
    with sqlite3.connect("wallets.db") as conn:
        cursor = conn.cursor()

        user_id = update.message.from_user.id
        args = context.args

        if len(args) != 1:
            update.message.reply_text("Usage: /deletewallet <address>")
            return

        address = args[0]
        cursor.execute("DELETE FROM wallets WHERE telegram_id = ? AND address = ?", (user_id, address))
        conn.commit()

        # Notify BlockCypher and Solana to remove subscription
        if address_exists_for_user(user_id, address):
            coin_type = address_coin_type(user_id, address)
            if coin_type in ["BTC", "ETH",None]:
                delete_blockcypher_webhook(user_id, address)
            elif coin_type == "SOLANA":
                delete_solana_webhook(user_id, address)
        else:
            pass
        update.message.reply_text(f"Wallet for {address} deleted successfully!")


def address_coin_type(user_id, address):
    with sqlite3.connect("wallets.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT coin FROM wallets WHERE telegram_id = ? AND address = ?", (user_id, address))
        coin_type = cursor.fetchone()
        return coin_type[0] if coin_type else None

def create_blockcypher_webhook(user_id, coin, address):
    url = f"{BLOCKCYPHER_BASE_URL}/{coin.lower()}/main/hooks?token={BLOCKCYPHER_API_TOKEN}"
    payload = {
        "event": "tx-confirmation",
        "address": address,
        "confirmations": 1,
        "url": f"{VPS_HOST}:{PORT}/webhook/{coin.lower()}"  # Replace with your app's domain
    }
    headers = {
        "Content-Type": "application/json",
        "token": BLOCKCYPHER_API_TOKEN
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.json())

def delete_blockcypher_webhook(user_id, address):
    coin_type = address_coin_type(user_id, address)
    url = f"{BLOCKCYPHER_BASE_URL}/{coin_type.lower()}/main/hooks/{user_id}/{address}?token={BLOCKCYPHER_API_TOKEN}"
    headers = {
        "Content-Type": "application/json",
        "token": BLOCKCYPHER_API_TOKEN
    }
    response = requests.delete(url, headers=headers)
    print(response.json())

def create_solana_webhook(user_id, address):
    url = f"{SOLANA_BASE_URL}/v1/transaction/subscribe"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "accountSubscribe",
        "params": [address],
        "commitment": "finalized"
    }
    headers = {
        "Content-Type": "application/json",
        "url": f"{VPS_HOST}:{PORT}/webhook/solana"  # Replace with your app's domain
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.json())

def delete_solana_webhook(user_id, address):
    url = f"{SOLANA_BASE_URL}/v1/transaction/unsubscribe"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "accountUnsubscribe",
        "params": [address]
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.json())

# Telegram Message Handler
def message_handler(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("I'm a bot, please use the provided buttons.")


def process_blockcypher_transaction(data, coin_type):
    # Check if it's an incoming or outgoing transaction
    if data.get('incoming', False):
        address = data.get('address', '')
        user_info = get_user_by_address(address)

        if user_info and user_info['coin_type'] == coin_type:
            user_id = user_info['user_id']
            amount = data.get('amount', 0)  # Replace with the actual key in your data
            send_bot_message(user_id, coin_type, amount, 'incoming')
    else:
        # Handle outgoing transactions if needed
        pass

def process_solana_transaction(data):
    # Check if it's an incoming or outgoing transaction
    if data.get('is_incoming', False):
        address = data.get('address', '')
        user_info = get_user_by_address(address)

        if user_info and user_info['coin_type'] == 'SOLANA':
            user_id = user_info['user_id']
            amount = data.get('amount', 0)  # Replace with the actual key in your data
            send_bot_message(user_id, 'SOLANA', amount, 'incoming')
    else:
        # Handle outgoing transactions if needed
        pass

def get_user_by_address(address):
    with sqlite3.connect("wallets.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, coin FROM wallets WHERE address = ?", (address,))
        user_info = cursor.fetchone()
        return {"user_id": user_info[0], "coin_type": user_info[1]} if user_info else None


@app.route('/', methods=['GET'])
def landing_page():
    return render_template('index.html')

@app.route('/webhook/btc', methods=['POST'])
def btc_webhook():
    data = request.get_json()
    process_blockcypher_transaction(data, 'BTC')
    return "", 200

@app.route('/webhook/eth', methods=['POST'])
def eth_webhook():
    data = request.get_json()
    process_blockcypher_transaction(data, 'ETH')
    return "", 200

@app.route('/webhook/solana', methods=['POST'])
def solana_webhook():
    try:
        data = request.get_json()
        print("Received Solana Webhook Data:", data)

        # Process Solana webhook data and extract relevant information
        address = data.get('address', '')
        user_info = get_user_by_address(address)

        if user_info and user_info['coin_type'] == 'SOLANA':
            user_id = user_info['user_id']
            amount = data.get('amount', 0)  # Replace with the actual key in your data
            transaction_type = 'incoming' if data.get('is_incoming', False) else 'outgoing'

            # Send a Telegram message to the user
            send_bot_message(user_id, 'SOLANA', amount, transaction_type)

        return "", 200
    except Exception as e:
        print(f"Error processing Solana webhook: {e}")
        return "", 500

def run_flask():
    run_simple('0.0.0.0', PORT, app, use_debugger=True)

def run_telegram_bot():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register your handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addwallet", add_wallet_action, pass_args=True))
    dp.add_handler(CommandHandler("deletewallet", delete_wallet_action, pass_args=True))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    dp.add_handler(CallbackQueryHandler(button_callback))

    updater.start_polling()
    try:
        updater.idle()
    except:
        pass

if __name__ == '__main__':
    # Run Flask and Telegram bot concurrently
    flask_thread = threading.Thread(target=run_flask)
    telegram_thread = threading.Thread(target=run_telegram_bot)

    flask_thread.start()
    telegram_thread.start()

    flask_thread.join()
    telegram_thread.join()
