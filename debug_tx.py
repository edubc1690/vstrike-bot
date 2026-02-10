import database as db
import uuid
import logging
import sys

# Setup logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

db.init_db()
user_id = 999999
order_id = f"test_{uuid.uuid4()}"
amount = 10.0

print(f"Attempting to add user {user_id}")
db.add_user(user_id)

print(f"Attempting to create transaction {order_id}")
success = db.create_transaction(order_id, user_id, amount, "OxaPay", "Debug Meta")

if success:
    print("SUCCESS")
else:
    print("FAILURE")
