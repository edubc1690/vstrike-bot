import threading
import time
import requests
import logging
import uuid
import hashlib
import hmac
import json
import os
import config
import database as db
from flask import Flask

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SystemVerifier")

# Mock Configuration for Test
TEST_PORT = 5001
TEST_SECRET = "test_secret_override"
TEST_API_KEY = "test_api_key_123"

# Override config for testing BEFORE importing bot
config.PORT = TEST_PORT
config.WEBHOOK_SECRET = TEST_SECRET
config.OXAPAY_API_KEY = TEST_API_KEY

# Now import bot, so decorators use the overridden config
from bot import app as flask_app

def run_flask_server():
    """Run Flask server in a separate thread"""
    flask_app.run(host='127.0.0.1', port=TEST_PORT, debug=False, use_reloader=False)

def generate_oxapay_signature(payload, api_key):
    """Generate HMAC-SHA256 signature"""
    return hmac.new(
        api_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_full_flow():
    logger.info("--- Starting System Verification ---")
    
    # 1. Initialize DB
    logger.info("Step 1: Initializing Database...")
    db.init_db()
    
    # 2. Create a Test User and Transaction
    user_id = 123456789
    order_id = f"test_{uuid.uuid4()}"
    amount = 10.0
    
    logger.info(f"Step 2: Creating test user {user_id} and pending transaction {order_id}...")
    db.add_user(user_id)
    db.create_transaction(order_id, user_id, amount, "OxaPay", "Test Metadata")
    
    # Verify initial state
    tx = db._db_manager.execute_query("SELECT status FROM transactions WHERE tx_id = ?", (order_id,))
    if not tx or tx[0][0] != 'pending':
        logger.error("❌ Pre-condition failed: Transaction not found or not pending")
        return False
    logger.info("✅ Transaction created successfully (Pending)")

    # 3. Start Flask Server
    logger.info("Step 3: Starting Local Webhook Server...")
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()
    time.sleep(2) # Give it time to start
    
    # 4. Simulate Webhook Call
    logger.info("Step 4: Simulating OxaPay Payment Webhook...")
    webhook_url = f"http://127.0.0.1:{TEST_PORT}/webhook/oxapay/{TEST_SECRET}"
    
    payload = {
        "merchant": TEST_API_KEY,
        "trackId": order_id, # OxaPay uses trackId or orderId depending on context, bot.py uses orderId in get check but payload might vary.
        "orderId": order_id, # Bot.py expects orderId
        "status": "Paid",
        "amount": amount,
        "currency": "USD",
        "payAmount": amount,
        "payCurrency": "USDT"
    }
    payload_json = json.dumps(payload)
    
    headers = {
        "Content-Type": "application/json",
        "X-OxaPay-Signature": generate_oxapay_signature(payload_json, TEST_API_KEY)
    }
    
    try:
        response = requests.post(webhook_url, data=payload_json, headers=headers)
        if response.status_code == 200:
            logger.info("✅ Webhook request sent successfully (200 OK)")
        else:
            logger.error(f"❌ Webhook request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Could not connect to webhook server: {e}")
        return False
        
    # 5. Check Result in DB
    logger.info("Step 5: Verifying Database Updates...")
    time.sleep(1) # Allow DB update to happen
    
    # Check Transaction Status
    tx = db._db_manager.execute_query("SELECT status FROM transactions WHERE tx_id = ?", (order_id,))
    tx_status = tx[0][0] if tx else "unknown"
    
    # Check User VIP Status
    user = db.get_user(user_id)
    is_vip = user[3] if user else 0
    
    success = True
    
    if tx_status == 'completed':
        logger.info("✅ Transaction status updated to 'completed'")
    else:
        logger.error(f"❌ Transaction status mismatch. Expected 'completed', got '{tx_status}'")
        success = False
        
    if is_vip:
        logger.info("✅ User upgraded to VIP status")
    else:
        logger.error("❌ User NOT upgraded to VIP status")
        success = False
        
    if success:
        logger.info("--- 🎉 SYSTEM VERIFICATION PASSED 🎉 ---")
        return True
    else:
        logger.error("--- ⚠️ SYSTEM VERIFICATION FAILED ⚠️ ---")
        return False

if __name__ == "__main__":
    try:
        if verify_full_flow():
            os._exit(0)
        else:
            os._exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        os._exit(0)
