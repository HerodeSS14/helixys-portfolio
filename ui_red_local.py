import os
import sys
import json
from PySide6.QtWidgets import (QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QMessageBox, QProgressBar, QListWidget)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from estilos import tema

# Importamos las herramientas automáticas de red
import automatizacion_servidor
# Importamos el nuevo servicio_mdns refactorizado
from servicio_mdns import EmisorServidorMDNS, RastreadorClienteMDNS, actualizar_config_red

class HiloConfigurarServidor(QThread):
    progreso_senal = Signal(int, str)
    resultado_final = Signal(bool, str)

    def run(self):
        self.progreso_senal.emit(20, "Modificando parámetros de red en PostgreSQL...")
        exito_pg, msg_pg = automatizacion_servidor.liberar_postgresql_red_local()
        if not exito_pg:
            self.resultado_final.emit(False, msg_pg)
            return

        self.progreso_senal.emit(50, "Liberando puerto 5432 en el Firewall de Windows...")
        exito_fw, msg_fw = automatizacion_servidor.abrir_firewall_windows()
        if not exito_fw:
            self.resultado_final.emit(False, msg_fw)
            return

        self.progreso_senal.emit(80, "Reiniciando el motor de base de datos...")
        automatizacion_servidor.reiniciar_servicio_postgres()

        self.resultado_final.emit(True, "Servidor configurado con éxito.")


class HiloRastrearDispositivos(QThread):
    """ Hilo asíncrono para escanear la red por 4 segundos sin congelar la interfaz de PySide6 """
    dispositivos_encontrados = Signal(list)

    def run(self):
        rastreador = RastreadorClienteMDNS()
        # Escanea el canal '_meddb' durante 4 segundos reales
        lista_equipos = rastreador.escanear_red_local(timeout=4)
        self.dispositivos_encontrados.emit(lista_equipos)


class TabConectividadRed(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Layout principal centrado
        layout_global = QVBoxLayout(self)
        layout_global.setAlignment(Qt.AlignCenter) 
        
        # CONTENEDOR LIMITADO (Para mantener una proporción elegante)
        contenedor_fijo = QWidget()
        contenedor_fijo.setMaximumWidth(950) 
        contenedor_fijo.setMinimumHeight(550)
        lay_fijo = QVBoxLayout(contenedor_fijo)
        lay_fijo.setSpacing(20)

        # TÍTULO PRINCIPAL
        self.lbl_titulo = QLabel("<h2>🌐 Centro de Conexión y Sincronización Local</h2>")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        lay_fijo.addWidget(self.lbl_titulo)

        # FILA DE TARJETAS HORIZONTALES
        layout_tarjetas = QHBoxLayout()
        layout_tarjetas.setSpacing(25)

        # --- TARJETA 1: SERVIDOR (Doctor) ---
        self.card_servidor = QFrame()
        lay_servidor = QVBoxLayout(self.card_servidor)
        lay_servidor.setContentsMargins(20, 20, 20, 20)
        lay_servidor.setSpacing(15)
        lay_servidor.setAlignment(Qt.AlignTop)

        self.lbl_tit_serv = QLabel("<h3>🖥️ Modo Servidor (PC Doctor)</h3>")
        self.lbl_desc_serv = QLabel("Habilita el acceso seguro para que la computadora de la secretaria guarde e interactúe con los datos de la clínica.")
        self.lbl_desc_serv.setWordWrap(True)
        self.lbl_status_serv = QLabel("<b>Estado:</b> 🔴 Solo acceso local")
        
        self.btn_activar_servidor = QPushButton("🚀 COMPARTIR BASE DE DATOS")
        self.btn_activar_servidor.setMinimumHeight(42)
        self.btn_activar_servidor.setCursor(Qt.PointingHandCursor)
        self.btn_activar_servidor.clicked.connect(self.iniciar_automatizacion_servidor)

        lay_servidor.addWidget(self.lbl_tit_serv)
        lay_servidor.addWidget(self.lbl_desc_serv)
        lay_servidor.addWidget(self.lbl_status_serv)
        lay_servidor.addStretch()
        lay_servidor.addWidget(self.btn_activar_servidor)

        # --- TARJETA 2: CLIENTE INTERACTIVO (Secretaria) ---
        self.card_cliente = QFrame()
        lay_cliente = QVBoxLayout(self.card_cliente)
        lay_cliente.setContentsMargins(20, 20, 20, 20)
        lay_cliente.setSpacing(12)
        lay_cliente.setAlignment(Qt.AlignTop)

        self.lbl_tit_cli = QLabel("<h3>🤝 Modo Asistente </h3>")
        self.lbl_desc_cli = QLabel("Escanea e identifica los servidores activos en la clínica. Selecciona la computadora del doctor para enlazarte.")
        self.lbl_desc_cli.setWordWrap(True)
        self.lbl_status_cli = QLabel("<b>Estado:</b> 🔴 Desconectado")
        
        # 📋 LISTA VISUAL INTERACTIVA DE DISPOSITIVOS DETECTADOS
        self.lista_dispositivos = QListWidget()
        self.lista_dispositivos.setMinimumHeight(120)
        # ✅ REEMPLAZO SEGURO Y COMPATIBLE:
        item_ayuda = QListWidgetItem("🔍 Presione 'BUSCAR' para escanear la red local...")
        # Le ponemos un color grisáceo sutil para que parezca un placeholder real
        item_ayuda.setForeground(QColor("#747f8d" if tema.modo_actual == "oscuro" else "#7f8c8d"))
        # Deshabilitamos el ítem para que la secretaria no pueda darle click ni seleccionarlo por error
        item_ayuda.setFlags(item_ayuda.flags() & ~Qt.ItemIsEnabled)
        self.lista_dispositivos.addItem(item_ayuda)
        self.lista_dispositivos.itemClicked.connect(self.seleccionar_servidor_de_lista)
        
        self.btn_buscar_servidor = QPushButton("🔍 BUSCAR COMPUTADORAS EN RED")
        self.btn_buscar_servidor.setMinimumHeight(42)
        self.btn_buscar_servidor.setCursor(Qt.PointingHandCursor)
        self.btn_buscar_servidor.clicked.connect(self.iniciar_escaneo_red)

        lay_cliente.addWidget(self.lbl_tit_cli)
        lay_cliente.addWidget(self.lbl_desc_cli)
        lay_cliente.addWidget(self.lbl_status_cli)
        lay_cliente.addWidget(self.lista_dispositivos) # Inyectamos la lista en la tarjeta
        lay_cliente.addWidget(self.btn_buscar_servidor)

        layout_tarjetas.addWidget(self.card_servidor)
        layout_tarjetas.addWidget(self.card_cliente)
        lay_fijo.addLayout(layout_tarjetas)

        # STATUS Y BARRA DE PROGRESO INFERIOR
        self.lbl_progreso_accion = QLabel("")
        self.lbl_progreso_accion.setAlignment(Qt.AlignCenter)
        self.lbl_progreso_accion.setVisible(False)
        lay_fijo.addWidget(self.lbl_progreso_accion)

        self.progreso = QProgressBar()
        self.progreso.setVisible(False)
        self.progreso.setTextVisible(True)
        self.progreso.setFixedHeight(15)
        lay_fijo.addWidget(self.progreso)

        layout_global.addWidget(contenedor_fijo)

        self.aplicar_diseno_dinamico()
        
        tema_changed = getattr(tema, 'tema_cambiado', None)
        if tema_changed:
            tema_changed.connect(self.aplicar_diseno_dinamico)

    def lanzar_popup_estilizado(self, tipo, titulo, mensaje):
        box = QMessageBox(self)
        if tipo == "info": box.setIcon(QMessageBox.Information)
        elif tipo == "error": box.setIcon(QMessageBox.Critical)
        elif tipo == "aviso": box.setIcon(QMessageBox.Warning)
            
        box.setWindowTitle(titulo)
        box.setText(mensaje)
        
        bg_popup = "#2f3136" if tema.modo_actual == "oscuro" else "#FFFFFF"
        txt_popup = "#FFFFFF" if tema.modo_actual == "oscuro" else "#1C1C1C"
        
        box.setStyleSheet(f"""
            QMessageBox {{ background-color: {bg_popup}; }}
            QLabel {{ color: {txt_popup}; background: transparent; font-size: 13px; }}
            QPushButton {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; padding: 6px 18px; border-radius: 4px; border: none; min-width: 65px; }}
            QPushButton:hover {{ background-color: #93F6E3; }}
        """)
        box.exec()

    # =========================================================
    # ACCIONES DEL DOCTOR (SERVIDOR)
    # =========================================================
    def iniciar_automatizacion_servidor(self):
        self.btn_activar_servidor.setEnabled(False)
        self.progreso.setVisible(True)
        self.lbl_progreso_accion.setVisible(True)
        self.progreso.setValue(5)
        self.lbl_progreso_accion.setText("Analizando puertos del sistema...")

        self.hilo_servidor = HiloConfigurarServidor()
        self.hilo_servidor.progreso_senal.connect(self.actualizar_progreso_ui)
        self.hilo_servidor.resultado_final.connect(self.finalizar_automatizacion_servidor)
        self.hilo_servidor.start()

    def actualizar_progreso_ui(self, valor, mensaje):
        self.progreso.setValue(valor)
        self.lbl_progreso_accion.setText(mensaje)

    def finalizar_automatizacion_servidor(self, exito, mensaje):
        self.btn_activar_servidor.setEnabled(True)
        self.progreso.setVisible(False)
        self.lbl_progreso_accion.setVisible(False)

        if exito:
            self.emisor_mdns = EmisorServidorMDNS()
            exito_mdns, ip_real = self.emisor_mdns.registrar_servidor()
            
            if exito_mdns:
                self.lbl_status_serv.setText(f"<b>Estado:</b> 🟢 Compartido en IP {ip_real}")
                self.lbl_status_serv.setStyleSheet("color: #34D399; font-weight: bold; background: transparent;")
                self.lanzar_popup_estilizado("info", "Servidor Activo", "Base de datos abierta y visible por mDNS. La secretaria ya puede buscarte en su lista.")
            else:
                self.lanzar_popup_estilizado("aviso", "Aviso de mDNS", f"PostgreSQL abierto pero mDNS falló: {ip_real}. Ingresa la IP manualmente.")
        else:
            self.lanzar_popup_estilizado("error", "Error de Permisos", f"No se pudo configurar: {mensaje}\n\nEjecuta la app como ADMINISTRADOR.")

    # =========================================================
    # ACCIONES DE LA SECRETARIA (CLIENTE INTERACTIVO)
    # =========================================================
    def iniciar_escaneo_red(self):
        self.lista_dispositivos.clear()
        self.btn_buscar_servidor.setEnabled(False)
        self.progreso.setVisible(True)
        self.lbl_progreso_accion.setVisible(True)
        self.progreso.setValue(50)
        self.lbl_status_cli.setText("<b>Estado:</b> 🔄 Escaneando red...")
        self.lbl_progreso_accion.setText("Rastreando computadoras con bases de datos activas...")

        self.hilo_rastreo = HiloRastrearDispositivos()
        self.hilo_rastreo.dispositivos_encontrados.connect(self.finalizar_escaneo_red)
        self.hilo_rastreo.start()

    def finalizar_escaneo_red(self, lista_equipos):
        self.progreso.setVisible(False)
        self.lbl_progreso_accion.setVisible(False)
        self.btn_buscar_servidor.setEnabled(True)
        
        if not lista_equipos:
            self.lbl_status_cli.setText("<b>Estado:</b> 🔴 No se hallaron servidores")
            self.lbl_status_cli.setStyleSheet("color: #F87171; font-weight: bold; background: transparent;")
            self.lanzar_popup_estilizado("aviso", "Escaneo Terminado", "No se detectó ninguna PC transmitiendo. Verifica que el doctor haya presionado 'COMPARTIR BASE DE DATOS'.")
            return

        self.lbl_status_cli.setText(f"<b>Estado:</b> 🔍 {len(lista_equipos)} equipo(s) detectado(s)")
        self.lbl_status_cli.setStyleSheet("color: #F59E0B; font-weight: bold; background: transparent;")
        
        # Rellenamos la lista de la interfaz con los nombres reales de los equipos
        for eq in lista_equipos:
            texto_fila = f"💻 {eq['nombre']} ---- (IP: {eq['ip']})"
            self.lista_dispositivos.addItem(texto_fila)

    def seleccionar_servidor_de_lista(self, item):
        """ Se ejecuta al darle un clic físico a una PC de la lista """
        texto_renglon = item.text()
        ip_elegida = texto_renglon.split("(IP: ")[1].replace(")", "").strip()
        nombre_equipo = texto_renglon.split(" ----")[0].replace("💻 ", "").strip()
        
        box = QMessageBox(QMessageBox.Question, "Confirmar Enlace", 
                            f"¿Desea enlazar este terminal con la base de datos de:\n\n👉 {nombre_equipo} [{ip_elegida}]?",
                            QMessageBox.Yes | QMessageBox.No, self)
        
        bg_popup = "#2f3136" if tema.modo_actual == "oscuro" else "#FFFFFF"
        txt_popup = "#FFFFFF" if tema.modo_actual == "oscuro" else "#1C1C1C"
        box.setStyleSheet(f"QMessageBox {{ background-color: {bg_popup}; }} QLabel {{ color: {txt_popup}; }}")
        
        if box.exec() == QMessageBox.Yes:
            # 1. Guardamos la IP para el futuro
            exito_json = actualizar_config_red(ip_elegida)
            
            if exito_json:
                self.lbl_status_cli.setText(f"<b>Estado:</b> 🔄 Conectando en caliente...")
                self.lbl_status_cli.setStyleSheet("color: #F59E0B; font-weight: bold; background: transparent;")
                
                # 2. Hacemos el Hot-Swap sin reiniciar la app
                import database
                exito_db, mensaje = database.conectar_en_caliente(ip_elegida)
                
                if exito_db:
                    self.lbl_status_cli.setText(f"<b>Estado:</b> 🟢 Enlazado a {nombre_equipo}")
                    self.lbl_status_cli.setStyleSheet("color: #34D399; font-weight: bold; background: transparent;")
                    self.lanzar_popup_estilizado("info", "¡Conectado!", f"¡Sincronización en vivo completada con éxito!\n\nEl sistema está enlazado a {nombre_equipo}. Ya puedes ir a la pestaña de pacientes y ver la información.")
                else:
                    self.lbl_status_cli.setText(f"<b>Estado:</b> 🔴 Falló el enlace")
                    self.lbl_status_cli.setStyleSheet("color: #EF4444; font-weight: bold; background: transparent;")
                    self.lanzar_popup_estilizado("error", "Bloqueo de Red", f"No se pudo acceder a la computadora del doctor.\n\nRevisa que el Firewall del doctor esté apagado o tenga la regla 'trust'.\nDetalle técnico:\n{mensaje}")
            else:
                self.lanzar_popup_estilizado("error", "Error", "No se pudo escribir el archivo de configuración de red.")
    # =========================================================
    # CONTROL DE ESTILOS Y TEMA
    # =========================================================
    def aplicar_diseno_dinamico(self):
        is_dark = (tema.modo_actual == "oscuro")
        color_txt = "#FFFFFF" if is_dark else tema.TEXTO_MAIN
        bg_card = "#2f3136" if is_dark else "#fdfdfd"
        bg_lista = "#202225" if is_dark else "#f0f0f0"
        
        self.lbl_titulo.setStyleSheet(getattr(tema, 'ESTILO_LABEL_TITULO', f"color: {color_txt};"))
        
        for card in [self.card_servidor, self.card_cliente]:
            card.setStyleSheet(f"QFrame {{ background-color: {bg_card}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 12px; }}")
            
        for lbl in [self.lbl_tit_serv, self.lbl_desc_serv, self.lbl_status_serv, 
                    self.lbl_tit_cli, self.lbl_desc_cli, self.lbl_status_cli, self.lbl_progreso_accion]:
            lbl.setStyleSheet(f"color: {color_txt}; background: transparent; border: none;")
            
        # Estilo premium para nuestra lista de dispositivos
        self.lista_dispositivos.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_lista};
                color: {color_txt};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                padding: 5px;
                font-weight: bold;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {tema.BORDE_SUAVE};
            }}
            QListWidget::item:hover {{
                background-color: {tema.MENTA_MEDICA};
                color: #1C1C1C;
                border-radius: 4px;
            }}
        """)
            
        self.btn_activar_servidor.setStyleSheet(tema.ESTILO_BTN_ORDEN)
        self.btn_buscar_servidor.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        
        self.progreso.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid {tema.BORDE_SUAVE}; border-radius: 5px; text-align: center; color: {color_txt}; background-color: {bg_card}; }}
            QProgressBar::chunk {{ background-color: #93F6E3; width: 20px; }}
        """)