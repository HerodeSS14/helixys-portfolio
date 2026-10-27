import os
import sys
import json
import datetime
import traceback  # Herramienta para capturar el error exacto con su línea
from dotenv import load_dotenv
from sqlalchemy import create_engine  
from sqlalchemy.orm import sessionmaker
from models import Base

# 🌐 DETECCIÓN INTELIGENTE DE RUTAS CRÍTICAS (Soporte nativo para PyInstaller .exe --onefile)
if getattr(sys, 'frozen', False):
    # Si el programa está corriendo empaquetado como un .exe independiente
    CARPETA_PROYECTO = os.path.dirname(sys.executable)
else:
    # Si está corriendo desde VS Code, terminal o consola como un script .py normal
    CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))

RUTA_CONFIG_RED = os.path.join(CARPETA_PROYECTO, "config_red.json")
RUTA_LOG = os.path.join(CARPETA_PROYECTO, "log_conexion.txt")
RUTA_ENV = os.path.join(CARPETA_PROYECTO, ".env")

# Cargamos las variables del archivo .env buscando fijamente la ubicación física del entorno externo
if os.path.exists(RUTA_ENV):
    load_dotenv(RUTA_ENV)
else:
    load_dotenv() # Intento de carga por defecto si no se localiza explícito

# Forzamos que si el .env dice que es la secretaria, use el rol secundario
ROL_PC = os.getenv("ROL_PC", "principal")  # "principal" o "secundaria"

user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST', 'localhost') 
port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME')

def escribir_en_log(mensaje):
    """ Escribe alertas en un archivo de texto físico al lado del ejecutable y en consola """
    hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    texto_final = f"[{hora}] {mensaje}"
    
    # Forzamos print en consola para depuración rápida por terminal
    print(texto_final)
    
    try:
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(texto_final + "\n")
    except Exception as e:
        print(f"🚨 ALERTA DE SISTEMA: No se pudo escribir en log_conexion.txt -> {e}")

# Variable interna para saber si cargamos una IP del archivo o no
ip_json_detectada = False

if os.path.exists(RUTA_CONFIG_RED):
    try:
        with open(RUTA_CONFIG_RED, "r", encoding="utf-8") as f:
            datos_red = json.load(f)
            ip_servidor = datos_red.get("ip_servidor")
            if ip_servidor:
                host = ip_servidor
                ip_json_detectada = True
                escribir_en_log(f"🔌 JSON detectado en directorio raíz persistente. Host cambiado a la IP: {host}")
    except Exception as e:
        escribir_en_log(f"⚠️ Error al leer config_red.json: {str(e)}")

# Variables globales que Qt y las pantallas importarán directamente
engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
tipo_conexion_actual = "desconectado"

def inicializar_conexion_medica():
    """
    Determina el entorno y establece la conexión física.
    Si detecta modo terminal (secretaria sin enlazar) o si el servidor PostgreSQL no responde,
    activar un entorno SQLite virtual en la memoria RAM para evitar caídas del sistema.
    """
    global engine, SessionLocal, tipo_conexion_actual
    
    # 1. Modo terminal pura de fábrica (Secretaria que jamás ha enlazado a nadie y sigue en localhost)
    if ROL_PC == "secundaria" and not ip_json_detectada and (host == "localhost" or host == "127.0.0.1"):
        escribir_en_log("🌐 Modo Terminal Inicial Activo (Sin enlazar). Levantando entorno seguro en RAM...")
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SessionLocal.configure(bind=engine)
        tipo_conexion_actual = "sqlite"
        return tipo_conexion_actual

    # 2. Intentamos conectar al motor PostgreSQL remoto o local
    DB_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    
    try:
        escribir_en_log(f"📡 Intentando establecer apretón de manos con PostgreSQL en: {host}...")
        
        # connect_timeout=3 evita bloqueos si la red está caída o el Firewall tranca
        engine = create_engine(
            DB_URL, 
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3}
        )
        
        # PROBAMOS LA CONEXIÓN INMEDIATAMENTE
        conexion_prueba = engine.connect()
        conexion_prueba.close()
        
        SessionLocal.configure(bind=engine)
        escribir_en_log(f"✅ ¡CONEXIÓN EXITOSA EN RED LOCAL! Enlazado al PostgreSQL en [{host}].")
        tipo_conexion_actual = "postgres"
        return tipo_conexion_actual
        
    except Exception as e:
        # 3. ESCUDO DE EMERGENCY: Si la IP falló o el Firewall rebotó, se activa la RAM
        error_detallado = traceback.format_exc()
        escribir_en_log(
            f"❌ ERROR CRÍTICO DE ENLACE A POSTGRESQL:\n"
            f"   - IP intentada: {host}\n"
            f"   - Usuario: {user}\n"
            f"   - Base de datos: {db_name}\n"
            f"   - Traza del error:\n{error_detallado}\n"
            f"{'-'*60}"
        )
        
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SessionLocal.configure(bind=engine)
        tipo_conexion_actual = "sqlite_emergencia"
        return tipo_conexion_actual


# Ejecutamos la inicialización del motor en caliente al importar el archivo
inicializar_conexion_medica()

def inicializar_base_de_datos():
    try:
        Base.metadata.create_all(bind=engine)
        escribir_en_log(f"✅ Estructura de tablas mapeada correctamente en el motor [{tipo_conexion_actual}].")
    except Exception as e:
        escribir_en_log(f"❌ Error crítico al estructurar tablas: {str(e)}")

def conectar_en_caliente(nueva_ip):
    """
    Destruye la conexión temporal de RAM y fuerza un enlace a PostgreSQL en tiempo real
    sin necesidad de cerrar y volver a abrir la aplicación.
    """
    global engine, SessionLocal, tipo_conexion_actual, host
    
    host = nueva_ip
    DB_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    
    try:
        escribir_en_log(f"🔥 [HOT-SWAP] Intentando conexión en caliente a: {host}")
        
        nuevo_engine = create_engine(
            DB_URL, 
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3}
        )
        
        # Probamos que el puente exista de verdad
        conexion = nuevo_engine.connect()
        conexion.close()
        
        # Si no explotó, hacemos el cambiazo oficial de los motores
        engine = nuevo_engine
        SessionLocal.configure(bind=engine)
        tipo_conexion_actual = "postgres"
        
        escribir_en_log("✅ [HOT-SWAP] ¡Éxito! Motor cambiado a PostgreSQL en vivo.")
        return True, "Conexión en caliente exitosa"
        
    except Exception as e:
        error_msg = str(e)
        escribir_en_log(f"❌ [HOT-SWAP] Falló la conexión en caliente: {error_msg}")
        return False, error_msg

# =====================================================================
# MODIFICACIÓN AGREGADA: VERIFICACIÓN PARA CONTROL DE FLUJO GLOBAL
# =====================================================================
def es_conexion_valida():
    """ Devuelve True si estamos enlazados de verdad al motor PostgreSQL físico de la red """
    global tipo_conexion_actual
    return tipo_conexion_actual == "postgres"

if __name__ == "__main__":
    inicializar_conexion_medica()
    inicializar_base_de_datos()
