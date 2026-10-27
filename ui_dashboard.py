from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QMessageBox, QHeaderView, QTabWidget, QDialog, 
                             QCalendarWidget, QLineEdit, QListWidget, QInputDialog, QTextEdit, QMenu,
                             QCheckBox, QWidgetAction, QFrame)
from PySide6.QtCore import QTimer, Qt, Signal, QDate, QUrl, QSettings 
from PySide6.QtGui import QColor, QBrush, QAction, QDesktopServices
from datetime import date
from database import SessionLocal
from models import Paciente, AgendaDiaria, CitaMedica
import urllib.parse
from estilos import tema  # Importación del motor de diseño centralizado

# =================================================================
# 2. COLOCA ESTA CLASE PRIMERO (Para evitar el NameError)
# =================================================================
class TarjetaNotificacionWidget(QWidget):
    def __init__(self, badge_tiempo, paciente_nombre, fecha_cita, cita_id, dashboard_parent, parent=None):
        super().__init__(parent)
        self.cita_id = cita_id
        self.dashboard_parent = dashboard_parent # Guardamos la referencia para disparar el salto
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        layout_master = QVBoxLayout(self)
        layout_master.setContentsMargins(5, 5, 5, 5)
        
        # El contenedor (burbuja)
        self.burbuja = QFrame()
        bg_burbuja = "#2f3136" if tema.modo_actual == "oscuro" else "#FFFFFF"
        self.burbuja.setStyleSheet(f"background-color: {bg_burbuja}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 14px;")
        
        lay_burbuja = QVBoxLayout(self.burbuja)
        lay_burbuja.setContentsMargins(12, 10, 12, 12)
        lay_burbuja.setSpacing(6)
        
        lay_cabecera = QHBoxLayout()
        lbl_icono = QLabel("💬") 
        lbl_icono.setStyleSheet("border: none; background: transparent; font-size: 14px;")
        
        lbl_app = QLabel("CITAS")
        color_app = "#FFFFFF" if tema.modo_actual == "oscuro" else "#1C1C1C"
        lbl_app.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {color_app}; letter-spacing: 1px; border: none; background: transparent;")
        
        lbl_tiempo = QLabel(badge_tiempo)
        color_tiempo = "#b9bbbe" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        lbl_tiempo.setStyleSheet(f"font-size: 11px; color: {color_tiempo}; border: none; background: transparent;")
        
        lay_cabecera.addWidget(lbl_icono)
        lay_cabecera.addWidget(lbl_app)
        lay_cabecera.addStretch()
        lay_cabecera.addWidget(lbl_tiempo)
        
        lbl_cuerpo = QLabel(f"<b>{paciente_nombre}</b><br><span style='font-size:11px;'>Requiere contacto para confirmar asistencia ({fecha_cita})</span>")
        lbl_cuerpo.setWordWrap(True)
        color_cuerpo = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        lbl_cuerpo.setStyleSheet(f"font-size: 13px; color: {color_cuerpo}; border: none; background: transparent; padding-left: 2px;")
        
        lay_burbuja.addLayout(lay_cabecera)
        lay_burbuja.addWidget(lbl_cuerpo)
        layout_master.addWidget(self.burbuja)

    # 👑 EVENTO MOUSE: Al hacer click físico en el rectángulo, cierra el menú y salta a la fila
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Cerramos el menú flotante de la campana
            if self.dashboard_parent.menu_notificaciones.isVisible():
                self.dashboard_parent.menu_notificaciones.close()
            # Ejecutamos el redireccionamiento seguro
            self.dashboard_parent.ir_a_cita_desde_notificacion(self.cita_id)
            super().mousePressEvent(event)

class DialogoPlantillaWhatsApp(QDialog):
    def __init__(self, plantilla_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modificar Mensaje de WhatsApp")
        self.setMinimumSize(550, 400)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)

        # Determinar colores de los textos explicativos internos
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        bg_tarjeta = "#36393e" if tema.modo_actual == "oscuro" else "#ecf0f1"

        lbl_info = QLabel(
            f"<h3 style='color: {color_txt};'>✏️ Edite el mensaje base para las notificaciones</h3>"
            f"<p style='font-size: 14px; color: {color_txt};'>Puede usar las siguientes etiquetas. El sistema las cambiará automáticamente por los datos reales del paciente al momento de enviar el mensaje:</p>"
            f"<ul style='font-size: 14px; background-color: {bg_tarjeta}; padding: 10px; border-radius: 5px; color: {color_txt};'>"
            "<li><b>{paciente}</b> : Se reemplaza por el nombre completo.</li>"
            "<li><b>{fecha}</b> : Se reemplaza por el día de la cita.</li>"
            "<li><b>{motivo}</b> : Se reemplaza por el motivo de la consulta.</li>"
            "</ul>"
        )
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        self.texto_edit = QTextEdit()
        self.texto_edit.setPlainText(plantilla_actual)
        self.texto_edit.setStyleSheet(f"""
            QTextEdit {{
                font-size: 15px; 
                padding: 15px; 
                border: 1px solid {tema.BORDE_SUAVE}; 
                border-radius: 8px;
                background-color: {tema.BG_INPUT};
                color: {tema.TEXTO_MAIN};
            }}
            QTextEdit:focus {{ border: 2px solid {tema.MENTA_MEDICA}; }}
        """)
        layout.addWidget(self.texto_edit)

        lay_btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        btn_cancelar.setFixedHeight(35)
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_guardar = QPushButton("💾 Guardar Plantilla")
        self.btn_guardar.setFixedHeight(35)
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar.clicked.connect(self.accept)
        
        lay_btns.addStretch()
        lay_btns.addWidget(btn_cancelar)
        lay_btns.addWidget(self.btn_guardar)
        layout.addLayout(lay_btns)

    def get_plantilla(self):
        return self.texto_edit.toPlainText().strip()

# =================================================================
# DIÁLOGO PARA AGENDAR NUEVA CITA
# =================================================================
class DialogoAgendar(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agendar Nueva Cita")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)

        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN

        lbl_1 = QLabel("<b>1. Seleccione el Paciente:</b>")
        lbl_1.setStyleSheet(f"color: {color_txt}; background: transparent;")
        layout.addWidget(lbl_1)
        
        self.in_buscador = QLineEdit()
        self.in_buscador.setPlaceholderText("Buscar paciente por nombre o cédula...")
        self.in_buscador.textChanged.connect(self.filtrar_pacientes)
        self.in_buscador.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {tema.TEXTO_MAIN}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 6px; font-size: 14px;")
        layout.addWidget(self.in_buscador)

        self.lista_pacientes = QListWidget()
        self.lista_pacientes.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {tema.TEXTO_MAIN}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 5px;")
        layout.addWidget(self.lista_pacientes)
        self.cargar_pacientes()

        lbl_2 = QLabel("<b>2. Motivo de la Cita (Opcional):</b>")
        lbl_2.setStyleSheet(f"color: {color_txt}; background: transparent;")
        layout.addWidget(lbl_2)
        
        self.in_motivo = QLineEdit()
        self.in_motivo.setPlaceholderText("Ej. Chequeo de rutina, Lectura de exámenes...")
        self.in_motivo.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {tema.TEXTO_MAIN}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 6px; font-size: 14px;")
        layout.addWidget(self.in_motivo)

        lbl_3 = QLabel("<b>3. Seleccione la Fecha:</b>")
        lbl_3.setStyleSheet(f"color: {color_txt}; background: transparent;")
        layout.addWidget(lbl_3)
        
        self.calendario = QCalendarWidget()
        self.calendario.setGridVisible(True)
        self.calendario.setMinimumDate(QDate.currentDate())
        
        self.calendario.setStyleSheet(f"""
            QCalendarWidget QWidget {{
                background-color: #93F6E3; 
                color: #1C1C1C;
            }}
            QCalendarWidget QNavigationBar {{
                background-color: #93F6E3; 
                color: #1C1C1C;
                font-weight: bold;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #ffffff;
                color: #1C1C1C;
                selection-background-color: #93F6E3;
                selection-color: #1C1C1C;
            }}
        """)
        layout.addWidget(self.calendario)

        lay_btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("✅ Agendar Cita")
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar.clicked.connect(self.accept)
        
        lay_btns.addWidget(btn_cancelar)
        lay_btns.addWidget(self.btn_guardar)
        layout.addLayout(lay_btns)

    def cargar_pacientes(self):
        try:
            db = SessionLocal()
            pacientes = db.query(Paciente).order_by(Paciente.nombre_completo).all()
            for p in pacientes:
                item_text = f"{p.nombre_completo} - {p.cedula} (ID:{p.id})"
                self.lista_pacientes.addItem(item_text)
            db.close()
        except Exception as e:
            print(f"🌐 [DASHBOARD] Diálogo agendar: Sin acceso a base de datos de pacientes ({e})")
            
    def filtrar_pacientes(self, texto):
        for i in range(self.lista_pacientes.count()):
            item = self.lista_pacientes.item(i)
            item.setHidden(texto.lower() not in item.text().lower())

    def get_datos(self):
        item_seleccionado = self.lista_pacientes.currentItem()
        if not item_seleccionado: return None
        texto = item_seleccionado.text()
        paciente_id = int(texto.split("(ID:")[1].replace(")", ""))
        fecha = self.calendario.selectedDate().toPython()
        motivo = self.in_motivo.text().strip()
        return {"paciente_id": paciente_id, "fecha": fecha, "motivo": motivo}

# =================================================================
# DIÁLOGO PARA REAGENDAR (CAMBIAR FECHA)
# =================================================================
class DialogoReagendar(QDialog):
    def __init__(self, fecha_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reagendar Cita")
        self.setFixedSize(400, 400)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)

        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN

        lbl = QLabel("<b>Seleccione la nueva fecha para la cita:</b>")
        lbl.setStyleSheet(f"color: {color_txt}; background: transparent;")
        layout.addWidget(lbl)
        
        self.calendario = QCalendarWidget()
        self.calendario.setGridVisible(True)
        self.calendario.setMinimumDate(QDate.currentDate())
        
        self.calendario.setStyleSheet(f"""
            QCalendarWidget QWidget {{
                background-color: #93F6E3; 
                color: #1C1C1C;
            }}
            QCalendarWidget QNavigationBar {{
                background-color: #93F6E3; 
                color: #1C1C1C;
                font-weight: bold;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #ffffff;
                color: #1C1C1C;
                selection-background-color: #93F6E3;
                selection-color: #1C1C1C;
            }}
        """)
        
        if fecha_actual:
            qdate = QDate(fecha_actual.year, fecha_actual.month, fecha_actual.day)
            self.calendario.setSelectedDate(qdate)
            
        layout.addWidget(self.calendario)

        lay_btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("💾 Confirmar Cambio")
        btn_guardar.setStyleSheet(tema.ESTILO_BTN_INFORME)
        btn_guardar.clicked.connect(self.accept)
        
        lay_btns.addWidget(btn_cancelar)
        lay_btns.addWidget(btn_guardar)
        layout.addLayout(lay_btns)

    def get_nueva_fecha(self):
        return self.calendario.selectedDate().toPython()

# =================================================================
# PANTALLA PRINCIPAL DEL DASHBOARD
# =================================================================
class Dashboard(QWidget):
    iniciar_consulta_signal = Signal(int)
    solicitar_informe_signal = Signal(int)
    solicitar_factura_signal = Signal(int) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)
        
        # --- CABECERA CON CAMPANA DE NOTIFICACIONES ---
        lay_header = QHBoxLayout()
        self.lbl_titulo_dash = QLabel("<h2>Panel de Control Clínico</h2>")
        self.lbl_titulo_dash.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        lay_header.addWidget(self.lbl_titulo_dash)
        lay_header.addStretch()
        
        self.btn_notificaciones = QPushButton("🔔 (0)")
        self.btn_notificaciones.setStyleSheet("font-size: 18px; font-weight: bold; border: none; padding: 5px; background: transparent;")
        
        self.menu_notificaciones = QMenu(self)
        self.btn_notificaciones.setMenu(self.menu_notificaciones)
        
        lay_header.addWidget(self.btn_notificaciones)
        layout.addLayout(lay_header)

        self.tabs = QTabWidget()
        
        # --- PESTAÑA 1: SALA DE ESPERA ---
        self.tab_espera = QWidget()
        self.setup_tab_espera()
        
        # --- PESTAÑA 2: AGENDA PROGRAMADA ---
        self.tab_citas = QWidget()
        self.setup_tab_citas()

        self.tabs.addTab(self.tab_espera, "🏥 Pacientes en Espera (Hoy)")
        self.tabs.addTab(self.tab_citas, "📅 Citas Programadas (Agenda)")
        
        layout.addWidget(self.tabs)
        
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()
        self.actualizar_notificaciones()

        # ⏱️ CONFIGURACIÓN DEL LATIDO INTELIGENTE PARA EL DASHBOARD
        self.huella_espera = ""
        self.huella_citas = ""
        
        self.timer_sincronizacion = QTimer(self)
        self.timer_sincronizacion.timeout.connect(self.verificar_cambios_dashboard)
        self.timer_sincronizacion.start(5000)  # Chequeo ligero cada 5 segundos

    # =========================================================
    # LÓGICA DE LA PESTAÑA 1: SALA DE ESPERA (Agenda Diaria)
    # =========================================================
    def setup_tab_espera(self):
        layout = QVBoxLayout(self.tab_espera)

        self.tabla_espera = QTableWidget()
        self.tabla_espera.setColumnCount(6) 
        self.tabla_espera.setHorizontalHeaderLabels(["Hora", "Paciente", "Cédula", "Estado", "ID_Agenda", "ID_Paciente"])
        self.tabla_espera.setColumnHidden(4, True)
        self.tabla_espera.setColumnHidden(5, True)
        self.tabla_espera.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_espera.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla_espera)

        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)
        
        self.btn_atender = QPushButton("🩺 INICIAR CONSULTA")
        self.btn_atender.setStyleSheet(tema.ESTILO_BTN_INFORME)
        self.btn_atender.clicked.connect(self.preparar_consulta) 

        self.btn_informe = QPushButton("📄 GENERAR INFORME")
        # INYECCIÓN DIRECTA: Forzamos el color #31d57e con hover adaptativo a un tono más oscuro (#27ae60)
        self.btn_informe.setStyleSheet("""
            QPushButton { 
                background-color: #31d57e; 
                color: white; 
                padding: 10px; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 13px;
            } 
            QPushButton:hover { 
                background-color: #27ae60; 
            }
        """)
        self.btn_informe.clicked.connect(self.preparar_informe)

        self.btn_factura = QPushButton("🧾 EMITIR FACTURA")
        self.btn_factura.setStyleSheet("background-color: #e67e22; color: white; padding: 10px; font-weight: bold; border-radius: 6px; font-size: 13px;")
        self.btn_factura.clicked.connect(self.preparar_factura)

        self.btn_finalizar = QPushButton("✅ MARCAR ATENDIDO")
        self.btn_finalizar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_finalizar.clicked.connect(lambda: self.cambiar_estado("Atendido"))

        self.btn_refresh = QPushButton("🔄 ACTUALIZAR")
        self.btn_refresh.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_refresh.clicked.connect(self.cargar_espera)

        layout_botones.addWidget(self.btn_atender)
        layout_botones.addWidget(self.btn_informe)
        layout_botones.addWidget(self.btn_factura) 
        layout_botones.addWidget(self.btn_finalizar)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_refresh)
        
        layout.addLayout(layout_botones)
        self.cargar_espera()

    def cargar_espera(self):
        try:
            db = SessionLocal()
            hoy = date.today()
            citas = db.query(AgendaDiaria).filter(AgendaDiaria.fecha_dia == hoy).order_by(AgendaDiaria.hora_llegada.asc()).all()
            
            self.tabla_espera.setRowCount(len(citas))
            color_titulos = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN

            for i, cita in enumerate(citas):
                p = db.query(Paciente).filter(Paciente.id == cita.paciente_id).first()
                
                item_hora = QTableWidgetItem(cita.hora_llegada.strftime("%I:%M %p"))
                item_pac = QTableWidgetItem(p.nombre_completo if p else "N/A")
                item_ced = QTableWidgetItem(p.cedula if p else "N/A")
                item_estado = QTableWidgetItem(cita.estado)
                
                item_estado.setTextAlignment(Qt.AlignCenter)
                
                for it in [item_hora, item_pac, item_ced, item_estado]:
                    it.setForeground(QColor(color_titulos))

                self.tabla_espera.setItem(i, 0, item_hora)
                self.tabla_espera.setItem(i, 1, item_pac)
                self.tabla_espera.setItem(i, 2, item_ced)
                self.tabla_espera.setItem(i, 3, item_estado)
                self.tabla_espera.setItem(i, 4, QTableWidgetItem(str(cita.id))) 
                self.tabla_espera.setItem(i, 5, QTableWidgetItem(str(p.id) if p else "0")) 
            db.close()
        except Exception as e:
            print(f"🌐 [DASHBOARD] Modo Terminal activo: Esperando conexión de red local... ({e})")
            # Dejamos la tabla limpia o con un aviso para que la app no explote
            if hasattr(self, 'tabla_espera'):
                self.tabla_espera.setRowCount(0)

    def ajustar_emergente_parent(self, box):
        # Ayudante para enlazar el parent de la app y heredar el estilo oscuro
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def preparar_consulta(self):
        fila = self.tabla_espera.currentRow()
        if fila == -1:
            box = QMessageBox(QMessageBox.Warning, "Atención", "Por favor, seleccione un paciente de la lista.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return

        id_agenda = int(self.tabla_espera.item(fila, 4).text())
        id_paciente = int(self.tabla_espera.item(fila, 5).text())

        db = SessionLocal()
        try:
            cita = db.query(AgendaDiaria).filter(AgendaDiaria.id == id_agenda).first()
            if cita:
                cita.estado = "En consulta"
                db.commit()
                self.cargar_espera() 
                self.iniciar_consulta_signal.emit(id_paciente)
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"No se pudo iniciar la consulta: {e}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
        finally:
            db.close()

    def preparar_informe(self):
        fila = self.tabla_espera.currentRow()
        if fila == -1:
            box = QMessageBox(QMessageBox.Warning, "Atención", "Por favor, seleccione un paciente de la lista.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return
        id_paciente = int(self.tabla_espera.item(fila, 5).text())
        self.solicitar_informe_signal.emit(id_paciente)

    def preparar_factura(self):
        fila = self.tabla_espera.currentRow()
        if fila == -1:
            box = QMessageBox(QMessageBox.Warning, "Atención", "Por favor, seleccione un paciente de la lista para facturar.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return
        id_paciente = int(self.tabla_espera.item(fila, 5).text())
        self.solicitar_factura_signal.emit(id_paciente)
        
    def cambiar_estado(self, nuevo_estado):
        fila_actual = self.tabla_espera.currentRow()
        if fila_actual == -1:
            box = QMessageBox(QMessageBox.Warning, "Atención", "Por favor, seleccione un paciente de la lista.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return

        id_agenda = int(self.tabla_espera.item(fila_actual, 4).text())
        db = SessionLocal()
        try:
            cita = db.query(AgendaDiaria).filter(AgendaDiaria.id == id_agenda).first()
            if cita:
                cita.estado = nuevo_estado
                db.commit()
                self.cargar_espera()
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"No se pudo cambiar el estado: {e}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
        finally:
            db.close()

    # =========================================================
    # LÓGICA DE LA PESTAÑA 2: AGENDA DE CITAS PROGRAMADAS
    # =========================================================
    def setup_tab_citas(self):
        layout = QVBoxLayout(self.tab_citas)

        self.tabla_citas = QTableWidget(0, 6)
        self.tabla_citas.setHorizontalHeaderLabels(["Paciente", "Fecha", "Días Restantes", "Motivo", "Confirmación", "Estado"])
        self.tabla_citas.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_citas.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla_citas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_citas.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabla_citas)

        lay_botones_sup = QHBoxLayout()
        lay_botones_inf = QHBoxLayout()
        lay_botones_sup.setSpacing(10)
        lay_botones_inf.setSpacing(10)
        
        self.btn_agendar = QPushButton("➕ Agendar Cita")
        self.btn_agendar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_agendar.clicked.connect(self.abrir_dialogo_agendar)

        self.btn_plantilla = QPushButton("⚙️ Modificar Mensaje WhatsApp")
        self.btn_plantilla.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_plantilla.clicked.connect(self.modificar_plantilla_whatsapp)

        lay_botones_sup.addWidget(self.btn_agendar)
        lay_botones_sup.addWidget(self.btn_plantilla)
        lay_botones_sup.addStretch()

        self.btn_notificar = QPushButton("📱 Notificar Cita")
        self.btn_notificar.setStyleSheet("background-color: #25D366; color: white; font-weight: bold; padding: 10px; border-radius: 6px; font-size: 13px;")
        self.btn_notificar.clicked.connect(self.notificar_whatsapp)

        self.btn_confirmar = QPushButton("✅ Confirmar Asistencia")
        self.btn_confirmar.setStyleSheet(tema.ESTILO_BTN_INFORME)
        self.btn_confirmar.clicked.connect(self.marcar_confirmado)

        self.btn_reagendar = QPushButton("🔄 Reagendar")
        self.btn_reagendar.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 10px; border-radius: 6px; font-size: 13px;")
        self.btn_reagendar.clicked.connect(self.reagendar_cita)

        self.btn_asistio = QPushButton("🏥 Marcar como Asistió")
        self.btn_asistio.setStyleSheet(tema.ESTILO_BTN_ORDEN)
        self.btn_asistio.clicked.connect(self.marcar_asistio)

        self.btn_eliminar_cita = QPushButton("🗑️ Eliminar Cita")
        self.btn_eliminar_cita.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_eliminar_cita.clicked.connect(self.eliminar_cita)

        lay_botones_inf.addWidget(self.btn_notificar)
        lay_botones_inf.addWidget(self.btn_confirmar)
        lay_botones_inf.addWidget(self.btn_reagendar)
        lay_botones_inf.addWidget(self.btn_asistio)
        lay_botones_inf.addWidget(self.btn_eliminar_cita)
        
        layout.addLayout(lay_botones_sup)
        layout.addLayout(lay_botones_inf)
        
        self.cargar_citas()

    def cargar_citas(self):
        try:
            db = SessionLocal()
            hoy = date.today()
            
            citas_vencidas = db.query(CitaMedica).filter(CitaMedica.fecha < hoy, CitaMedica.estado != "Asistió").all()
            if citas_vencidas:
                for cv in citas_vencidas:
                    db.delete(cv)
                db.commit()
                
            self.tabla_citas.setRowCount(0)
            citas = db.query(CitaMedica).filter(CitaMedica.fecha >= hoy).order_by(CitaMedica.fecha).all()
            color_titulos = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN

            for cita in citas:
                row = self.tabla_citas.rowCount()
                self.tabla_citas.insertRow(row)

                dias_restantes = (cita.fecha - hoy).days
                texto_dias = f"{dias_restantes} días" if dias_restantes > 1 else ("Mañana" if dias_restantes == 1 else "Hoy")
                
                item_pac = QTableWidgetItem(cita.paciente.nombre_completo)
                item_pac.setData(Qt.UserRole, cita.id) 
                
                item_fecha = QTableWidgetItem(cita.fecha.strftime("%d/%m/%Y"))
                item_dias = QTableWidgetItem(texto_dias)
                item_mot = QTableWidgetItem(cita.motivo if cita.motivo else "N/A")
                item_conf = QTableWidgetItem(cita.confirmacion)
                item_est = QTableWidgetItem(cita.estado)

                items = [item_pac, item_fecha, item_dias, item_mot, item_conf, item_est]
                
                if tema.modo_actual == "oscuro":
                    color_fondo_celda = QColor("#424549")
                    color_texto_celda = QColor("#FFFFFF")
                    
                    if cita.estado == "Asistió":
                        color_fondo_celda = QColor("#145A32")  
                        color_texto_celda = QColor("#2ECC71")  
                    elif cita.estado == "Pendiente":
                        if dias_restantes <= 1:
                            color_fondo_celda = QColor("#7B241C")  
                            color_texto_celda = QColor("#FFFFFF")  
                        elif 1 < dias_restantes <= 7:
                            color_fondo_celda = QColor("#7D6608")  
                            color_texto_celda = QColor("#FFFFFF")
                    
                    for it in items:
                        it.setBackground(QBrush(color_fondo_celda))
                        it.setForeground(QColor(color_texto_celda))
                else:
                    color_fondo = QColor(255, 255, 255)
                    if cita.estado == "Asistió":
                        color_fondo = QColor("#d5f5e3")
                    elif cita.estado == "Pendiente":
                        if dias_restantes <= 1:
                            color_fondo = QColor("#fadbd8")
                        elif 1 < dias_restantes <= 7:
                            color_fondo = QColor("#fcf3cf")
                    for it in items:
                        it.setBackground(QBrush(color_fondo))
                        it.setForeground(QColor(color_titulos))

                for it in items:
                    self.tabla_citas.setItem(row, items.index(it), it)

            db.close()
        except Exception as e:
            print(f"🌐 [DASHBOARD] Ignorando calendario de citas hasta sincronizar red.")
            if hasattr(self, 'tabla_citas'):
                self.tabla_citas.setRowCount(0)
                
    def obtener_id_cita_seleccionada(self):
        fila = self.tabla_citas.currentRow()
        if fila == -1:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione una cita programada de la tabla primero.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return None
        return self.tabla_citas.item(fila, 0).data(Qt.UserRole)

    def abrir_dialogo_agendar(self):
        dialogo = DialogoAgendar(self)
        if dialogo.exec():
            datos = dialogo.get_datos()
            if not datos:
                box = QMessageBox(QMessageBox.Warning, "Error", "Debe seleccionar un paciente.", QMessageBox.Ok, self)
                self.ajustar_emergente_parent(box); box.exec()
                return
                
            db = SessionLocal()
            cita_existente = db.query(CitaMedica).filter(
                CitaMedica.paciente_id == datos["paciente_id"],
                CitaMedica.estado == "Pendiente"
            ).first()
            
            if cita_existente:
                fecha_ext = cita_existente.fecha.strftime('%d/%m/%Y')
                box = QMessageBox(QMessageBox.Question, "Advertencia de Duplicado", 
                                  f"Este paciente ya tiene una cita agendada para el {fecha_ext}.\n¿Desea agendar otra cita de todos modos?", 
                                  QMessageBox.Yes | QMessageBox.No, self)
                self.ajustar_emergente_parent(box)
                if box.exec() == QMessageBox.No:
                    db.close()
                    return

            db.add(CitaMedica(paciente_id=datos["paciente_id"], fecha=datos["fecha"], motivo=datos["motivo"]))
            db.commit()
            db.close()
            self.cargar_citas()
            self.actualizar_notificaciones()

    def reagendar_cita(self):
        cita_id = self.obtener_id_cita_seleccionada()
        if not cita_id: return
        
        box = QMessageBox(QMessageBox.Question, "Confirmar", "¿Seguro quieres cambiar la fecha de esta cita?", QMessageBox.Yes | QMessageBox.No, self)
        self.ajustar_emergente_parent(box)
        if box.exec() == QMessageBox.No: return

        db = SessionLocal()
        cita = db.query(CitaMedica).get(cita_id)
        dialogo = DialogoReagendar(cita.fecha, self)
        if dialogo.exec():
            cita.fecha = dialogo.get_nueva_fecha()
            cita.confirmacion = "Por confirmar" 
            cita.estado = "Pendiente"
            db.commit()
            self.cargar_citas()
            self.actualizar_notificaciones()
        db.close()

    def marcar_confirmado(self):
        cita_id = self.obtener_id_cita_seleccionada()
        if not cita_id: return
        db = SessionLocal()
        cita = db.query(CitaMedica).get(cita_id)
        cita.confirmacion = "Confirmado"
        db.commit()
        db.close()
        self.cargar_citas()
        self.actualizar_notificaciones()

    def marcar_asistio(self):
        cita_id = self.obtener_id_cita_seleccionada()
        if not cita_id: return
        db = SessionLocal()
        cita = db.query(CitaMedica).get(cita_id)
        cita.estado = "Asistió"
        db.commit()
        db.close()
        self.cargar_citas()
        self.actualizar_notificaciones()

    def modificar_plantilla_whatsapp(self):
        settings = QSettings("SistemaMedico", "Configuracion")
        plantilla_default = "Hola {paciente}, le escribimos del consultorio médico para recordarle su cita el día {fecha} por el motivo de: {motivo}. Por favor confírmenos su asistencia por esta vía. ¡Saludos!"
        plantilla_actual = settings.value("whatsapp_template", plantilla_default)

        dialogo = DialogoPlantillaWhatsApp(plantilla_actual, self)
        if dialogo.exec():
            nueva_plantilla = dialogo.get_plantilla()
            if nueva_plantilla:
                settings.setValue("whatsapp_template", nueva_plantilla)
                box = QMessageBox(QMessageBox.Information, "Éxito", "Plantilla de WhatsApp actualizada correctamente.", QMessageBox.Ok, self)
                self.ajustar_emergente_parent(box); box.exec()

    def notificar_whatsapp(self):
        cita_id = self.obtener_id_cita_seleccionada()
        if not cita_id: return

        db = SessionLocal()
        cita = db.query(CitaMedica).get(cita_id)
        paciente = cita.paciente
        numero = paciente.telefono_celular
        
        if not numero:
            box = QMessageBox(QMessageBox.Warning, "Error", "Este paciente no tiene un número de teléfono registrado.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            db.close(); return
            
        numero_limpio = "".join(filter(str.isdigit, numero))
        if not numero.startswith("+") and not numero_limpio.startswith("58"):
            numero_limpio = "58" + numero_limpio.lstrip("0") 
            
        fecha_str = cita.fecha.strftime("%d/%m/%Y")
        texto_motivo = cita.motivo if cita.motivo else "chequeo médico"

        settings = QSettings("SistemaMedico", "Configuracion")
        plantilla_default = "Hola {paciente}, le escribimos del consultorio médico para recordarle su cita el día {fecha} por el motivo de: {motivo}. Por favor confírmenos su asistencia por esta vía. ¡Saludos!"
        plantilla = settings.value("whatsapp_template", plantilla_default)
        
        mensaje = plantilla.replace("{paciente}", paciente.nombre_completo)\
                           .replace("{fecha}", fecha_str)\
                           .replace("{motivo}", texto_motivo)

        mensaje_codificado = urllib.parse.quote(mensaje)
        url_whatsapp = f"https://wa.me/{numero_limpio}?text={mensaje_codificado}"
        
        QDesktopServices.openUrl(QUrl(url_whatsapp))
        db.close()

    def eliminar_cita(self):
        cita_id = self.obtener_id_cita_seleccionada()
        if not cita_id: return
        
        box = QMessageBox(QMessageBox.Question, "Confirmar Eliminación", 
                          "¿Está seguro de que desea ELIMINAR esta cita permanentemente de la agenda?", 
                          QMessageBox.Yes | QMessageBox.No, self)
        self.ajustar_emergente_parent(box)
        if box.exec() == QMessageBox.No: return

        db = SessionLocal()
        cita = db.query(CitaMedica).get(cita_id)
        if cita:
            db.delete(cita)
            db.commit()
        db.close()
        
        self.cargar_citas()
        self.actualizar_notificaciones()
        
        box = QMessageBox(QMessageBox.Information, "Éxito", "Cita eliminada de la base de datos.", QMessageBox.Ok, self)
        self.ajustar_emergente_parent(box); box.exec()

    # =========================================================
    # GESTIÓN DINÁMICA DE ESTILOS (ADAPTACIÓN CENTRALIZADA)
    # =========================================================
    def actualizar_diseno_dinamico(self):
        color_fondo_tabla = "#424549" if tema.modo_actual == "oscuro" else tema.BG_INPUT
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_titulos = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        
        self.tab_espera.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.tab_citas.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.menu_notificaciones.setStyleSheet(tema.ESTILO_VENTANA)

        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {tema.BORDE_SUAVE};
                background-color: {color_fondo_paginas};
            }}
            QTabBar::tab {{
                background-color: {color_fondo_tabla};
                color: {color_titulos};
                border: 1px solid {tema.BORDE_SUAVE};
                padding: 10px 20px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {tema.MENTA_MEDICA};
                color: #1C1C1C;
                border-bottom-color: transparent;
            }}
        """)
        
        for tabla in [self.tabla_espera, self.tabla_citas]:
            tabla.setStyleSheet(f"""
                QTableWidget {{ 
                    background-color: {color_fondo_tabla}; 
                    color: {color_titulos}; 
                    gridline-color: {tema.COLOR_DIVISION_TABLA}; 
                    font-size: 13px;
                    border: 1px solid {tema.BORDE_SUAVE};
                }}
                QHeaderView::section {{
                    background-color: #93F6E3;
                    color: #1C1C1C;
                    font-weight: bold;
                    padding: 6px;
                    border: 1px solid {tema.BORDE_SUAVE};
                }}
            """)
        
        self.lbl_titulo_dash.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        self.cargar_espera()
        self.cargar_citas()

    # =========================================================
    # LÓGICA DE NOTIFICACIONES EN CABECERA (CAMPANITA)
    # =========================================================
    # =========================================================
    # LÓGICA DE NOTIFICACIONES EN CABECERA (CAMPANITA)
    # =========================================================
    # =================================================================
# LÓGICA DE NOTIFICACIONES EN CABECERA CORREGIDA Y AUDIO-REACTIVA
# =================================================================
    def actualizar_notificaciones(self):
        try:
            self.menu_notificaciones.clear()
            
            settings = QSettings("SistemaMedico", "Configuracion")
            alerta_7 = settings.value("alerta_7_dias", True, type=bool)
            alerta_1 = settings.value("alerta_1_dia", True, type=bool)

            db = SessionLocal()
            hoy = date.today()
            citas = db.query(CitaMedica).filter(
                CitaMedica.fecha >= hoy, 
                CitaMedica.estado == "Pendiente",
                CitaMedica.confirmacion == "Por confirmar"
            ).order_by(CitaMedica.fecha).all()

            contador_actual = 0
            Hubo_alertas_nuevas = False

            if alerta_7 or alerta_1:
                for cita in citas:
                    dias_restantes = (cita.fecha - hoy).days
                    mostrar = False
                    
                    if dias_restantes == 1 and alerta_1: mostrar = True
                    elif dias_restantes == 7 and alerta_7: mostrar = True
                    
                    if mostrar:
                        contador_actual += 1
                        Hubo_alertas_nuevas = True
                        
                        badge_txt = "ahora" if dias_restantes == 1 else "en 7d"
                        fecha_str = cita.fecha.strftime("%d/%m/%Y")
                        
                        # Pasamos los nuevos parámetros: ID de la cita y la instancia del Dashboard (self)
                        widget_notificacion = TarjetaNotificacionWidget(
                            badge_tiempo=badge_txt.upper(),
                            paciente_nombre=cita.paciente.nombre_completo,
                            fecha_cita=fecha_str,
                            cita_id=cita.id,
                            dashboard_parent=self
                        )
                        
                        accion_custom = QWidgetAction(self.menu_notificaciones)
                        accion_custom.setDefaultWidget(widget_notificacion)
                        
                        # Añadimos al menú directamente. El evento interno de la tarjeta se encarga del resto
                        self.menu_notificaciones.addAction(accion_custom)

            db.close()
            
            # --- BOTÓN DE CONFIGURACIÓN MINIMALISTA INFERIOR ---
            self.menu_notificaciones.addSeparator()
            accion_config = QAction("⚙️ Configurar Alertas de la Agenda", self)
            accion_config.triggered.connect(self.abrir_configuracion_alertas)
            self.menu_notificaciones.addAction(accion_config)

            # 🔊 DETECTOR REACTIVO: Si entran alertas nuevas, suena el sistema al instante
            texto_notificaciones_anterior = self.btn_notificaciones.text()
            numero_anterior = int("".join(filter(str.isdigit, texto_notificaciones_anterior))) if any(str.isdigit() for str in texto_notificaciones_anterior) else 0

            if contador_actual > numero_anterior and Hubo_alertas_nuevas:
                tema.reproducir_alerta_notificacion()

            if contador_actual > 0:
                self.btn_notificaciones.setText(f"🔔 ({contador_actual})")
                self.btn_notificaciones.setStyleSheet("color: #F43F5E; font-size: 18px; font-weight: bold; border: none; padding: 5px; background: transparent;")
            else:
                self.btn_notificaciones.setText("🔔 (0)")
                self.btn_notificaciones.setStyleSheet("color: #64748B; font-size: 18px; font-weight: bold; border: none; padding: 5px; background: transparent;")
        except Exception as e:
            print(f"🌐 [DASHBOARD] Ignorando módulo de notificaciones hasta resolver enlace de red: {e}")
            self.btn_notificaciones.setText("🔔 (0)")
            self.btn_notificaciones.setStyleSheet("color: #64748B; font-size: 18px; font-weight: bold; border: none; padding: 5px; background: transparent;")

    def ir_a_cita_desde_notificacion(self, cita_id):
        self.tabs.setCurrentIndex(1)
        for row in range(self.tabla_citas.rowCount()):
            item_pac = self.tabla_citas.item(row, 0)
            if item_pac and item_pac.data(Qt.UserRole) == cita_id:
                self.tabla_citas.selectRow(row)
                break
    
    def abrir_configuracion_alertas(self):
        dialogo = DialogoConfigAlertas(self)
        if dialogo.exec():
            self.actualizar_notificaciones()

    
    def verificar_cambios_dashboard(self):
        db = SessionLocal()
        try:
            hoy = date.today()
            
            # 1. HUELLA SALA DE ESPERA: Solo pedimos la columna 'id' y 'estado' (Pesa casi 0 bytes)
            espera_db = db.query(AgendaDiaria.id, AgendaDiaria.estado).filter(AgendaDiaria.fecha_dia == hoy).all()
            nueva_huella_espera = str(espera_db)
            
            # 2. HUELLA DE CITAS: Solo pedimos id, fecha, confirmacion y estado (De hoy en adelante)
            citas_db = db.query(
                CitaMedica.id, 
                CitaMedica.fecha, 
                CitaMedica.confirmacion, 
                CitaMedica.estado
            ).filter(CitaMedica.fecha >= hoy).all()
            nueva_huella_citas = str(citas_db)

            # --- Evaluar Sala de Espera ---
            if self.huella_espera != nueva_huella_espera:
                if self.huella_espera != "":
                    self.cargar_espera() 
                self.huella_espera = nueva_huella_espera

            # --- Evaluar Agenda de Citas ---
            if self.huella_citas != nueva_huella_citas:
                if self.huella_citas != "":
                    self.cargar_citas()
                    self.actualizar_notificaciones() 
                self.huella_citas = nueva_huella_citas

        except Exception:
            pass  
        finally:
            db.close()

class DialogoConfigAlertas(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Alertas de Confirmación")
        self.setFixedSize(350, 150)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)

        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN

        lbl = QLabel("<b>Seleccione cuándo desea que el sistema le alerte:</b>")
        lbl.setStyleSheet(f"color: {color_txt}; background: transparent;")
        layout.addWidget(lbl)

        self.settings = QSettings("SistemaMedico", "Configuracion")
        
        alerta_7 = self.settings.value("alerta_7_dias", True, type=bool)
        alerta_1 = self.settings.value("alerta_1_dia", True, type=bool)

        self.check_7_dias = QCheckBox("Recordar faltando 7 días")
        self.check_7_dias.setChecked(alerta_7)
        
        self.check_1_dia = QCheckBox("Recordar faltando 1 día")
        self.check_1_dia.setChecked(alerta_1)

        for cb in [self.check_7_dias, self.check_1_dia]:
            cb.setStyleSheet(f"color: {color_txt}; font-size: 13px; background: transparent;")

        layout.addWidget(self.check_7_dias)
        layout.addWidget(self.check_1_dia)

        lay_btns = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar Cambios")
        btn_guardar.setStyleSheet(tema.ESTILO_BTN_RECIPE)
        btn_guardar.clicked.connect(self.guardar_y_cerrar)
        lay_btns.addStretch()
        lay_btns.addWidget(btn_guardar)
        
        layout.addLayout(lay_btns)

    def guardar_y_cerrar(self):
        self.settings.setValue("alerta_7_dias", self.check_7_dias.isChecked())
        self.settings.setValue("alerta_1_dia", self.check_1_dia.isChecked())
        self.accept()