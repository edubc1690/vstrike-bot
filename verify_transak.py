
import os
from payments import generate_payment_link, USDT_WALLET_ADDRESS, Transak

def test_transak_link():
    print(f"Testing Transak Link Generation...")
    print(f"Configured Wallet: {USDT_WALLET_ADDRESS}")
    
    amount = 10.0
    user_id = 123456789
    
    # Test unified factory
    print("\n[1] Testing generate_payment_link('transak')...")
    result = generate_payment_link('transak', amount, user_id)
    
    if result.get('ok'):
        url = result['pay_url']
        print(f"SUCCESS: Generated URL: {url}")
        
        # Validation
        if USDT_WALLET_ADDRESS not in url:
            print("❌ ERROR: Wallet address not found in URL!")
        else:
            print("✅ Wallet address found in URL parameters.")
            
        if "disableWalletAddressForm=true" not in url:
             print("❌ ERROR: Wallet address form not disabled!")
        else:
             print("✅ Wallet address form disabled (Security checks out).")
    else:
        print(f"❌ FAILED: {result.get('error')}")

if __name__ == "__main__":
    if not USDT_WALLET_ADDRESS:
        print("⚠️  ADVERTENCIA: USDT_WALLET_ADDRESS no está definido en el entorno para este test.")
        # Mocking for test if env parsing fails in standalone script (though it should work if .env is loaded in payments.py)
        import payments
        payments.USDT_WALLET_ADDRESS = "TTpXe...MOCK"
        
    test_transak_link()
