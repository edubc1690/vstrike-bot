# V-Strike CRM Bot - Bot de Pagos para Telegram

Bot de Telegram para gestión de pagos VIP con múltiples métodos de pago (OxaPay, Cryptomus, NOWPayments, Telegram Stars).

## 🚀 **Características**

- ✅ **Multi-payment gateway**: OxaPay, Cryptomus, NOWPayments, Telegram Stars
- 🔒 **Seguridad robusta**: Validación de webhooks con firma HMAC/MD5
- 🏗️ **Arquitectura optimizada**: Connection pooling SQLite, thread-safe
- 📊 **Dashboard admin**: Estadísticas en tiempo real
- 🛡️ **Validación de inputs**: Sanitización y validación completa
- ⚡ **Performance**: Queries optimizados con índices
- 🔧 **Manejo de errores robusto**: Reintentos con exponential backoff

## 📋 **Requisitos**

- Python 3.9+
- Todas las dependencias en `requirements.txt`

## 🛠️ **Instalación**

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd bot-tlgr-pagos-apuestas

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## ⚙️ **Configuración**

### Variables de Entorno Obligatorias

```bash
# Bot de Telegram
TELEGRAM_BOT_TOKEN=TU_BOT_TOKEN
ADMIN_ID=TU_ADMIN_ID
TELEGRAM_BOT_USERNAME=TuBotUsername

# Servidor
PORT=5000
WEBHOOK_SECRET=tu_secreto_unico
WEBHOOK_URL=https://tu-dominio.com

# Payment Gateways
OXAPAY_API_KEY=tu_api_oxapay
CRYPTOMUS_API_KEY=tu_api_cryptomus
CRYPTOMUS_MERCHANT_ID=tu_merchant_cryptomus
NOWPAYMENTS_API_KEY=tu_api_nowpayments
NOWPAYMENTS_IPN_SECRET=tu_ipn_secret
```

### Configuración de Webhooks

Configura estos URLs en los paneles respectivos:

- **OxaPay**: `https://tu-dominio.com/webhook/oxapay/TU_SECRET`
- **Cryptomus**: `https://tu-dominio.com/webhook/cryptomus/TU_SECRET` (IP: 91.227.144.54)
- **NOWPayments**: `https://tu-dominio.com/webhook/nowpayments/TU_SECRET`

## 🚀 **Ejecución**

```bash
# Iniciar el bot
python bot.py
```

El bot iniciará:
1. Servidor Flask para webhooks (puerto 5000)
2. Bot de Telegram con polling
3. Bridge de comunicación entre Flask y Bot

## 📖 **Uso**

### Comandos del Bot

- `/start` - Iniciar sesión y mostrar bienvenida
- `/pay` - Mostrar opciones de pago
- `/status` - Ver estado VIP del usuario
- `/dashboard` - Ver estadísticas (solo admin)

### Flujo de Pago

1. Usuario ejecuta `/pay`
2. Elige método de pago (OxaPay/Cryptomus/NOWPayments/Stars)
3. Recibe enlace de pago o invoice de Stars
4. Completa el pago
5. Webhook notifica al bot
6. Usuario recibe confirmación y acceso VIP

## 🏗️ **Arquitectura**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask App     │    │  Bridge Module  │    │ Telegram Bot    │
│  (webhooks)     │◄──►│ (asyncio.Queue)│◄──►│  (asyncio)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Validation     │    │  Message Queue  │    │  User Commands │
│  (signatures)   │    │  (thread-safe)  │    │  (handlers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   SQLite + WAL  │
                    │ (optimized)     │
                    └─────────────────┘
```

## 🔒 **Seguridad Implementada**

### Webhook Validation
- **OxaPay**: HMAC-SHA256 signature validation
- **Cryptomus**: MD5 hash + IP whitelist (91.227.144.54)
- **NOWPayments**: HMAC-SHA512 header validation

### Input Validation
- Sanitización de todos los inputs
- Validación de IDs, montos, métodos de pago
- Protección contra SQL injection

### Connection Security
- Thread-safe connection pooling
- Request timeouts (30s)
- Rate limiting implícito

## 📊 **Estadísticas y Monitorización**

El dashboard admin muestra:
- Ventas diarias
- Ingresos totales
- Método de pago más popular
- Total de usuarios VIP

## 🛠️ **Mantenimiento**

### Limpieza de Base de Datos
```python
import database as db
# Limpiar sesiones antiguas (30 días)
db.cleanup_old_sessions(days=30)
```

### Logs
Los logs están configurados para mostrar:
- Errores de webhook
- Creación de transacciones
- Errores de API
- Notificaciones enviadas

## 🧪 **Testing**

```bash
# Ejecutar tests
pytest

# Formato de código
black .

# Linting
flake8 .
```

## 🔄 **Troubleshooting**

### Webhooks no funcionan
1. Verifica que WEBHOOK_URL sea HTTPS válido
2. Confirma URLs configuradas en paneles de pago
3. Revisa que los secretos coincidan
4. Verificar whitelist IP para Cryptomus

### Error de conexión
1. Confirma que el bot token sea válido
2. Verifica que el puerto esté abierto
3. Revisa variables de entorno en .env

### Base de datos corrupta
```bash
rm vstrike_crm.db
python bot.py  # Se recreará automáticamente
```

## 📝 **Cambios Recientes (v2.0)**

- ✅ Implementada validación segura de webhooks
- ✅ Optimización de SQLite con WAL mode
- ✅ Thread-safe communication bridge
- ✅ Validación robusta de inputs
- ✅ Manejo de errores con reintentos
- ✅ Connection pooling optimizado
- ✅ Índices para queries de alto rendimiento

## 📄 **Licencia**

MIT License

## 🤝 **Contribuir**

1. Fork
2. Feature branch
3. Commit changes
4. Push to branch
5. Pull request

## 📞 **Soporte**

Para soporte técnico:
- Revisa los logs del bot
- Verifica configuración de variables de entorno
- Confirma estado de webhooks en paneles de pago