import os
import requests
import json
import hmac
import hashlib
import base64
import time
import logging
from typing import Optional, Dict, Any
from requests.exceptions import RequestException, Timeout, ConnectionError
from dotenv import load_dotenv
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

load_dotenv()

OXAPAY_API_KEY = os.getenv("OXAPAY_API_KEY")
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY")
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
RETURN_URL_BASE = os.getenv("RETURN_URL_BASE", "https://t.me/YourBotName")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "YourBotName")
USDT_WALLET_ADDRESS = os.getenv("USDT_WALLET_ADDRESS")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

try:
    import stripe
except ImportError:
    stripe = None



class PaymentGateway:
    """Base class para payment gateways con manejo robusto de errores"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'V-Strike-Bot/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, url: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Realizar petición HTTP con reintentos y manejo robusto de errores
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Retry attempt {attempt} for {url}, waiting {wait_time}s")
                    time.sleep(wait_time)
                
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                
                # Validar que sea JSON válido
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {url}: {e}")
                    return None
                
            except Timeout:
                logger.error(f"Timeout after {self.timeout}s for {url} (attempt {attempt + 1})")
                if attempt == self.max_retries:
                    logger.error(f"All retries failed for {url}")
                    return None
                    
            except ConnectionError as e:
                logger.error(f"Connection error for {url}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"All connection attempts failed for {url}")
                    return None
                    
            except RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"All request attempts failed for {url}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"All attempts failed for {url}")
                    return None
        
        return None
    
    def create_payment(self, amount, currency="USD", order_id=None, user_id=None):
        raise NotImplementedError


class OxaPay(PaymentGateway):
    def __init__(self):
        super().__init__(timeout=30, max_retries=3)
        
    def create_payment(self, amount: float, currency: str = "USD", 
                      order_id: Optional[str] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        url = "https://api.oxapay.com/merchants/request"
        
        if not OXAPAY_API_KEY:
            logger.error("OxaPay: Missing API key")
            return None
            
        if amount <= 0:
            logger.error(f"OxaPay: Invalid amount {amount}")
            return None
            
        data = {
            "merchant": OXAPAY_API_KEY,
            "amount": round(amount, 2),
            "currency": currency.upper(),
            "lifeTime": 30,
            "feePaidByPayer": 0,
            "underPaidCover": 0,
            "callbackUrl": f"{WEBHOOK_URL}/webhook/oxapay",
            "returnUrl": RETURN_URL_BASE,
            "description": f"Order {order_id} for user {user_id}",
            "orderId": order_id
        }
        
        logger.info(f"OxaPay: Creating payment for order {order_id}, amount {amount}")
        
        response = self._make_request("POST", url, data)
        
        if response:
            if response.get("result") == 100:
                logger.info(f"OxaPay: Payment created successfully - {response.get('trackId')}")
                return {
                    "trackId": response.get("trackId"),
                    "payLink": response.get("payLink"),
                    "amount": response.get("amount"),
                    "currency": response.get("currency")
                }
            else:
                logger.error(f"OxaPay: API error - {response}")
                return None
        
        return None


class Cryptomus(PaymentGateway):
    def __init__(self):
        super().__init__(timeout=30, max_retries=3)
        
    def _sign_request(self, data: Dict[str, Any]) -> str:
        """Generar firma Cryptomus MD5"""
        api_key = CRYPTOMUS_API_KEY or ""
        if not api_key:
            return ""
            
        payload = json.dumps(data, separators=(',', ':'))
        sign_string = base64.b64encode(payload.encode()).decode() + api_key
        return hashlib.md5(sign_string.encode()).hexdigest()
        
    def create_payment(self, amount: float, currency: str = "USD", 
                      order_id: Optional[str] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        url = "https://api.cryptomus.com/v1/payment"
        
        if not CRYPTOMUS_API_KEY or not CRYPTOMUS_MERCHANT_ID:
            logger.error("Cryptomus: Missing API key or merchant ID")
            return None
            
        if amount <= 0:
            logger.error(f"Cryptomus: Invalid amount {amount}")
            return None
        
        data = {
            "amount": str(round(amount, 2)),
            "currency": currency.upper(),
            "order_id": str(order_id) if order_id else "",
            "url_callback": f"{WEBHOOK_URL}/webhook/cryptomus",
            "url_return": RETURN_URL_BASE,
            "is_payment_multiple": False,
            "lifetime": 1800
        }
        
        sign = self._sign_request(data)
        if not sign:
            logger.error("Cryptomus: Failed to generate signature")
            return None
            
        headers = {
            "merchant": CRYPTOMUS_MERCHANT_ID,
            "sign": sign,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Cryptomus: Creating payment for order {order_id}, amount {amount}")
        
        response = self._make_request("POST", url, data, headers)
        
        if response:
            if response.get("state") == 0 and "result" in response:
                logger.info(f"Cryptomus: Payment created successfully - {response['result'].get('uuid')}")
                return {
                    "uuid": response["result"].get("uuid"),
                    "url": response["result"].get("url"),
                    "amount": response["result"].get("amount"),
                    "currency": response["result"].get("currency")
                }
            else:
                logger.error(f"Cryptomus: API error - {response}")
                return None
        
        return None


class NOWPayments(PaymentGateway):
    def __init__(self):
        super().__init__(timeout=30, max_retries=3)
        
    def create_payment(self, amount: float, currency: str = "USD", 
                      order_id: Optional[str] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        url = "https://api.nowpayments.io/v1/invoice"
        
        if not NOWPAYMENTS_API_KEY:
            logger.error("NOWPayments: Missing API key")
            return None
            
        if amount <= 0:
            logger.error(f"NOWPayments: Invalid amount {amount}")
            return None
        
        headers = {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json"
        }
        
        data = {
            "price_amount": round(amount, 2),
            "price_currency": currency.upper(),
            "ipn_callback_url": f"{WEBHOOK_URL}/webhook/nowpayments",
            "order_id": str(order_id) if order_id else "",
            "order_description": f"VIP Access for user {user_id}"
        }
        
        logger.info(f"NOWPayments: Creating invoice for order {order_id}, amount {amount}")
        
        response = self._make_request("POST", url, data, headers)
        
        if response:
            if "invoice_url" in response:
                logger.info(f"NOWPayments: Invoice created successfully - {response.get('id')}")
                return {
                    "id": response.get("id"),
                    "invoice_url": response.get("invoice_url"),
                    "price_amount": response.get("price_amount"),
                    "price_currency": response.get("price_currency")
                }
            else:
                logger.error(f"NOWPayments: API error - {response}")
                return None
        
        return None


class Transak(PaymentGateway):
    def __init__(self, api_key: str = "4fcd6904-706b-4e0e-9764-159cc4142646"):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://global.transak.com"

    def create_payment_link(self, amount: float, currency: str = "USD", 
                          crypto_currency: str = "USDT", network: str = "tron") -> Dict[str, Any]:
        """Genera un enlace de widget de Transak pre-rellenado."""
        try:
            params = {
                "apiKey": self.api_key,
                "defaultCryptoCurrency": crypto_currency,
                "defaultNetwork": network,
                "defaultFiatAmount": str(amount),
                "defaultFiatCurrency": currency,
                "walletAddress": USDT_WALLET_ADDRESS,
                "redirectURL": RETURN_URL_BASE,
                "disableWalletAddressForm": "true",
                "hideMenu": "true",
                "exchangeScreenTitle": "Pagar VIP V-Strike",
                "cryptoCurrencyList": "USDT",
                "networks": "tron"
            }
            
            query_string = urlencode(params)
            payment_url = f"{self.base_url}?{query_string}"
            
            return {
                "ok": True,
                "pay_url": payment_url,
                "order_id": f"transak_{int(time.time())}",
                "amount": amount,
                "currency": currency
            }
            
        except Exception as e:
            logger.error(f"Error generando link Transak: {e}")
            return {"ok": False, "error": str(e)}


class StripePayment(PaymentGateway):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or STRIPE_SECRET_KEY
        if stripe and self.api_key:
            stripe.api_key = self.api_key
            
    def create_payment(self, amount: float, currency: str = "USD", 
                      order_id: Optional[str] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Crea una sesión de Stripe Checkout"""
        if not stripe:
            logger.error("Stripe library not installed")
            return None
            
        if not self.api_key:
            logger.error("Stripe: Missing API Key")
            return None
            
        try:
            # Crear sesión de Checkout
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': 'Acceso VIP V-Strike',
                            'description': f'Orden {order_id} para usuario {user_id}',
                        },
                        'unit_amount': int(amount * 100),  # Centavos
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{RETURN_URL_BASE}?status=success&order_id={order_id}",
                cancel_url=f"{RETURN_URL_BASE}?status=cancel",
                client_reference_id=str(user_id),
                metadata={
                    "order_id": str(order_id),
                    "user_id": str(user_id)  
                }
            )
            
            logger.info(f"Stripe: Session created successfully - {session.id}")
            return {
                "id": session.id,
                "url": session.url,
                "amount": amount,
                "currency": currency
            }
            
        except Exception as e:
            logger.error(f"Stripe Error: {e}")
            return None

# ============================================================
# FUNCIÓN PRINCIPAL: generate_payment_link
# Esta es la ÚNICA función que bot.py debe importar y usar.
# Llama a gateway.create_payment() (NO create_invoice).
# ============================================================
def generate_payment_link(method: str, amount: float, order_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Generar enlace de pago con validación y manejo robusto de errores.
    
    Args:
        method: Método de pago ("OxaPay", "Cryptomus", "NOWPayments", "Transak")
        amount: Monto del pago
        order_id: ID único de la orden
        user_id: ID del usuario
        
    Returns:
        Dict con datos del pago o None si hay error
    """
    
    # Validar inputs
    if not method or not amount or not order_id or not user_id:
        logger.error("generate_payment_link: Missing required parameters")
        return None
        
    if amount <= 0:
        logger.error(f"generate_payment_link: Invalid amount {amount}")
        return None
        
    # Handle Transak specifically (usa create_payment_link, no create_payment)
    if method == "Transak":
        if not USDT_WALLET_ADDRESS:
            logger.error("Transak: Wallet USDT no configurada")
            return None
        client = Transak()
        return client.create_payment_link(amount=amount)

    if method not in ["OxaPay", "Cryptomus", "NOWPayments", "Stripe"]:
        logger.error(f"generate_payment_link: Unsupported method {method}")
        return None
    
    try:
        gateway = None
        
        if method == "OxaPay":
            gateway = OxaPay()
            if not OXAPAY_API_KEY: 
                logger.warning("OxaPay: Using mock response (no API key)")
                return {"trackId": order_id, "payLink": f"https://oxapay.com/pay/{order_id} (MOCK)"}
                
        elif method == "Cryptomus":
            gateway = Cryptomus()
            if not CRYPTOMUS_API_KEY:
                logger.warning("Cryptomus: Using mock response (no API key)")
                return {"uuid": order_id, "url": f"https://cryptomus.com/pay/{order_id} (MOCK)"}
                
        elif method == "NOWPayments":
            gateway = NOWPayments()
            if not NOWPAYMENTS_API_KEY:
                logger.warning("NOWPayments: Using mock response (no API key)")
                return {"id": order_id, "invoice_url": f"https://nowpayments.io/payment/{order_id} (MOCK)"}
                
        elif method == "Stripe":
            gateway = StripePayment()
            if not STRIPE_SECRET_KEY:
                logger.warning("Stripe: Using mock response (no API key)")
                return {"id": "mock_sess", "url": "https://stripe.com/docs/testing (MOCK)"}

        
        if gateway:
            result = gateway.create_payment(
                amount=float(amount), 
                order_id=str(order_id), 
                user_id=int(user_id)
            )
            
            if result:
                logger.info(f"Payment link generated successfully for {method} - order {order_id}")
                return result
            else:
                logger.error(f"Failed to generate payment link for {method}")
                return None
                
    except Exception as e:
        logger.error(f"Error generating payment link for {method}: {e}")
        return None
    
    return None
