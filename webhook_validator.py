import hmac
import hashlib
import base64
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class WebhookValidator:
    """Validación segura de webhooks para diferentes proveedores de pago"""
    
    @staticmethod
    def verify_oxapay(payload: str, signature: Optional[str], api_key: str) -> bool:
        """
        Validar webhook de OxaPay usando HMAC-SHA256
        """
        if not signature or not api_key:
            logger.warning("OxaPay: Missing signature or API key")
            return False
            
        try:
            expected_signature = hmac.new(
                api_key.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"OxaPay signature validation error: {e}")
            return False
    
    @staticmethod
    def verify_cryptomus(data: Dict[str, Any], api_key: str) -> bool:
        """
        Validar webhook de Cryptomus usando MD5 hash
        """
        if not api_key:
            logger.warning("Cryptomus: Missing API key")
            return False
            
        received_sign = data.get('sign')
        if not received_sign:
            logger.warning("Cryptomus: Missing sign field in payload")
            return False
            
        try:
            # Remover el campo sign para validar
            payload_copy = data.copy()
            del payload_copy['sign']
            
            # Ordenar claves y crear JSON
            sorted_json = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))
            
            # Codificar en base64 y agregar API key
            base64_encoded = base64.b64encode(sorted_json.encode()).decode()
            sign_string = base64_encoded + api_key
            
            expected_sign = hashlib.md5(sign_string.encode()).hexdigest()
            
            return hmac.compare_digest(expected_sign, received_sign)
            
        except Exception as e:
            logger.error(f"Cryptomus signature validation error: {e}")
            return False
    
    @staticmethod
    def verify_nowpayments(payload: str, signature: Optional[str], ipn_secret: str) -> bool:
        """
        Validar webhook de NOWPayments usando HMAC-SHA512
        """
        if not signature or not ipn_secret:
            logger.warning("NOWPayments: Missing signature or IPN secret")
            return False
            
        try:
            expected_signature = hmac.new(
                ipn_secret.encode(),
                payload.encode(),
                hashlib.sha512
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"NOWPayments signature validation error: {e}")
            return False

def validate_webhook_data(data: Dict[str, Any]) -> bool:
    """
    Validación básica de datos del webhook
    """
    if not data or not isinstance(data, dict):
        logger.error("Webhook data is not a valid dictionary")
        return False
        
    # Validar que exista al menos un ID reconocible
    # OxaPay usa 'orderId' o 'trackId', otros 'order_id'
    id_fields = ['order_id', 'orderId', 'trackId', 'id']
    
    has_id = any(field in data for field in id_fields)
    
    if not has_id:
        logger.error(f"Missing required ID field. Checked: {id_fields}")
        return False
            
    return True