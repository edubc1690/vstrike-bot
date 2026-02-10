import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock
import os
import config

logger = logging.getLogger(__name__)

DB_NAME = config.DB_NAME
_pool_lock = Lock()
_connection_pool = {}

class DatabaseManager:
    """Manager thread-safe para SQLite con connection pooling optimizado"""
    
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self._local_locks = {}
        
    @contextmanager
    def get_connection(self):
        """
        Context manager para conexiones thread-safe
        """
        thread_id = threading.get_ident()
        
        with _pool_lock:
            if thread_id not in _connection_pool:
                _connection_pool[thread_id] = []
        
        # Obtener o crear conexión
        conn = None
        try:
            with _pool_lock:
                if _connection_pool[thread_id]:
                    conn = _connection_pool[thread_id].pop()
            
            if conn is None:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                # Optimizaciones SQLite
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA cache_size = 10000')
                conn.execute('PRAGMA mmap_size = 268435456')  # 256MB
                conn.execute('PRAGMA temp_store = MEMORY')
            
            yield conn
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            # Devolver conexión al pool
            if conn and len(_connection_pool[thread_id]) < 5:  # Max 5 por thread
                with _pool_lock:
                    _connection_pool[thread_id].append(conn)
            elif conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Ejecutar query con return de resultados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Ejecutar update/delete/insert con return de rowcount"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Ejecutar multiple inserts/updates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

# Instancia global
_db_manager = DatabaseManager()

def init_db():
    """Inicializar base de datos con schema optimizado"""
    
    # Tabla Users con índices optimizados
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        join_date TEXT NOT NULL,
        last_interaction TEXT NOT NULL,
        is_vip BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Tabla Transactions con índices para rendimiento
    create_transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        metadata TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        timestamp TEXT NOT NULL,
        processed_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
    )
    """
    
    # Crear tablas
    _db_manager.execute_update(create_users_table)
    _db_manager.execute_update(create_transactions_table)
    
    # Crear índices para optimización
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_is_vip ON users(is_vip)",
        "CREATE INDEX IF NOT EXISTS idx_users_last_interaction ON users(last_interaction)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_method ON transactions(method)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_status_timestamp ON transactions(status, timestamp)",
    ]
    
    for index_query in indexes:
        try:
            _db_manager.execute_update(index_query)
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    logger.info("Database initialized with optimized schema")

def add_user(telegram_id: int) -> bool:
    """Agregar o actualizar usuario de forma thread-safe"""
    try:
        now = datetime.now().isoformat()
        
        # Verificar si existe
        existing = _db_manager.execute_query(
            "SELECT telegram_id FROM users WHERE telegram_id = ?", 
            (telegram_id,)
        )
        
        if not existing:
            # Insertar nuevo usuario
            query = """
            INSERT INTO users (telegram_id, join_date, last_interaction, is_vip, updated_at)
            VALUES (?, ?, ?, 0, ?)
            """
            _db_manager.execute_update(query, (telegram_id, now, now, now))
        else:
            # Actualizar usuario existente
            query = """
            UPDATE users SET last_interaction = ?, updated_at = ? 
            WHERE telegram_id = ?
            """
            _db_manager.execute_update(query, (now, now, telegram_id))
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding user {telegram_id}: {e}")
        return False

def get_user(telegram_id: int) -> Optional[Tuple]:
    """Obtener usuario de forma thread-safe"""
    try:
        result = _db_manager.execute_query(
            "SELECT * FROM users WHERE telegram_id = ?", 
            (telegram_id,)
        )
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {e}")
        return None

def create_transaction(tx_id: str, user_id: int, amount: float, 
                       method: str, metadata: str) -> bool:
    """Crear transacción con validación y logging"""
    try:
        # Validar inputs usando el validador
        from validator import validate_transaction_input
        validated_data = validate_transaction_input(tx_id, user_id, amount, method, metadata)
        
        if not validated_data:
            return False
        
        now = datetime.now().isoformat()
        
        query = """
        INSERT INTO transactions 
        (tx_id, user_id, amount, method, metadata, status, timestamp, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        _db_manager.execute_update(
            query, 
            (
                validated_data["tx_id"], 
                validated_data["user_id"], 
                validated_data["amount"], 
                validated_data["method"], 
                validated_data["metadata"], 
                "pending", 
                now, 
                now
            )
        )
        
        logger.info(f"Transaction created: {tx_id} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating transaction {tx_id}: {e}")
        return False

def update_transaction_status(tx_id: str, status: str) -> bool:
    """Actualizar status de transacción con efectos colaterales"""
    try:
        now = datetime.now().isoformat()
        
        # Actualizar transacción
        query = """
        UPDATE transactions 
        SET status = ?, processed_at = ?, updated_at = ?
        WHERE tx_id = ?
        """
        row_count = _db_manager.execute_update(query, (status, now, now, tx_id))
        
        if row_count == 0:
            logger.warning(f"Transaction not found: {tx_id}")
            return False
        
        # Si es completed, actualizar usuario a VIP
        if status == "completed":
            user_result = _db_manager.execute_query(
                "SELECT user_id FROM transactions WHERE tx_id = ?", 
                (tx_id,)
            )
            
            if user_result:
                user_id = user_result[0][0]
                _db_manager.execute_update(
                    "UPDATE users SET is_vip = 1, updated_at = ? WHERE telegram_id = ?", 
                    (now, user_id)
                )
                logger.info(f"User {user_id} upgraded to VIP")
        
        logger.info(f"Transaction {tx_id} updated to {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating transaction {tx_id}: {e}")
        return False

def get_daily_stats() -> Dict[str, Any]:
    """Obtener estadísticas diarias con queries optimizados"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        today_start = f"{today}T00:00:00"
        today_end = f"{today}T23:59:59"
        
        # Ventas del día (query optimizado con índice compuesto)
        daily_sales_result = _db_manager.execute_query("""
            SELECT COUNT(*) FROM transactions 
            WHERE status = 'completed' 
            AND timestamp BETWEEN ? AND ?
        """, (today_start, today_end))
        daily_sales = daily_sales_result[0][0] if daily_sales_result else 0
        
        # Ingresos totales
        total_revenue_result = _db_manager.execute_query("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE status = 'completed'
        """)
        total_revenue = total_revenue_result[0][0] if total_revenue_result else 0.0
        
        # Método más popular (query eficiente)
        popular_result = _db_manager.execute_query("""
            SELECT method, COUNT(*) as count 
            FROM transactions 
            WHERE status = 'completed' 
            GROUP BY method 
            ORDER BY count DESC 
            LIMIT 1
        """)
        
        popular_method = popular_result[0][0] if popular_result else "N/A"
        
        # Estadísticas adicionales
        total_users_result = _db_manager.execute_query("""
            SELECT COUNT(*) FROM users WHERE is_vip = 1
        """)
        total_vip_users = total_users_result[0][0] if total_users_result else 0
        
        return {
            "daily_sales": daily_sales,
            "total_revenue": float(total_revenue),
            "popular_method": popular_method,
            "total_vip_users": total_vip_users
        }
        
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return {
            "daily_sales": 0,
            "total_revenue": 0.0,
            "popular_method": "N/A",
            "total_vip_users": 0
        }

def get_user_transactions(user_id: int, limit: int = 10) -> List[Tuple]:
    """Obtener transacciones de usuario con paginación"""
    try:
        result = _db_manager.execute_query("""
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, limit))
        return result
    except Exception as e:
        logger.error(f"Error getting user transactions: {e}")
        return []

def cleanup_old_sessions(days: int = 30) -> int:
    """Limpiar sesiones antiguas para mantenimiento"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        result = _db_manager.execute_update("""
            UPDATE users 
            SET last_interaction = ?, updated_at = ?
            WHERE last_interaction < ? AND is_vip = 0
        """, (cutoff_date, datetime.now().isoformat(), cutoff_date))
        
        logger.info(f"Cleaned up {result} old user sessions")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return 0

def get_connection():
    """Función de compatibilidad con código existente"""
    return _db_manager.get_connection()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Database initialized with optimized schema")
