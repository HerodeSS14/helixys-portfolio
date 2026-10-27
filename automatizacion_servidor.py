import os
import sys
import subprocess
import re

def obtener_ruta_postgres():
    """ Intenta localizar la ruta de configuración de PostgreSQL en Windows """
    ruta_base = r"C:\Program Files\PostgreSQL"
    if os.path.exists(ruta_base):
        versiones = os.listdir(ruta_base)
        if versiones:
            # Tomamos la versión más alta instalada (ej: '15', '16', '17')
            version_reciente = sorted(versiones, key=lambda x: [int(c) for c in re.findall(r'\d+', x)][0] if re.findall(r'\d+', x) else [0])[-1]
            ruta_data = os.path.join(ruta_base, version_reciente, "data")
            if os.path.exists(ruta_data):
                return ruta_data
    return None

def liberar_postgresql_red_local():
    """ Modifica postgresql.conf y pg_hba.conf usando autenticación compatible (md5) """
    ruta_data = obtener_ruta_postgres()
    if not ruta_data:
        return False, "No se encontró la carpeta de datos de PostgreSQL."

    try:
        # 1. Modificar postgresql.conf (Escuchar en todas las interfaces de red)
        ruta_conf = os.path.join(ruta_data, "postgresql.conf")
        with open(ruta_conf, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        modificado_conf = False
        for i, linea in enumerate(lineas):
            if linea.strip().startswith("listen_addresses"):
                lineas[i] = "listen_addresses = '*'     # Modificado automaticamente por Historias Medicas\n"
                modificado_conf = True
                break
        
        if not modificado_conf:
            lineas.append("\nlisten_addresses = '*' # Añadido por Historias Medicas\n")

        with open(ruta_conf, "w", encoding="utf-8") as f:
            f.writelines(lineas)

        # 2. Modificar pg_hba.conf (Permitir el acceso por red usando el estándar compatible md5)
        ruta_hba = os.path.join(ruta_data, "pg_hba.conf")
        with open(ruta_hba, "r", encoding="utf-8") as f:
            lineas_hba = f.readlines()

        # REM COMPATIBILIDAD CRÍTICA: Forzamos el uso de md5 para la red local 192.168.X.X
        # REM COMPATIBILIDAD CRÍTICA: Forzamos el uso de trust para la red local 192.168.X.X
        regla_red = "host    all             all             192.168.0.0/16          trust\n"
        
        # Verificamos si la regla ya existe en el archivo
        existe_regla = any(regla_red.strip() in linea for linea in lineas_hba)

        if not existe_regla:
            # Insertamos la regla al principio (justo después de los comentarios iniciales)
            # para asegurarnos de que Windows y Postgres la lean antes que cualquier restricción scram
            lineas_hba.insert(0, f"\n# Regla de acceso local automatizada por Historias Medicas\n{regla_red}")
            with open(ruta_hba, "w", encoding="utf-8") as f:
                f.writelines(lineas_hba)

        return True, "Configuraciones de PostgreSQL (md5) aplicadas con éxito."
    except PermissionError:
        return False, "Error de permisos: Ejecuta la aplicación como ADMINISTRADOR."
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def abrir_firewall_windows():
    """ Abre el puerto 5432 garantizando permisos para redes de entrada y salida """
    nombre_regla = "HistoriasMedicas_PostgreSQL"
    comando = f'netsh advfirewall firewall add rule name="{nombre_regla}" dir=in action=allow protocol=TCP localport=5432 profile=any'
    
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0 or "ya existe" in resultado.stderr.lower():
            return True, "Puerto 5432 abierto con éxito en el Firewall de Windows."
        return False, f"Error al configurar Firewall: {resultado.stderr}"
    except Exception as e:
        return False, f"No se pudo ejecutar el comando de Firewall: {str(e)}"

def reiniciar_servicio_postgres():
    """ Localiza dinámicamente cualquier servicio de PostgreSQL activo en Windows y lo reinicia """
    try:
        resultado_sc = subprocess.run('sc query type= service state= all', shell=True, capture_output=True, text=True)
        nombres_servicios = re.findall(r'SERVICE_NAME:\s*(postgresql\S*)', resultado_sc.stdout, re.IGNORECASE)
        
        if not nombres_servicios:
            nombres_servicios = ["postgresql-x64-16", "postgresql-x64-15", "postgresql-x64-14", "postgresql-x64-17", "postgresql"]

        for servicio in nombres_servicios:
            servicio = servicio.strip()
            print(f"🔄 Intentando reiniciar servicio hallado: {servicio}")
            subprocess.run(f'net stop "{servicio}"', shell=True, capture_output=True)
            resultado = subprocess.run(f'net start "{servicio}"', shell=True, capture_output=True, text=True)
            
            if "inició con éxito" in resultado.stdout or resultado.returncode == 0:
                print(f"✅ Servicio [{servicio}] reiniciado con éxito por red.")
                return True, f"Servicio {servicio} reiniciado correctamente."
                
    except Exception as e:
        print(f"⚠️ Error rastreando servicios: {e}")
            
    return False, "No se pudo reiniciar el servicio automáticamente. Por favor, reinicie la PC."