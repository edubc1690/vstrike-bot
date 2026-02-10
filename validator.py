import re
import uuid
import json
import logging
import time
import secrets
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Resultado de validación con mensajes de error"""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Any = None

class InputValidator:
    """Validador y sanitizador de inputs para seguridad"""
    
    # Patrones regex para validación
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    ORDER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
    TELEGRAM_ID_PATTERN = re.compile(r'^\d{1,20}$')
    AMOUNT_PATTERN = re.compile(r'^\d+(\.\d{1,2})?$')
    PAYMENT_METHOD_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> ValidationResult:
        """Validar formato UUID"""
        if not uuid_str or not isinstance(uuid_str, str):
            return ValidationResult(False, "UUID is required and must be string")
            
        cleaned_uuid = uuid_str.strip()
        
        if not InputValidator.UUID_PATTERN.match(cleaned_uuid):
            return ValidationResult(False, f"Invalid UUID format: {uuid_str}")
            
        return ValidationResult(True, None, cleaned_uuid)
    
    @staticmethod
    def validate_order_id(order_id: str) -> ValidationResult:
        """Validar ID de orden"""
        if not order_id or not isinstance(order_id, str):
            return ValidationResult(False, "Order ID is required and must be string")
            
        cleaned_id = re.sub(r'[^\w\-]', '', str(order_id).strip())
        
        if len(cleaned_id) < 3 or len(cleaned_id) > 64:
            return ValidationResult(False, "Order ID must be 3-64 characters")
            
        if not InputValidator.ORDER_ID_PATTERN.match(cleaned_id):
            return ValidationResult(False, f"Invalid order ID format: {order_id}")
            
        return ValidationResult(True, None, cleaned_id)
    
    @staticmethod
    def validate_telegram_id(telegram_id: Union[int, str]) -> ValidationResult:
        """Validar ID de Telegram"""
        if telegram_id is None:
            return ValidationResult(False, "Telegram ID is required")
            
        try:
            # Convertir a entero y limpiar
            if isinstance(telegram_id, str):
                cleaned_id = re.sub(r'[^\d]', '', telegram_id.strip())
                if not cleaned_id:
                    return ValidationResult(False, "Invalid Telegram ID format")
                telegram_id = int(cleaned_id)
            else:
                telegram_id = int(telegram_id)
                
            if telegram_id <= 0:
                return ValidationResult(False, "Telegram ID must be positive")
                
            if telegram_id > 9999999999:  # Límite razonable
                return ValidationResult(False, "Telegram ID too large")
                
            return ValidationResult(True, None, telegram_id)
            
        except (ValueError, TypeError):
            return ValidationResult(False, f"Invalid Telegram ID: {telegram_id}")
    
    @staticmethod
    def validate_amount(amount: Union[int, float, str]) -> ValidationResult:
        """Validar monto de pago"""
        if amount is None:
            return ValidationResult(False, "Amount is required")
            
        try:
            # Convertir a float
            if isinstance(amount, str):
                cleaned_amount = re.sub(r'[^\d.]', '', amount.strip())
                if not cleaned_amount or cleaned_amount.count('.') > 1:
                    return ValidationResult(False, "Invalid amount format")
                amount = float(cleaned_amount)
            else:
                amount = float(amount)
                
            if amount <= 0:
                return ValidationResult(False, "Amount must be positive")
                
            if amount > 10000:  # Límite razonable para prevención de fraudes
                return ValidationResult(False, "Amount exceeds maximum allowed")
                
            # Redondear a 2 decimales
            amount = round(amount, 2)
            
            return ValidationResult(True, None, amount)
            
        except (ValueError, TypeError):
            return ValidationResult(False, f"Invalid amount: {amount}")
    
    @staticmethod
    def validate_payment_method(method: str) -> ValidationResult:
        """Validar método de pago"""
        if not method or not isinstance(method, str):
            return ValidationResult(False, "Payment method is required and must be string")
            
        cleaned_method = method.strip()
        valid_methods = ["OxaPay", "Cryptomus", "NOWPayments", "Stars"]
        
        # Check case-insensitive
        match = next((m for m in valid_methods if m.lower() == cleaned_method.lower()), None)
        
        if not match:
            return ValidationResult(
                False, 
                f"Invalid payment method. Valid methods: {', '.join(valid_methods)}"
            )
            
        return ValidationResult(True, None, match)
    
    @staticmethod
    def validate_status(status: str) -> ValidationResult:
        """Validar status de transacción"""
        if not status or not isinstance(status, str):
            return ValidationResult(False, "Status is required and must be string")
            
        cleaned_status = status.strip().lower()
        valid_statuses = ["pending", "completed", "failed", "cancelled", "refunded"]
        
        if cleaned_status not in valid_statuses:
            return ValidationResult(
                False, 
                f"Invalid status. Valid statuses: {', '.join(valid_statuses)}"
            )
            
        return ValidationResult(True, None, cleaned_status)
    
    @staticmethod
    def validate_webhook_payload(data: Dict[str, Any]) -> ValidationResult:
        """Validar payload de webhook"""
        if not data or not isinstance(data, dict):
            return ValidationResult(False, "Webhook payload must be a dictionary")
        
        # Validar campos obligatorios
        required_fields = ["order_id"]
        for field in required_fields:
            if field not in data:
                return ValidationResult(False, f"Missing required field: {field}")
        
        # Validar order_id
        order_validation = InputValidator.validate_order_id(str(data.get("order_id")))
        if not order_validation.is_valid:
            return ValidationResult(False, f"Invalid order_id: {order_validation.error_message}")
        
        return ValidationResult(True, None, data)
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 255) -> str:
        """Sanitizar string para seguridad"""
        if not text or not isinstance(text, str):
            return ""
            
        # Remover caracteres peligrosos
        cleaned = re.sub(r'[<>"\';]', '', text.strip())
        
        # Limitar longitud
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            
        return cleaned
    
    @staticmethod
    def generate_secure_order_id(prefix: str = "order") -> str:
        """Generar ID de orden seguro"""
        timestamp = int(time.time() * 1000)
        random_part = secrets.token_hex(4).upper()
        return f"{prefix}_{timestamp}_{random_part}"

# Función helper para validación de IDs de orden

class TransactionValidator:
    """Validador específico para transacciones"""
    
    @staticmethod
    def validate_transaction_data(tx_data: Dict[str, Any]) -> ValidationResult:
        """Validar datos completos de transacción"""
        if not tx_data or not isinstance(tx_data, dict):
            return ValidationResult(False, "Transaction data must be a dictionary")
        
        # Validar campos obligatorios
        validations = [
            InputValidator.validate_order_id(str(tx_data.get("order_id"))),
            InputValidator.validate_telegram_id(tx_data.get("user_id")),
            InputValidator.validate_amount(tx_data.get("amount")),
            InputValidator.validate_payment_method(tx_data.get("method")),
        ]
        
        for validation in validations:
            if not validation.is_valid:
                return validation
        
        return ValidationResult(True, None, tx_data)
    
    @staticmethod
    def sanitize_transaction_metadata(metadata: Union[str, Dict]) -> str:
        """Sanitizar metadata de transacción"""
        if isinstance(metadata, dict):
            # Sanitizar valores string en el dict
            sanitized = {}
            for key, value in metadata.items():
                if isinstance(value, str):
                    sanitized[key] = InputValidator.sanitize_string(value, 500)
                else:
                    sanitized[key] = value
            return json.dumps(sanitized)
        elif isinstance(metadata, str):
            return InputValidator.sanitize_string(metadata, 1000)
        else:
            return str(metadata)

# Alias para compatibilidad
validate_uuid = InputValidator.validate_uuid
validate_order_id = InputValidator.validate_order_id
validate_telegram_id = InputValidator.validate_telegram_id
validate_amount = InputValidator.validate_amount
validate_payment_method = InputValidator.validate_payment_method
validate_status = InputValidator.validate_status
sanitize_string = InputValidator.sanitize_string

def validate_transaction_input(tx_id: Optional[str], user_id: Optional[int], amount: Optional[float], 
                            method: Optional[str], metadata: Any = None) -> Optional[Dict[str, Any]]:
    """
    Función helper para validar todos los inputs de transacción
    
    Args:
        tx_id: ID de transacción
        user_id: ID de usuario
        amount: Monto
        method: Método de pago
        metadata: Metadata adicional
        
    Returns:
        Dict con datos validados o None si hay error
    """
    try:
        # Validar cada campo
        if not tx_id:
            logger.error("Transaction ID is required")
            return None
        
        tx_validation = InputValidator.validate_order_id(tx_id)
        if not tx_validation.is_valid:
            logger.error(f"Transaction ID validation failed: {tx_validation.error_message}")
            return None
        
        if user_id is None:
            logger.error("User ID is required")
            return None
        
        user_validation = InputValidator.validate_telegram_id(user_id)
        if not user_validation.is_valid:
            logger.error(f"User ID validation failed: {user_validation.error_message}")
            return None
        
        if amount is None:
            logger.error("Amount is required")
            return None
            
        amount_validation = InputValidator.validate_amount(amount)
        if not amount_validation.is_valid:
            logger.error(f"Amount validation failed: {amount_validation.error_message}")
            return None
        
        if not method:
            logger.error("Payment method is required")
            return None
            
        method_validation = InputValidator.validate_payment_method(method)
        if not method_validation.is_valid:
            logger.error(f"Payment method validation failed: {method_validation.error_message}")
            return None
        
        # Sanitizar metadata
        sanitized_metadata = TransactionValidator.sanitize_transaction_metadata(metadata)
        
        return {
            "tx_id": tx_validation.sanitized_value,
            "user_id": user_validation.sanitized_value,
            "amount": amount_validation.sanitized_value,
            "method": method_validation.sanitized_value,
            "metadata": sanitized_metadata
        }
        
    except Exception as e:
        logger.error(f"Error in transaction validation: {e}")
        return None