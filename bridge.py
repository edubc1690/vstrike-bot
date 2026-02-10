import asyncio
import logging
from typing import Optional, Dict, Any
import config

logger = logging.getLogger(__name__)

# Global queue for cross-thread/async communication
_message_queue = asyncio.Queue()

async def get_next_message():
    """Obtener el siguiente mensaje de la cola (async)"""
    return await _message_queue.get()

def send_payment_notification(order_id: str, user_id: int, message: str = "¡Pago completado!", admin_id: Optional[int] = None) -> bool:
    """
    Enviar notificación de pago desde un thread síncrono (Flask) al loop asíncrono del bot.
    
    Args:
        order_id: ID de la orden
        user_id: ID del usuario de Telegram
        message: Mensaje a enviar
        admin_id: ID del admin para notificación
        
    Returns:
        bool: True si se puso en cola correctamente
    }
    """
    try:
        # Note: We need to use call_soon_threadsafe if we are calling this from Flask thread
        # but here we just put it in a non-async thread-safe way if possible, 
        # but asyncio.Queue is not thread-safe.
        # We will use a regular queue and a task in the bot to bridge it.
        import queue
        global _sync_queue
        _sync_queue.put({
            'type': 'payment_notification',
            'order_id': order_id,
            'user_id': user_id,
            'message': message,
            'admin_id': admin_id
        })
        return True
    except Exception as e:
        logger.error(f"Error bridging notification: {e}")
        return False

# Regular thread-safe queue for Flask -> Bot communication
import queue
_sync_queue = queue.Queue()

async def bridge_task(bot):
    """Tarea asíncrona que monitorea la cola sincrónica y procesa mensajes"""
    logger.info("Bridge task started - monitoring for notifications")
    while True:
        try:
            # Non-blocking check of the sync queue
            while not _sync_queue.empty():
                data = _sync_queue.get_nowait()
                if data.get('type') == 'payment_notification':
                    await _handle_payment_notification(bot, data)
            
            await asyncio.sleep(1) # Check every second
        except Exception as e:
            logger.error(f"Error in bridge task: {e}")
            await asyncio.sleep(5)

async def _handle_payment_notification(bot, data: Dict[str, Any]):
    """Manejar notificaciones de pago en el loop del bot"""
    order_id = data.get('order_id')
    user_id = data.get('user_id')
    message = data.get('message', '¡Pago completado!')
    admin_id = data.get('admin_id') or config.ADMIN_ID
    
    try:
        # Notificar al usuario
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ {message}\n\nOrden: {order_id}\n\n🌟 Ya eres VIP!"
        )
        
        # Notificar al admin
        await bot.send_message(
            chat_id=admin_id,
            text=f"💰 Nueva venta completada!\n\nUsuario: {user_id}\nOrden: {order_id}"
        )
        
        logger.info(f"Payment notification delivered for order {order_id}")
    except Exception as e:
        logger.error(f"Error delivery notification: {e}")

def notify_user_success(order_id: str, user_id: int, admin_id: Optional[int] = None) -> bool:
    """Helper de compatibilidad"""
    return send_payment_notification(order_id, user_id, admin_id=admin_id)