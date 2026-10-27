import os
import sys
import json
import socket
import time
from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener

# 🛡️ CORREGIDO: '_meddb' tiene menos de 15 bytes, evitando el crash internacional de mDNS
NOMBRE_SERVICIO = "_meddb._tcp.local."
PROPIEDADES = {"descripcion": "Servidor de Base de Datos Clinica"}

class EmisorServidorMDNS:
    """ Hace que la PC del Doctor sea visible en la red local de forma automática """
    def __init__(self):
        self.zeroconf = None
        self.info = None

    def registrar_servidor(self):
        try:
            # Obtener la IP local real de esta máquina
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()

            # Capturamos el nombre real de la computadora del doctor en Windows
            nombre_equipo = socket.gethostname()

            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            
            # Configuramos el servicio usando el nombre real del equipo
            self.info = ServiceInfo(
                type_=NOMBRE_SERVICIO,
                name=f"{nombre_equipo}.{NOMBRE_SERVICIO}",
                addresses=[socket.inet_aton(ip_local)],
                port=5432,  # Puerto nativo de PostgreSQL
                properties=PROPIEDADES,
                server=f"{nombre_equipo}.local."
            )
            
            self.zeroconf.register_service(self.info)
            print(f"📡 [mDNS] Transmitiendo servicio clínico en la IP: {ip_local}")
            return True, ip_local
        except Exception as e:
            return False, f"Error al levantar mDNS: {str(e)}"

    def detener_servidor(self):
        if self.zeroconf and self.info:
            try:
                self.zeroconf.unregister_service(self.info)
            except:
                pass
            self.zeroconf.close()
            print("🛑 [mDNS] Transmisión de red detenida de forma limpia.")


class BuscadorListener(ServiceListener):
    """ Escuchador dinámico que va llenando la lista de servidores encontrados """
    def __init__(self, lista_acumuladora):
        self.lista_acumuladora = lista_acumuladora

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            ip_encontrada = socket.inet_ntoa(info.addresses[0])
            nombre_limpio = name.split(".")[0]
            
            servidor = {"nombre": nombre_limpio, "ip": ip_encontrada}
            
            if servidor not in self.lista_acumuladora:
                self.lista_acumuladora.append(servidor)
                print(f"🎯 [mDNS] Servidor Localizado -> {nombre_limpio} ({ip_encontrada})")


class RastreadorClienteMDNS:
    """ Maneja el escaneo y recolección de servidores en la red local """
    def __init__(self):
        self.zeroconf = None
        self.browser = None
        self.servidores_encontrados = []

    def escanear_red_local(self, timeout=4):
        """ Escanea la red durante unos segundos y devuelve la lista de dispositivos """
        self.servidores_encontrados = []  # Limpiamos búsquedas previas
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        
        listener = BuscadorListener(self.servidores_encontrados)
        print("🔍 [mDNS] Buscando servidores con PostgreSQL activo en la red...")
        self.browser = ServiceBrowser(self.zeroconf, NOMBRE_SERVICIO, listener)
        
        # Dormimos el hilo temporalmente mientras se recolectan las señales mDNS en segundo plano
        time.sleep(timeout)
        self.detener_rastreo()
        
        return self.servidores_encontrados

    def detener_rastreo(self):
        if self.browser:
            self.browser.cancel()
            self.browser = None
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None


def actualizar_config_red(ip_servidor):
    """ Modifica el archivo config_red.json asegurando una ruta absoluta al lado del .exe """
    try:
        # Detectamos si es .exe o script normal
        if getattr(sys, 'frozen', False):
            carpeta_actual = os.path.dirname(sys.executable)
        else:
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))
            
        ruta_json = os.path.join(carpeta_actual, "config_red.json")
        
        config_red = {"ip_servidor": ip_servidor}
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(config_red, f, indent=4)
            
        print(f"✅ [mDNS Config] Guardado persistente en: {ruta_json}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar config_red.json: {e}")
        return False
# Mantenemos esta función por compatibilidad de nombres con el archivo original
def actualizar_conexion_secretaria(ip_servidor):
    return actualizar_config_red(ip_servidor)