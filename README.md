# Wallet Tracking Flask App

## Introduction

The Wallet Tracking Flask App is a simple application designed to help users track their cryptocurrency wallets using a Telegram bot. Users can add, delete, and manage their wallet addresses for Bitcoin (BTC), Ethereum (ETH), and Solana (SOL) cryptocurrencies. The app utilizes Flask for the web server and integrates with the Telegram API for user interactions.

## Features

- Add and manage cryptocurrency wallet addresses for BTC, ETH, and SOL.
- Receive notifications on incoming transactions to the added wallets.
- Delete wallets when they are no longer needed.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.x
- Flask
- Telegram Bot API token
- BlockCypher API token (for BTC and ETH)
- Solana API token (for SOL)

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/wallet-tracking-app.git
   cd wallet-tracking-app


pip install -r requirements.txt

python app.py

Usage
Start the Telegram bot by sending the /start command.
Add a wallet using the /addwallet command with the coin type (e.g., BTC, ETH) and wallet address.
Delete a wallet using the /deletewallet command with the wallet address.
Receive notifications for incoming transactions.
Contributing
Feel free to contribute to the development of this app by submitting issues, feature requests, or pull requests.

License
This project is licensed under the MIT License.

Happy wallet tracking!