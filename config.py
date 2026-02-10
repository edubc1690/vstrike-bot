import os
import logging
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

# --- Core Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "715520483"))
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "YourBotName")
PORT = int(os.getenv("PORT", 5000))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default_secret")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000")
RETURN_URL_BASE = os.getenv("RETURN_URL_BASE", f"https://t.me/{TELEGRAM_BOT_USERNAME}")

# --- Payment Gateways ---
OXAPAY_API_KEY = os.getenv("OXAPAY_API_KEY")
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY")
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")
# Wallet para Transak (USDT TRC20)
# Wallet para Transak (USDT TRC20)
USDT_WALLET_ADDRESS = os.getenv("USDT_WALLET_ADDRESS")

# --- Stripe ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# --- Business Logic ---
VIP_PRICE_USD = 10.00
STARS_PRICE = 500  # Approx $10 USD

# --- Database ---
DB_NAME = "vstrike_crm.db"

# --- Logging Configuration ---
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )
    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Validate critical settings
def validate_config():
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not WEBHOOK_URL: missing.append("WEBHOOK_URL")
    
    if missing:
        print(f"CRITICAL ERROR: Missing environment variables: {', '.join(missing)}")
        return False
    return True
