"""
Sistema de logging centralizado para la aplicación
Captura todos los prints, errores y excepciones con información del usuario
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
import traceback as tb


class UserContextFilter(logging.Filter):
    """Filtro para añadir el usuario actual a los logs"""
    current_user = "SYSTEM"
    
    def filter(self, record):
        record.username = UserContextFilter.current_user
        return True


class AppLogger:
    """Gestor centralizado de logging para la aplicación"""
    
    def __init__(self, log_dir="logs", username=None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.username = username or "SYSTEM"
        
        # Configurar logger principal
        self.logger = logging.getLogger("GestorExpedientes")
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicados
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Archivo de log con fecha y usuario
        fecha = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"app_{fecha}_{self.username}.log"
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formato con usuario
        formatter = logging.Formatter(
            '[%(asctime)s] [%(username)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Añadir filtro de usuario
        user_filter = UserContextFilter()
        file_handler.addFilter(user_filter)
        console_handler.addFilter(user_filter)
        
        # Añadir handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Guardar referencia al print original
        self._original_print = print
        
        self.logger.info("="*80)
        self.logger.info("Sistema de logging inicializado")
        self.logger.info("="*80)
    
    def set_user(self, username):
        """Actualiza el usuario actual en los logs y reconfigura el archivo de log"""
        UserContextFilter.current_user = username if username else "SYSTEM"
        
        # Si cambiamos de usuario, crear un nuevo archivo de log
        if username and username != self.username:
            self.username = username
            
            # Cerrar handlers anteriores
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            
            # Crear nuevo archivo de log con el nombre del usuario
            fecha = datetime.now().strftime('%Y-%m-%d')
            log_file = self.log_dir / f"app_{fecha}_{self.username}.log"
            
            # Handler para archivo
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Handler para consola
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Formato con usuario
            formatter = logging.Formatter(
                '[%(asctime)s] [%(username)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Añadir filtro de usuario
            user_filter = UserContextFilter()
            file_handler.addFilter(user_filter)
            console_handler.addFilter(user_filter)
            
            # Añadir handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
            self.logger.info("="*80)
            self.logger.info(f"Log reconfigurado para usuario: {self.username}")
            self.logger.info("="*80)
    
    def get_logger(self):
        """Retorna el logger configurado"""
        return self.logger
    
    def override_print(self):
        """Sobrescribe la función print() global para capturar en logs"""
        def logged_print(*args, **kwargs):
            # Llamar al print original
            self._original_print(*args, **kwargs)
            
            # Capturar el mensaje
            message = ' '.join(str(arg) for arg in args)
            
            # Registrar en el log (sin intentar sobrescribir filename/lineno)
            self.logger.debug(f"[PRINT] {message}")
        
        # Reemplazar print global
        import builtins
        builtins.print = logged_print
        self.logger.info("Función print() sobrescrita para logging")
    
    def log_exception(self, exc_type, exc_value, exc_traceback):
        """Handler global para excepciones no capturadas"""
        if issubclass(exc_type, KeyboardInterrupt):
            # No registrar KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Formatear traceback
        tb_lines = tb.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)
        
        self.logger.critical("EXCEPCIÓN NO CAPTURADA:", exc_info=(exc_type, exc_value, exc_traceback))
        self.logger.critical(f"\n{tb_text}")
    
    def setup_exception_handler(self):
        """Configura el handler global de excepciones"""
        sys.excepthook = self.log_exception
        self.logger.info("Handler de excepciones configurado")


# Instancia global del logger
_app_logger = None

def get_app_logger(username=None):
    """Obtiene o crea la instancia global del logger"""
    global _app_logger
    if _app_logger is None:
        _app_logger = AppLogger(username=username)
    return _app_logger

def setup_logging(username=None):
    """Inicializa el sistema de logging completo"""
    logger_manager = get_app_logger(username=username)
    logger_manager.override_print()
    logger_manager.setup_exception_handler()
    return logger_manager.get_logger()

def set_current_user(username):
    """Actualiza el usuario actual en los logs"""
    logger_manager = get_app_logger()
    logger_manager.set_user(username)

def get_logger():
    """Obtiene el logger para usar en módulos"""
    logger_manager = get_app_logger()
    return logger_manager.get_logger()
