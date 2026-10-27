from PySide6.QtWidgets import (QMenu, QTabBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QTreeWidget, QTreeWidgetItem, QFileDialog, 
                               QTabWidget, QMessageBox, QTextEdit, QSplitter, QGridLayout,
                               QInputDialog, QFrame, QSizePolicy) 
from PySide6.QtCore import QTimer, Signal, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QColor, QBrush
import os
import shutil
import re
from datetime import datetime
from database import SessionLocal
from servicios_impresion import MotorImpresion
from models import (Paciente, ArchivoPaciente, Consulta, InformeMedico, 
                    Antecedentes, GinecoObstetrico, PerfilDoctor, ConsentimientoCirugia,
                    InformeEgreso, NotaOperatoria)
from estilos import tema

class PantallaHistorial(QWidget):
    solicitar_consulta = Signal(int)
    solicitar_antecedentes = Signal(int)
    solicitar_informe = Signal(int)      
    solicitar_consentimiento = Signal(int)
    solicitar_receta_rapida = Signal(int) 
    solicitar_orden_rapida = Signal(int)
    solicitar_egreso = Signal(int)        
    solicitar_post_op = Signal(int)
    solicitar_factura = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.ruta_almacenamiento = "archivos_clinica"
        
        self.setAcceptDrops(True)
        if not os.path.exists(self.ruta_almacenamiento):
            os.makedirs(self.ruta_almacenamiento)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        layout_principal.setSpacing(15)
        
        self.splitter_horizontal = QSplitter(Qt.Horizontal)

        # --- SECCIÓN 1: BUSCADOR (IZQUIERDA) ---
        self.widget_izq = QWidget()
        self.widget_izq.setMinimumWidth(280)
        lay_izq = QVBoxLayout(self.widget_izq)
        lay_izq.setContentsMargins(0, 0, 5, 0)
        
        self.lbl_titulo_sel = QLabel("<h3>🔍 Selección de Paciente</h3>")
        lay_izq.addWidget(self.lbl_titulo_sel)
        
        self.in_buscador = QLineEdit(placeholderText="Nombre o cédula...")
        self.in_buscador.setMinimumHeight(38)
        self.in_buscador.textChanged.connect(self.actualizar_lista)
        lay_izq.addWidget(self.in_buscador)
        
        self.tabla_pacientes = QTableWidget(0, 2)
        self.tabla_pacientes.setHorizontalHeaderLabels(["Cédula", "Nombre"])
        self.tabla_pacientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_pacientes.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_pacientes.cellClicked.connect(self.seleccionar_paciente)
        lay_izq.addWidget(self.tabla_pacientes)

        # --- SECCIÓN 2: HISTORIAL Y VISOR (DERECHA) ---
        self.widget_der = QWidget()
        lay_der = QVBoxLayout(self.widget_der)
        lay_der.setContentsMargins(5, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        # TAB 1: EL EXPEDIENTE
        self.tab_clinica = QWidget()
        layout_c = QHBoxLayout(self.tab_clinica)
        layout_c.setContentsMargins(10, 10, 10, 10)
        layout_c.setSpacing(15)
        
        widget_arbol = QWidget()
        widget_arbol.setMinimumWidth(280) 
        lay_arbol = QVBoxLayout(widget_arbol)
        lay_arbol.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_linea_t = QLabel("<b>📂 Línea de Tiempo / Categorías:</b>")
        lay_arbol.addWidget(self.lbl_linea_t)
        
        self.arbol_historial = QTreeWidget()
        self.arbol_historial.setHeaderLabel("Eventos Registrados")
        self.arbol_historial.itemClicked.connect(self.mostrar_detalle_evento)
        lay_arbol.addWidget(self.arbol_historial)
        
        self.btn_nueva = QPushButton("🩺 INICIAR NUEVA CONSULTA")
        self.btn_nueva.setMinimumHeight(45)
        self.btn_nueva.setCursor(Qt.PointingHandCursor)
        self.btn_nueva.clicked.connect(lambda: self.solicitar_consulta.emit(self.paciente_id) if self.paciente_id else None)
        lay_arbol.addWidget(self.btn_nueva)
        
        self.visor_lectura = QTextEdit()
        self.visor_lectura.setReadOnly(True)
        
        # 🚀 REPORTE DE CAMBIO: Se ajustan las proporciones para expandir el visualizador 
        layout_c.addWidget(widget_arbol, 20)
        layout_c.addWidget(self.visor_lectura, 80)

        # TAB 2: ARCHIVO DIGITAL
        self.tab_archivos = QWidget()
        layout_a = QVBoxLayout(self.tab_archivos)
        layout_a.setContentsMargins(10, 10, 10, 10)
        layout_a.setSpacing(12)
        
        self.tabla_archivos = QTableWidget(0, 3)
        self.tabla_archivos.setHorizontalHeaderLabels(["Nombre del Archivo", "Tipo", "Fecha"])
        self.tabla_archivos.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.tabla_archivos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout_a.addWidget(self.tabla_archivos)
        
        btns_arch = QHBoxLayout()
        btns_arch.setSpacing(10)
        self.btn_add = QPushButton("📎 Adjuntar Archivo"); self.btn_add.setFixedHeight(40); self.btn_add.setCursor(Qt.PointingHandCursor); self.btn_add.clicked.connect(self.adjuntar_archivo)
        self.btn_open = QPushButton("📂 Abrir"); self.btn_open.setFixedHeight(40); self.btn_open.setCursor(Qt.PointingHandCursor); self.btn_open.clicked.connect(self.abrir_archivo)
        self.btn_rename = QPushButton("✏️ Renombrar"); self.btn_rename.setFixedHeight(40); self.btn_rename.setCursor(Qt.PointingHandCursor); self.btn_rename.clicked.connect(self.renombrar_archivo)
        self.btn_del = QPushButton("🗑️ Quitar"); self.btn_del.setFixedHeight(40); self.btn_del.setCursor(Qt.PointingHandCursor); self.btn_del.clicked.connect(self.eliminar_adjunto)
        
        btns_arch.addWidget(self.btn_add); btns_arch.addWidget(self.btn_open); btns_arch.addWidget(self.btn_rename); btns_arch.addWidget(self.btn_del)
        layout_a.addLayout(btns_arch)

        # TAB 3: ACCIONES REORGANIZADO (DASHBOARD)
        self.tab_acciones = QWidget()
        layout_dash = QHBoxLayout(self.tab_acciones)
        layout_dash.setContentsMargins(15, 15, 15, 15)
        layout_dash.setSpacing(15)
        
        # Panel Izquierdo Dashboard: Tarjeta Informativa del Paciente
        self.card_paciente = QFrame()
        self.card_paciente.setFrameShape(QFrame.StyledPanel)
        self.card_paciente.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        lay_card = QVBoxLayout(self.card_paciente)
        lay_card.setContentsMargins(20, 20, 20, 20)
        lay_card.setSpacing(15)
        lay_card.setAlignment(Qt.AlignTop)
        
        self.lbl_info_paciente = QLabel("<h3>⚡ Centro de Gestión</h3><p>Seleccione un paciente en la lista lateral para habilitar el panel de operaciones.</p>")
        self.lbl_info_paciente.setWordWrap(True)
        lay_card.addWidget(self.lbl_info_paciente)
        layout_dash.addWidget(self.card_paciente, 35)
        
        # Panel Derecho Dashboard: Matriz de Acciones Expandible
        widget_rejilla = QWidget()
        grid_botones = QGridLayout(widget_rejilla)
        grid_botones.setContentsMargins(0, 0, 0, 0)
        grid_botones.setSpacing(15)
        
        self.btn_acc_consulta = QPushButton("🩺 INICIAR\nNUEVA CONSULTA")
        self.btn_acc_informe = QPushButton("📄 REDACTAR\nINFORME MÉDICO")
        self.btn_acc_orden = QPushButton("🔬 ORDEN DE\nEXÁMENES")
        self.btn_acc_recipe = QPushButton("💊 EMITIR\nRÉCIPE RÁPIDO")
        self.btn_acc_postop = QPushButton("😷 NOTA\nOPERATORIA")
        self.btn_acc_egreso = QPushButton("🏥 INFORME DE\nEGRESO")
        self.btn_acc_consent = QPushButton("⚖️ GENERAR\nCONSENTIMIENTO")
        self.btn_acc_factura = QPushButton("💰 MODULO DE\nFACTURACIÓN")

        # ORGANIZACIÓN EN MATRIZ DE 2 COLUMNAS POR FILA
        grid_botones.addWidget(self.btn_acc_consulta, 0, 0)
        grid_botones.addWidget(self.btn_acc_informe, 0, 1)
        grid_botones.addWidget(self.btn_acc_orden, 1, 0)
        grid_botones.addWidget(self.btn_acc_recipe, 1, 1)
        grid_botones.addWidget(self.btn_acc_postop, 2, 0)
        grid_botones.addWidget(self.btn_acc_egreso, 2, 1)
        grid_botones.addWidget(self.btn_acc_consent, 3, 0) 
        grid_botones.addWidget(self.btn_acc_factura, 3, 1)

        for btn in [self.btn_acc_consulta, self.btn_acc_informe, self.btn_acc_postop, 
                    self.btn_acc_recipe, self.btn_acc_orden, self.btn_acc_egreso, self.btn_acc_consent, self.btn_acc_factura]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(85)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_acc_consulta.clicked.connect(lambda: self.solicitar_consulta.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_informe.clicked.connect(lambda: self.solicitar_informe.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_orden.clicked.connect(lambda: self.solicitar_orden_rapida.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_recipe.clicked.connect(lambda: self.solicitar_receta_rapida.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_consent.clicked.connect(lambda: self.solicitar_consentimiento.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_egreso.clicked.connect(lambda: self.solicitar_egreso.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_postop.clicked.connect(lambda: self.solicitar_post_op.emit(self.paciente_id) if self.paciente_id else None)
        self.btn_acc_factura.clicked.connect(lambda: self.solicitar_factura.emit(self.paciente_id) if self.paciente_id else None)

        layout_dash.addWidget(widget_rejilla, 65)

        # AGREGAR TABS PRINCIPALES
        self.tabs.addTab(self.tab_clinica, "📜 Historial Clínico")
        self.tabs.addTab(self.tab_archivos, "📄 Archivo Digital")
        self.tabs.addTab(self.tab_acciones, "⚡ Acciones")

        lay_der.addWidget(self.tabs)
        self.splitter_horizontal.addWidget(self.widget_izq)
        self.splitter_horizontal.addWidget(self.widget_der)
        
        # 🚀 REPORTE DE CAMBIO: Se ajusta el splitter dando prioridad de espacio al bloque del visor (de 880 a 1050)
        self.splitter_horizontal.setSizes([250, 1050])
        layout_principal.addWidget(self.splitter_horizontal)

        self.actualizar_lista()

        # --- CONFIGURACIÓN DE BOTONES FLOTANTES DE IMPRESIÓN ---
        # --- CONFIGURACIÓN DE BOTONES FLOTANTES DE IMPRESIÓN CON MENÚ DESPLEGABLE ---
        self.btn_generar_pdf_historia = QPushButton("🖨️ Generar Documento ▾", self.visor_lectura)
        self.btn_generar_pdf_informe = QPushButton("🖨️ Generar Documento ▾", self.visor_lectura)
        self.btn_generar_pdf_consentimiento = QPushButton("🖨️ Generar Documento ▾", self.visor_lectura)
        self.btn_generar_pdf_egreso = QPushButton("🖨️ Generar Documento ▾", self.visor_lectura)
        self.btn_generar_pdf_postop = QPushButton("🖨️ Generar Documento ▾", self.visor_lectura)

        botones_config = [
            (self.btn_generar_pdf_historia, self.imprimir_consulta_seleccionada),
            (self.btn_generar_pdf_informe, self.imprimir_informe_seleccionado),
            (self.btn_generar_pdf_consentimiento, self.imprimir_consentimiento_seleccionado),
            (self.btn_generar_pdf_egreso, self.imprimir_egreso_seleccionado),
            (self.btn_generar_pdf_postop, self.imprimir_postop_seleccionado)
        ]

        for btn_f, metodo_handler in botones_config:
            btn_f.setFixedSize(210, 36)
            btn_f.setCursor(Qt.PointingHandCursor)
            
            menu_btn = QMenu(self)
            menu_btn.setStyleSheet(tema.ESTILO_VENTANA)
            
            act_pdf = QAction("📄 Exportar a PDF (.pdf)", self)
            act_pdf.triggered.connect(lambda _, m=metodo_handler: m(formato="pdf"))
            
            act_docx = QAction("📝 Exportar a Word (.docx)", self)
            act_docx.triggered.connect(lambda _, m=metodo_handler: m(formato="docx"))
            
            menu_btn.addAction(act_pdf)
            menu_btn.addAction(act_docx)
            btn_f.setMenu(menu_btn)
            btn_f.hide()
            
        self.btn_generar_pdf_historia.clicked.connect(self.imprimir_consulta_seleccionada)
        self.btn_generar_pdf_informe.clicked.connect(self.imprimir_informe_seleccionado)
        self.btn_generar_pdf_consentimiento.clicked.connect(self.imprimir_consentimiento_seleccionado)
        self.btn_generar_pdf_egreso.clicked.connect(self.imprimir_egreso_seleccionado)
        self.btn_generar_pdf_postop.clicked.connect(self.imprimir_postop_seleccionado)

        self._visor_resize_original = self.visor_lectura.resizeEvent 
        self.visor_lectura.resizeEvent = self.reposicionar_boton

        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

        # ⏱️ CONFIGURACIÓN DEL LATIDO INTELIGENTE PARA EL HISTORIAL
        self.huella_pacientes = ""
        self.timer_sincronizacion = QTimer(self)
        self.timer_sincronizacion.timeout.connect(self.verificar_cambios_historial)
        self.timer_sincronizacion.start(5000)
        
    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        self.setStyleSheet(tema.ESTILO_VENTANA)
        self.in_buscador.setStyleSheet(f"QLineEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; padding: 6px; border-radius: 5px; }} QLineEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; }}")
        self.lbl_titulo_sel.setStyleSheet(f"color: {color_txt}; background: transparent;")
        self.lbl_linea_t.setStyleSheet(f"color: {color_txt}; background: transparent;")
        
        style_tablas = f"""
            QTableWidget {{ background-color: {color_fondo_entry}; color: {color_txt}; gridline-color: {tema.BORDE_SUAVE}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; }}
            QHeaderView::section {{ background-color: #93F6E3; color: #1C1C1C; font-weight: bold; padding: 6px; border: 1px solid {tema.BORDE_SUAVE}; }}
            QTableWidget::item {{ color: {color_txt}; }}
        """
        self.tabla_pacientes.setStyleSheet(style_tablas)
        self.tabla_archivos.setStyleSheet(style_tablas)

        color_tab_clinica = "#7288da"
        color_tab_archivos = "#4caf50" if tema.modo_actual == "oscuro" else "#31d57e"
        color_tab_acciones = "#e67e22"
        
        style_tabs = f"""
            QTabWidget::panel {{ 
                border: 1px solid {tema.BORDE_SUAVE}; 
                background-color: {tema.BG_TARJETA}; 
                border-radius: 6px; 
            }} 
            QTabBar::tab {{ 
                font-size: 13px; 
                font-weight: bold; 
                height: 40px; 
                width: 180px; 
                border: 1px solid {tema.BORDE_SUAVE};
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 4px;
                padding: 6px;
            }}
        """
        self.tabs.setStyleSheet(style_tabs)

        barra = self.tabs.tabBar()
        colores_pestanas = [color_tab_clinica, color_tab_archivos, color_tab_acciones]
        barra.setAutoFillBackground(True)
        
        for i in range(min(barra.count(), len(colores_pestanas))):
            barra.setTabTextColor(i, QColor("#FFFFFF"))
            from PySide6.QtGui import QPalette
            paleta_pestana = barra.palette()
            color_hex = colores_pestanas[i]
            paleta_pestana.setColor(QPalette.Window, QColor(color_hex))
            paleta_pestana.setColor(QPalette.Button, QColor(color_hex))
            paleta_pestana.setColor(QPalette.Base, QColor(color_hex))

        barra.setStyleSheet(f"""
            QTabBar::tab:selected {{ border-bottom-color: {tema.BG_TARJETA}; }}
            QTabBar::tab:hover {{ border: 1px solid #FFFFFF; }}
            QTabBar::tab:first {{ background-color: {color_tab_clinica}; color: white; }}
            QTabBar::tab:middle {{ background-color: {color_tab_archivos}; color: white; }}
            QTabBar::tab:last {{ background-color: {color_tab_acciones}; color: white; }}
        """)

        bg_header_arbol = "#424549" if tema.modo_actual == "oscuro" else "#f2f2f2"
        txt_header_arbol = "#FFFFFF" if tema.modo_actual == "oscuro" else "#1C1C1C"
        self.arbol_historial.setStyleSheet(f"""
            QTreeWidget {{ font-size: 14px; border: 1px solid {tema.BORDE_SUAVE}; background-color: {color_fondo_entry}; color: {color_txt}; border-radius: 6px; padding: 4px; }}
            QHeaderView::section {{ background-color: {bg_header_arbol}; color: {txt_header_arbol}; font-weight: bold; padding: 5px; border: 1px solid {tema.BORDE_SUAVE}; }}
            QTreeWidget::item {{ height: 42px; border-bottom: 1px solid {tema.BORDE_SUAVE}; padding-left: 5px; }}
            QTreeWidget::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; }}
        """)

        # 🚀 REPORTE DE CAMBIO: Se incrementa el padding interno de 15px a 20px y se asegura una fuente de 16px para mejor legibilidad
        self.visor_lectura.setStyleSheet(f"""
            QTextEdit {{ 
                background-color: {color_fondo_entry}; 
                border: 1px solid {tema.BORDE_SUAVE}; 
                font-size: 16px; border-radius: 6px; padding: 20px; color: {color_txt}; 
            }}
        """)

        self.btn_nueva.setStyleSheet("QPushButton { background-color: #3498DB; color: white; font-weight: bold; border-radius: 5px; } QPushButton:hover { background-color: #2980B9; }")

        self.btn_add.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_open.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_rename.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_del.setStyleSheet(tema.ESTILO_BTN_PELIGRO)

        self.card_paciente.setStyleSheet(f"QFrame {{ background-color: {'#2f3136' if tema.modo_actual == 'oscuro' else '#fdfdfd'}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 10px; }} QLabel {{ border: none; background: transparent; color: {color_txt}; }}")
        
        self.btn_acc_consulta.setStyleSheet("QPushButton { background-color: #3498DB; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #2980B9; }")
        self.btn_acc_informe.setStyleSheet("QPushButton { background-color: #31d57e; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #27ae60; }")
        self.btn_acc_postop.setStyleSheet("QPushButton { background-color: #c0392b; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #e74c3c; }")
        self.btn_acc_recipe.setStyleSheet("QPushButton { background-color: #7289da; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #5b73c7; }")
        self.btn_acc_orden.setStyleSheet("QPushButton { background-color: #4caf50; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #43a047; }")
        self.btn_acc_egreso.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #9b59b6; }")
        self.btn_acc_consent.setStyleSheet("QPushButton { background-color: #e67e22; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #d35400; }")
        self.btn_acc_factura.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; font-size: 12px; font-weight: bold; border-radius: 8px; } QPushButton:hover { background-color: #27ae60; }")
        
        self.btn_generar_pdf_historia.setStyleSheet("QPushButton { background-color: #3498DB; color: white; border-radius: 5px; font-weight: bold; }")
        self.btn_generar_pdf_informe.setStyleSheet("QPushButton { background-color: #31d57e; color: white; border-radius: 5px; font-weight: bold; }")
        self.btn_generar_pdf_consentimiento.setStyleSheet("QPushButton { background-color: #e67e22; color: white; border-radius: 5px; font-weight: bold; }")
        self.btn_generar_pdf_egreso.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; border-radius: 5px; font-weight: bold; }")
        self.btn_generar_pdf_postop.setStyleSheet("QPushButton { background-color: #c0392b; color: white; border-radius: 5px; font-weight: bold; }")

        if self.arbol_historial.currentItem():
            self.mostrar_detalle_evento(self.arbol_historial.currentItem(), 0)
        self.actualizar_tabla_archivos()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.paciente_id:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Primero seleccione un paciente para adjuntar archivos.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
            return
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self._procesar_y_guardar_archivo(file_path)

    def _procesar_y_guardar_archivo(self, file_path):
        db = SessionLocal()
        paciente = db.query(Paciente).get(self.paciente_id)
        if not paciente:
            db.close(); return

        nombre_orig = os.path.basename(file_path)
        nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
        nombre_carpeta = f"{nombre_limpio}_{paciente.cedula}"
        ruta_paciente = os.path.join(self.ruta_almacenamiento, nombre_carpeta)

        if not os.path.exists(ruta_paciente):
            os.makedirs(ruta_paciente)

        if db.query(ArchivoPaciente).filter(ArchivoPaciente.paciente_id == self.paciente_id, 
                                          ArchivoPaciente.nombre_archivo == nombre_orig).first():
            box = QMessageBox(QMessageBox.Warning, "Duplicado", f"El archivo '{nombre_orig}' ya existe.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
            db.close(); return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nuevo_nombre_fisico = f"{timestamp}_{nombre_orig}"
        ruta_destino = os.path.join(ruta_paciente, nuevo_nombre_fisico)

        try:
            shutil.copy(file_path, ruta_destino)
            nuevo_adjunto = ArchivoPaciente(
                paciente_id=self.paciente_id,
                nombre_archivo=nombre_orig,
                ruta_archivo=ruta_destino,
                tipo_archivo=nombre_orig.split('.')[-1].upper()
            )
            db.add(nuevo_adjunto); db.commit()
            self.actualizar_tabla_archivos()
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error", f"Error al copiar archivo: {str(e)}", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
        finally: db.close()

    def adjuntar_archivo(self):
        if not self.paciente_id: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Adjuntar", "", "Archivos (*.pdf *.docx *.jpg *.png *.jpeg)")
        if file_path: self._procesar_y_guardar_archivo(file_path)

    def renombrar_archivo(self):
        fila = self.tabla_archivos.currentRow()
        if fila == -1: return
        it_first = self.tabla_archivos.item(fila, 0)
        if not it_first: return
        id_arc = it_first.data(Qt.UserRole)
        if not id_arc: return 

        db = SessionLocal()
        arc = db.query(ArchivoPaciente).get(id_arc)
        if not arc:
            db.close(); return

        nombre_actual = arc.nombre_archivo
        
        dialogo = QInputDialog(self)
        dialogo.setWindowTitle("Renombrar Archivo")
        dialogo.setLabelText("Nuevo nombre (mantenga la extensión):")
        dialogo.setTextValue(nombre_actual)
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        dialogo.setStyleSheet(f"QInputDialog {{ background-color: {'#36393e' if tema.modo_actual == 'oscuro' else tema.BG_TARJETA}; color: {color_txt}; }} QLabel {{ color: {color_txt}; }} QLineEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; padding: 5px; border-radius: 4px; }} QPushButton {{ background-color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'}; color: {'#1C1C1C' if tema.modo_actual == 'oscuro' else '#FFFFFF'}; font-weight: bold; padding: 5px 12px; border-radius: 4px; }}")
        
        if dialogo.exec() == QInputDialog.Accepted:
            nuevo_nombre = dialogo.textValue().strip()
            if nuevo_nombre and nuevo_nombre != nombre_actual:
                ruta_vieja = arc.ruta_archivo
                directorio = os.path.dirname(ruta_vieja)
                
                ext_vieja = os.path.splitext(nombre_actual)[1]
                ext_nueva = os.path.splitext(nuevo_nombre)[1]
                if ext_nueva.lower() != ext_vieja.lower():
                    nuevo_nombre += ext_vieja

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nuevo_nombre_fisico = f"{timestamp}_{nuevo_nombre}"
                ruta_nueva = os.path.join(directorio, nuevo_nombre_fisico)

                try:
                    if os.path.exists(ruta_vieja):
                        os.rename(ruta_vieja, ruta_nueva)
                    arc.nombre_archivo = nuevo_nombre
                    arc.ruta_archivo = ruta_nueva
                    db.commit()
                    self.actualizar_tabla_archivos()
                except Exception as e:
                    box = QMessageBox(QMessageBox.Critical, "Error", f"No se pudo renombrar el archivo: {e}", QMessageBox.Ok, self)
                    box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
        db.close()

    def seleccionar_paciente(self, row, col):
        cedula = self.tabla_pacientes.item(row, 0).text()
        db = SessionLocal()
        p = db.query(Paciente).filter(Paciente.cedula == cedula).first()
        if p:
            self.paciente_id = p.id
            
            info_html = f"""
                <h3 style='margin-top:0; color: #52d5bc;'>⚡ Paciente Activo</h3>
                <hr style='border: none; border-top: 1px solid {tema.BORDE_SUAVE};'>
                <p style='font-size:14px; margin-bottom:8px;'><b>Nombre:</b><br>{p.nombre_completo}</p>
                <p style='font-size:14px; margin-bottom:8px;'><b>Cédula:</b><br>{p.cedula}</p>
                <p style='font-size:14px; margin-bottom:8px;'><b>Género:</b><br>{p.genero if p.genero else 'N/R'}</p>
                <p style='font-size:14px; margin-bottom:8px;'><b>Edad Clínica:</b><br>{p.edad_actual} años</p>
            """
            self.lbl_info_paciente.setText(info_html)
            self.cargar_arbol(p)
            self.actualizar_tabla_archivos() 
            self.visor_lectura.clear()
        db.close()

    def actualizar_tabla_archivos(self):
        if not self.paciente_id: return
        self.tabla_archivos.clearSpans()
        db = SessionLocal()
        archivos = db.query(ArchivoPaciente).filter(ArchivoPaciente.paciente_id == self.paciente_id).order_by(ArchivoPaciente.fecha_subida.desc()).all()
        
        categorias = {
            "📜 Historias Clínicas": [],
            "📄 Informes Médicos": [],
            "🏥 Informes de Egreso": [],        
            "😷 Informes Post-Operatorios": [], 
            "🔬 Exámenes": [],                  
            "⚖️ Consentimientos Legales": [],
            "🖼️ Imágenes y Anexos": [],
            "📎 Otros Documentos": []
        }
        
        for arc in archivos:
            nombre = arc.nombre_archivo.upper()
            tipo = arc.tipo_archivo.upper()
            if nombre.startswith("RECIPE_"): continue 
                
            if "EGRESO" in nombre:
                categorias["🏥 Informes de Egreso"].append(arc)
            elif any(x in nombre for x in ["POSTOP", "POST-OP", "POST_OP", "NOTA OPERATORIA", "NOTA_OPERATORIA", "NOTA-OPERATORIA", "NOTAOPERATORIA"]):
                categorias["😷 Informes Post-Operatorios"].append(arc)
            elif any(x in nombre for x in ["ORDENEXAMEN", "EXAMEN", "LABORATORIO", "BIOPSIA", "ANALISIS", "RESULTADO", "RESULTADOS"]):
                categorias["🔬 Exámenes"].append(arc)
            elif "HISTORIA" in nombre or "CONSULTA" in nombre:
                categorias["📜 Historias Clínicas"].append(arc)
            elif "INFORME" in nombre:
                categorias["📄 Informes Médicos"].append(arc)
            elif "CONSENTIMIENTO" in nombre:
                categorias["⚖️ Consentimientos Legales"].append(arc)
            elif tipo in ["JPG", "JPEG", "PNG"] or any(x in nombre for x in ["IMAGEN", "ANEXO", "RADIOGRAFIA", "ECOGRAFIA", "FOTO"]):
                categorias["🖼️ Imágenes y Anexos"].append(arc)
            else:
                categorias["📎 Otros Documentos"].append(arc)
            
        total_filas = sum(1 for cat, arts in categorias.items() if arts) + sum(len(arts) for arts in categorias.values())
        self.tabla_archivos.setRowCount(total_filas)
        
        bg_folder = QColor("#2a2d32" if tema.modo_actual == "oscuro" else "#dce4ea")
        txt_folder = QColor("#52d5bc" if tema.modo_actual == "oscuro" else "#2c3e50")
        
        if tema.modo_actual == "oscuro":
            c_pdf = QColor("#3D2E2E") 
            c_doc = QColor("#243343") 
            c_img = QColor("#223828") 
            c_def = QColor("#2d3136") 
        else:
            c_pdf = QColor(255, 242, 242); c_doc = QColor(242, 248, 255); c_img = QColor(242, 255, 242); c_def = QColor(255, 255, 255)

        fila_actual = 0
        for cat_nombre, lista_archivos in categorias.items():
            if not lista_archivos: continue
            
            it_titulo = QTableWidgetItem(cat_nombre)
            it_titulo.setBackground(QBrush(bg_folder))
            it_titulo.setForeground(QBrush(txt_folder)) 
            font = it_titulo.font(); font.setBold(True); font.setPointSize(11); it_titulo.setFont(font)
            it_titulo.setFlags(Qt.ItemIsEnabled) 
            
            self.tabla_archivos.setItem(fila_actual, 0, it_titulo)
            self.tabla_archivos.setSpan(fila_actual, 0, 1, 3) 
            fila_actual += 1
            
            for arc in lista_archivos:
                it_nombre = QTableWidgetItem("   " + arc.nombre_archivo)
                it_tipo = QTableWidgetItem(arc.tipo_archivo)
                it_fecha = QTableWidgetItem(arc.fecha_subida.strftime("%d/%m/%Y"))
                
                tipo = arc.tipo_archivo.upper()
                color_celda = c_def
                if tipo == "PDF": color_celda = c_pdf
                elif tipo in ["DOC", "DOCX"]: color_celda = c_doc
                elif tipo in ["JPG", "JPEG", "PNG"]: color_celda = c_img
                
                for it in [it_nombre, it_tipo, it_fecha]:
                    it.setBackground(QBrush(color_celda))
                    it.setFlags(it.flags() ^ Qt.ItemIsEditable)

                self.tabla_archivos.setItem(fila_actual, 0, it_nombre)
                self.tabla_archivos.setItem(fila_actual, 1, it_tipo)
                self.tabla_archivos.setItem(fila_actual, 2, it_fecha)
                it_nombre.setData(Qt.UserRole, arc.id) 
                fila_actual += 1
        db.close()

    def cargar_arbol(self, paciente):
        self.arbol_historial.clear()
        
        c_ant = QColor("#ef5350")    
        c_cons = QColor("#3498DB")   
        c_inf = QColor("#31d57e")    
        c_egr = QColor("#8e44ad")    
        c_post = QColor("#c0392b")   
        c_leg = QColor("#e67e22")    

        item_ant = QTreeWidgetItem(self.arbol_historial, ["📋 ANTECEDENTES GENERALES"])
        item_ant.setData(0, Qt.UserRole, {"tipo": "ANTECEDENTES", "id": paciente.id})
        item_ant.setForeground(0, QBrush(c_ant))
        font_ant = item_ant.font(0); font_ant.setBold(True); item_ant.setFont(0, font_ant)
        
        consultas_cronologicas = sorted(paciente.consultas, key=lambda x: x.fecha_consulta)
        etiquetas_consulta = {}
        for i, c in enumerate(consultas_cronologicas):
            if i == 0:
                etiquetas_consulta[c.id] = "Historia de primera"
            else:
                etiquetas_consulta[c.id] = f"Consulta #{i+1}"
        
        cat_cons = QTreeWidgetItem(self.arbol_historial, ["🩺 CONSULTAS"])
        cat_cons.setData(0, Qt.UserRole, {"tipo": "CATEGORIA_CONSULTA"})
        cat_cons.setForeground(0, QBrush(c_cons))
        font_cons = cat_cons.font(0); font_cons.setBold(True); cat_cons.setFont(0, font_cons)
        for c in sorted(paciente.consultas, key=lambda x: x.fecha_consulta, reverse=True):
            nombre_label = etiquetas_consulta[c.id]
            item = QTreeWidgetItem(cat_cons, [f"📅 {nombre_label} - {c.fecha_consulta.strftime('%d/%m/%Y')}"])
            item.setData(0, Qt.UserRole, {"tipo": "CONSULTA", "id": c.id})
        cat_cons.setExpanded(True)
        
        cat_info = QTreeWidgetItem(self.arbol_historial, ["📄 INFORMES MÉDICOS"])
        cat_info.setData(0, Qt.UserRole, {"tipo": "CATEGORIA_INFORME"})
        cat_info.setForeground(0, QBrush(c_inf))
        font_inf = cat_info.font(0); font_inf.setBold(True); cat_info.setFont(0, font_inf)
        for f in sorted(paciente.informes, key=lambda x: x.fecha, reverse=True):
            item = QTreeWidgetItem(cat_info, [f"📝 Informe - {f.fecha.strftime('%d/%m/%Y')}"])
            item.setData(0, Qt.UserRole, {"tipo": "INFORME", "id": f.id})

        cat_egreso = QTreeWidgetItem(self.arbol_historial, ["🏥 INFORMES DE EGRESO"])
        cat_egreso.setData(0, Qt.UserRole, {"tipo": "CATEGORIA_EGRESO"})
        cat_egreso.setForeground(0, QBrush(c_egr))
        font_egr = cat_egreso.font(0); font_egr.setBold(True); cat_egreso.setFont(0, font_egr)
        for e in sorted(paciente.egresos, key=lambda x: x.fecha, reverse=True):
            item = QTreeWidgetItem(cat_egreso, [f"🏥 Egreso - {e.fecha.strftime('%d/%m/%Y')}"])
            item.setData(0, Qt.UserRole, {"tipo": "EGRESO", "id": e.id})
            
        cat_postop = QTreeWidgetItem(self.arbol_historial, ["😷 INFORMES POST-OPERATORIOS"])
        cat_postop.setData(0, Qt.UserRole, {"tipo": "CATEGORIA_POSTOP"})
        cat_postop.setForeground(0, QBrush(c_post))
        font_post = cat_postop.font(0); font_post.setBold(True); cat_postop.setFont(0, font_post)
        for p_op in sorted(paciente.notas_operatorias, key=lambda x: x.fecha, reverse=True):
            item = QTreeWidgetItem(cat_postop, [f"😷 Nota-Op - {p_op.fecha.strftime('%d/%m/%Y')}"])
            item.setData(0, Qt.UserRole, {"tipo": "POST_OP", "id": p_op.id})

        cat_cons_legales = QTreeWidgetItem(self.arbol_historial, ["⚖️ CONSENTIMIENTOS"])
        cat_cons_legales.setData(0, Qt.UserRole, {"tipo": "CATEGORIA_CONSENTIMIENTO"})
        cat_cons_legales.setForeground(0, QBrush(c_leg))
        font_leg = cat_cons_legales.font(0); font_leg.setBold(True); cat_cons_legales.setFont(0, font_leg)
        for cons in sorted(paciente.consentimientos, key=lambda x: x.fecha, reverse=True):
            item = QTreeWidgetItem(cat_cons_legales, [f"✍️ Consent. - {cons.fecha.strftime('%d/%m/%Y')}"])
            item.setData(0, Qt.UserRole, {"tipo": "CONSENTIMIENTO", "id": cons.id})

    def reposicionar_boton(self, event):
        if event is not None and hasattr(self, '_visor_resize_original'):
            self._visor_resize_original(event)
        y = self.visor_lectura.height() - 35 - 20 
        for btn_flotante in [self.btn_generar_pdf_historia, self.btn_generar_pdf_informe, self.btn_generar_pdf_consentimiento, self.btn_generar_pdf_egreso, self.btn_generar_pdf_postop]:
            btn_flotante.move(self.visor_lectura.width() - btn_flotante.width() - 20, y)

    def mostrar_detalle_evento(self, item, col):
        data = item.data(0, Qt.UserRole)
        if not data: return
        
        db = SessionLocal()
        try:
            self.btn_generar_pdf_historia.hide()
            self.btn_generar_pdf_informe.hide()
            self.btn_generar_pdf_consentimiento.hide()
            self.btn_generar_pdf_egreso.hide()
            self.btn_generar_pdf_postop.hide()

            is_dark = (tema.modo_actual == "oscuro")
            c_html_bg = "#2f3136" if is_dark else "#ffffff"
            c_html_txt = "#ffffff" if is_dark else "#1c1c1c"
            c_html_card = "#424549" if is_dark else "#f9f9f9"
            c_html_border = "#4f545c" if is_dark else "#ccc"
            
            c_html_ant = "#ef5350" if is_dark else "#1c1c1c"
            c_html_cons = "#93F6E3" if is_dark else "#1c1c1c" 
            c_html_inf = "#31d57e" if is_dark else "#1c1c1c"
            c_html_egr = "#8e44ad" if is_dark else "#1c1c1c"
            c_html_post = "#ef5350" if is_dark else "#1c1c1c"
            
            # --- 1. CASO: ANTECEDENTES ---
            if data["tipo"] == "ANTECEDENTES":
                p = db.query(Paciente).get(data["id"])
                if p:
                    ant = p.antecedentes
                    html = f"""
                    <div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>
                        <h1 style='color: {c_html_ant}; border-bottom: 2px solid {"#ef5350" if is_dark else "#1c1c1c"}; padding-bottom: 5px; font-size: 22px;'>FICHA DE ANTECEDENTES</h1>
                        
                        <h3 style='color: {c_html_ant}; margin-top: 15px;'>⚠️ Alergias</h3>
                        <p style='font-size: 15px; background: {c_html_card}; padding: 8px; border-radius: 4px;'>{ant.alergias if ant and ant.alergias else 'No registradas.'}</p>
                        
                        <h3 style='color: {c_html_ant};'>📋 Personales / Patológicos</h3>
                        <p style='font-size: 15px; background: {c_html_card}; padding: 8px; border-radius: 4px;'>{ant.personales if ant and ant.personales else 'Sin datos.'}</p>
                        
                        <h3 style='color: {c_html_ant};'>👥 Familiares</h3>
                        <p style='font-size: 15px; background: {c_html_card}; padding: 8px; border-radius: 4px;'>{ant.familiares if ant and ant.familiares else 'Sin datos.'}</p>
                        
                        <h3 style='color: {c_html_ant};'>✂️ Operaciones Realizadas</h3>
                        <p style='font-size: 15px; background: {c_html_card}; padding: 8px; border-radius: 4px;'>{ant.operaciones_realizadas if ant and ant.operaciones_realizadas else 'Sin datos.'}</p>

                        <h3 style='color: {c_html_ant};'>🧩 Hábitos Psicobiológicos</h3>
                        <ul style='font-size: 15px; background: {c_html_card}; padding: 10px 25px; border-radius: 4px; line-height: 1.6;'>
                            <li><b>🚬 Fuma:</b> {ant.habito_fuma if ant and ant.habito_fuma else 'No aplica'}</li>
                            <li><b>🍺 Bebe:</b> {ant.habito_bebe if ant and ant.habito_bebe else 'No aplica'}</li>
                            <li><b>Otros Hábitos:</b> {ant.otros_habitos if ant and ant.otros_habitos else 'No aplica'}</li>
                        </ul>

                        <h3 style='color: {c_html_ant};'>🩺 Examen Funcional</h3>
                        <p style='font-size: 15px; background: {c_html_card}; padding: 8px; border-radius: 4px;'>{ant.examen_funcional if ant and ant.examen_funcional else 'Sin datos.'}</p>
                    </div>
                    """
                    self.visor_lectura.setHtml(html)

            # --- 2. CASO: CONSULTA ---
            elif data["tipo"] == "CONSULTA":
                c = db.query(Consulta).get(data["id"])
                if c:
                    self.id_consulta_actual = c.id
                    self.btn_generar_pdf_historia.show()
                    self.reposicionar_boton(None)

                    def row(label, value):
                        if value is None: return ""
                        v_str = str(value).strip().lower()
                        if v_str in ["no aplica", "none", "", "false"]: return ""
                        etiquetas_con_cero = ["Gestas", "Abortos", "Emb. Ectópico", "Partos", "Cesáreas"]
                        if v_str in ["0", "0.0"] and label not in etiquetas_con_cero: return ""
                        return f"<tr><td style='padding:6px; width:35%; border-bottom: 1px solid {c_html_border}; color:{c_html_txt};'><b>{label}:</b></td><td style='padding:6px; border-bottom: 1px solid {c_html_border}; color:{c_html_txt};'>{value}</td></tr>"

                    html_nota_evolutiva = ""
                    if c.nota_evolutiva and str(c.nota_evolutiva).strip().lower() not in ["no aplica", "none", "", "false"]:
                        html_nota_evolutiva = f"<p style='margin: 5px 0;'><b>Nota Evolutiva:</b> {c.nota_evolutiva}</p>"

                    f_str = c.fecha_consulta.strftime('%d/%m/%Y') if c.fecha_consulta else "S/F"
                    html = f"<div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>"
                    html += f"""
                        <h1 style='color: {c_html_cons}; border-bottom: 2px solid {"#3498DB" if is_dark else "#1c1c1c"}; margin-bottom:5px; font-size:22px;'>Historia Médica - {f_str}</h1>
                        <p style='font-size: 14px; margin-bottom:15px; color:#888;'><b>Edad en consulta:</b> {c.edad_paciente if c.edad_paciente else 'N/R'} años</p>
                        
                        <div style='background-color: {c_html_card}; padding: 12px; border-left: 5px solid #3498DB; border-radius:4px; margin-bottom: 15px; color: {c_html_txt};'>
                            <h3 style='margin-top:0; color: {c_html_cons}; font-size:16px;'>📌 Motivo y Evolución</h3>
                            <p style='margin: 5px 0;'><b>Motivo de Consulta:</b> {c.motivo_consulta if hasattr(c, 'motivo_consulta') and c.motivo_consulta else 'N/R'}</p>
                            <p style='margin: 5px 0;'><b>Enfermedad Actual:</b> {c.enfermedad_actual}</p>
                            <p style='margin: 5px 0;'><b>Impresión Diagnóstica:</b> {c.impresion_diagnostica if hasattr(c, 'impresion_diagnostica') and c.impresion_diagnostica else 'N/R'}</p>
                            <p style='margin: 5px 0;'><b>Diagnóstico:</b> {c.diagnostico if hasattr(c, 'diagnostico') and c.diagnostico else 'N/R'}</p>
                            <p style='margin: 5px 0;'><b>Estudios Indicados:</b> {c.estudios_indicados if hasattr(c, 'estudios_indicados') and c.estudios_indicados else 'N/R'}</p>
                            {html_nota_evolutiva}
                        </div>
                    """

                    html += f"""
                        <h3 style='color: {c_html_cons}; border-bottom: 1px solid {c_html_border}; font-size:16px; margin-top:20px;'>🩺 Signos Vitales</h3>
                        <table width='100%' style='border-collapse: collapse; margin-bottom:15px;'>
                            {row("Peso", f"{c.peso} kg") if c.peso and c.peso > 0 else ""}
                            {row("Altura", f"{c.altura} m") if c.altura and c.altura > 0 else ""}
                            {row("IMC", f"{c.imc:.2f}") if c.imc and c.imc > 0 else ""}
                            {row("Tensión Arterial", c.tension_arterial)}
                            {row("Pulso", f"{c.pulso} ppm") if c.pulso and c.pulso > 0 else ""}
                        </table>
                    """

                    paciente = c.paciente
                    if paciente and paciente.antecedentes:
                        ant = paciente.antecedentes
                        hab_html = row("Fuma", ant.habito_fuma) + row("Bebe", ant.habito_bebe) + row("Otros", ant.otros_habitos) + row("Ex. Funcional", ant.examen_funcional)
                        if hab_html:
                            html += f"<h3 style='color: {c_html_cons}; border-bottom: 1px solid {c_html_border}; font-size:16px;'>🚬 Hábitos y Examen Funcional</h3><table width='100%' style='border-collapse: collapse; margin-bottom:15px;'>{hab_html}</table>"

                    ef_gen = (row("Piel", c.piel) + row("Ojos", c.ojos) + row("Oídos", c.oidos) + 
                              row("Orofaringe", c.orofaringe) + row("Tiroides", c.tiroides) + 
                              row("Axilas", c.axilas) + row("Supraclaviculares", c.supraclaviculares) + 
                              row("Abdomen", c.abdomen) + row("Lumbar", c.lumbar) +
                              row("Neurológico", getattr(c, 'neurologico', '')) + 
                              row("Otros", getattr(c, 'otros_examen_fisico', '')))
                    if ef_gen:
                        html += f"<h3 style='color: {c_html_cons}; border-bottom: 1px solid {c_html_border}; font-size:16px;'>🔍 Examen Físico General</h3><table width='100%' style='border-collapse: collapse; margin-bottom:15px;'>{ef_gen}</table>"

                    esp_html = ""
                    es_mujer = paciente and paciente.genero and paciente.genero.strip().lower() in ["femenino", "mujer"]
                    if es_mujer:
                        esp_html += (row("Mamas", c.mamas) + row("Vulva", c.vulva) + row("Vagina", c.vagina) + 
                                     row("Cérvix", c.cervix) + row("Colposcopia", c.colposcopia) + row("Tacto R-V", c.tacto_recto_vaginal))
                        gin = db.query(GinecoObstetrico).filter(GinecoObstetrico.paciente_id == paciente.id).order_by(GinecoObstetrico.fecha_registro.desc()).first()
                        if gin:
                            incont = "Sí" if gin.incontinencia else "No"
                            esp_html += f"<tr><td colspan='2' style='background:{c_html_card}; color:{c_html_cons}; padding:8px; font-weight:bold; border-top:1px solid {c_html_border}; border-bottom:1px solid {c_html_border};'>Antecedentes Gineco-Obstétricos</td></tr>"
                            esp_html += (
                                row("Menarquia", gin.menarquia) + row("Gestas", gin.gestas) + 
                                row("Abortos", gin.abortos) + row("Emb. Ectópico", gin.embarazo_ectopico) +
                                row("Partos", gin.partos) + row("Cesáreas", gin.cesarea) + 
                                row("Menopausia", gin.menopausia) + row("Sangramiento", gin.sangramiento) +
                                row("Incontinencia", incont) + row("Flujo", gin.flujo) +
                                row("DIU", gin.diu) + row("ACO", gin.aco)
                            )
                    elif paciente:
                        esp_html += row("Pene/Testículos", c.pene_testiculos) + row("Próstata", c.prostata)

                    if esp_html:
                        html += f"<h3 style='color: {c_html_cons}; border-bottom: 1px solid {c_html_border}; font-size:16px;'>⚕️ Especializado</h3><table width='100%' style='border-collapse: collapse;'>{esp_html}</table>"

                    html += "<br><br><br><br></div>"
                    self.visor_lectura.setHtml(html)

            # --- 3. CASO: INFORME MÉDICO ---
            elif data["tipo"] == "INFORME":
                inf = db.query(InformeMedico).get(data["id"])
                if inf:
                    self.id_informe_actual = inf.id 
                    self.btn_generar_pdf_informe.show() 
                    self.reposicionar_boton(None)
                    html = f"""
                    <div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>
                        <h1 style='color: {c_html_inf}; border-bottom: 2px solid {c_html_inf}; font-size:22px; padding-bottom:5px;'>INFORME MÉDICO</h1>
                        <p style='color:#888;'><b>Fecha:</b> {inf.fecha.strftime('%d/%m/%Y')}</p>
                        <div style='padding: 15px; background: {c_html_card}; border: 1px solid {c_html_border}; border-radius:5px; white-space: pre-wrap; color:{c_html_txt}; font-size:15px; line-height:1.6;'>{inf.informe_escrito}</div>
                    </div>"""
                    self.visor_lectura.setHtml(html)
            
            # --- 4. CASO: EGRESO ---
            elif data["tipo"] == "EGRESO":
                e = db.query(InformeEgreso).get(data["id"])
                if e:
                    self.id_egreso_actual = e.id
                    self.btn_generar_pdf_egreso.show()
                    self.reposicionar_boton(None)
                    
                    def f_val(val):
                        return val if val and str(val).strip().lower() not in ["no aplica", "none", "", "n/a"] else "No registrado"

                    html = f"""
                    <div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>
                        <h1 style='color: {c_html_egr}; border-bottom: 2px solid {c_html_egr}; font-size:22px; padding-bottom:5px;'>INFORME DE EGRESO</h1>
                        <p style='color:#888;'><b>Fecha de Egreso:</b> {e.fecha.strftime('%d/%m/%Y') if e.fecha else 'S/F'}</p>
                        <div style='padding: 15px; background: {c_html_card}; border-left: 5px solid {c_html_egr}; border-radius:4px; line-height:1.5; font-size:15px;'>
                            <h3 style='color: {c_html_egr}; margin-top: 0;'>Resumen del Egreso</h3>
                            <p>{f_val(e.resumen_egreso).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Evaluación</h3>
                            <p>{f_val(e.evaluacion).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Examen Físico</h3>
                            <p>{f_val(e.examen_fisico).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Paraclínicos</h3>
                            <p>{f_val(e.paraclinicos).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Diagnóstico de Egreso</h3>
                            <p>{f_val(e.diagnostico_egreso).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Procedimiento Realizado</h3>
                            <p>{f_val(e.procedimiento_realizado).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_egr};'>Plan de Manejo</h3>
                            <p>{f_val(e.plan_manejo).replace(chr(10), '<br>')}</p>
                        </div><br><br><br>
                    </div>"""
                    self.visor_lectura.setHtml(html)

            # --- 5. CASO: POST-OPERATORIO ---
            elif data["tipo"] == "POST_OP":
                p_op = db.query(NotaOperatoria).get(data["id"])
                if p_op:
                    self.id_postop_actual = p_op.id
                    self.btn_generar_pdf_postop.show()
                    self.reposicionar_boton(None)
                    
                    def f_val(val):
                        return val if val and str(val).strip().lower() not in ["no aplica", "none", "", "n/a"] else "No registrado"

                    html = f"""
                    <div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>
                        <h1 style='color: {c_html_post}; border-bottom: 2px solid {c_html_post}; font-size:22px; padding-bottom:5px;'>INFORME POST-OPERATORIO</h1>
                        <p style='color:#888;'><b>Fecha Quirúrgica:</b> {p_op.fecha.strftime('%d/%m/%Y') if p_op.fecha else 'S/F'}</p>
                        <div style='padding: 15px; background: {c_html_card}; border-left: 5px solid {c_html_post}; border-radius:4px; line-height:1.5; font-size:15px;'>
                            <h3 style='color: {c_html_post}; margin-top: 0;'>Diagnóstico Pre-operatorio</h3>
                            <p>{f_val(p_op.diagnostico_preoperatorio).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Cirugía Realizada</h3>
                            <p>{f_val(p_op.cirugia_realizada).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Diagnóstico Post-operatorio</h3>
                            <p>{f_val(p_op.diagnostico_postoperatorio).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Descripción detallada de la intervención</h3>
                            <p>{f_val(p_op.descripcion_intervencion).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Hallazgos</h3>
                            <p>{f_val(p_op.hallazgos).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Biopsia</h3>
                            <p>{f_val(p_op.biopsia).replace(chr(10), '<br>')}</p>
                            
                            <h3 style='color: {c_html_post};'>Plan de Manejo</h3>
                            <p>{f_val(p_op.plan_manejo).replace(chr(10), '<br>')}</p>
                        </div><br><br><br>
                    </div>"""
                    self.visor_lectura.setHtml(html)

            # --- 6. CASO: CONSENTIMIENTO LEGAL ---
            elif data["tipo"] == "CONSENTIMIENTO":
                cons = db.query(ConsentimientoCirugia).get(data["id"])
                if cons:
                    self.id_consentimiento_actual = cons.id
                    self.btn_generar_pdf_consentimiento.show()
                    self.reposicionar_boton(None)
                    
                    paciente = cons.paciente
                    doctor = db.query(PerfilDoctor).first()
                    from ui_consentimientos import PLANTILLA_BASE
                    plantilla = doctor.plantilla_consentimiento if doctor and doctor.plantilla_consentimiento else PLANTILLA_BASE
                    
                    texto = plantilla
                    texto = texto.replace("[PACIENTE]", f"<b>{paciente.nombre_completo.upper()}</b>")
                    texto = texto.replace("[CEDULA_PACIENTE]", f"<b>{paciente.cedula}</b>")
                    texto = texto.replace("[DOCTOR]", f"<b>{doctor.nombre_doctor.upper()}</b>" if doctor else "")
                    texto = texto.replace("[CEDULA_DOCTOR]", f"<b>{doctor.cedula_doctor}</b>" if doctor else "")
                    texto = texto.replace("[ESPECIALIDAD]", f"<b>{doctor.especialidades}</b>" if doctor else "")
                    texto = texto.replace("[MSDS]", f"<b>{doctor.matricula_msds}</b>" if doctor else "")
                    texto = texto.replace("[INTERVENCION]", f"<b>{cons.intervencion.upper()}</b>")
                    texto = texto.replace("[DIAGNOSTICO]", f"<b>{cons.diagnostico.upper()}</b>")
                    texto = texto.replace("[RIESGOS]", f"<b>{cons.riesgos_especificos.upper()}</b>")
                    
                    txt_testigo = f"<br><br>Actuando en representación de mi familiar <b>{cons.familiar_nombre}</b> (C.I. {cons.familiar_cedula})." if cons.familiar_nombre else ""
                    texto = texto.replace("[BLOQUE_TESTIGO]", txt_testigo)
                    
                    c_pergamino = "#3a3630" if is_dark else "#fdfae6"
                    c_p_border = tema.BORDE_SUAVE if is_dark else "#e67e22"
                    
                    html = f"""
                    <div style='font-family: Arial, sans-serif; background-color: {c_html_bg}; color: {c_html_txt}; padding: 10px;'>
                        <h1 style='color: #ffa726; border-bottom: 2px solid #ffa726; font-size:20px; padding-bottom:5px;'>CONSENTIMIENTO INFORMADO PARA CIRUGÍA</h1>
                        <p style='color:#888;'><b>Fecha de Registro:</b> {cons.fecha.strftime('%d/%m/%Y')}</p>
                        <div style='background-color: {c_pergamino}; padding: 20px; border: 1px solid {c_p_border}; border-radius:4px; line-height: 1.6; font-family: "Times New Roman", serif; font-size: 15px; color:{c_html_txt};'>
                            {texto.replace(chr(10), '<br>')}
                        </div>
                    </div>"""
                    self.visor_lectura.setHtml(html)
        except Exception as e:
            print(f"❌ Error crítico en el visualizador: {e}")
        finally:
            db.close()

    def imprimir_consulta_seleccionada(self, formato="pdf"):
        if not hasattr(self, 'id_consulta_actual'): return
        db = SessionLocal()
        try:
            consulta = db.query(Consulta).get(self.id_consulta_actual)
            paciente = consulta.paciente
            doctor = db.query(PerfilDoctor).first()
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join(self.ruta_almacenamiento, f"{nombre_limpio}_{paciente.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato == "docx" else ".pdf"
            base_name = f"HISTORIA_{nombre_limpio}_{consulta.fecha_consulta.strftime('%Y-%m-%d')}"
            ruta_doc = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_doc):
                ruta_doc = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
            
            filename = os.path.basename(ruta_doc)
            
            MotorImpresion.generar_pdf_historia(doctor, paciente, consulta, ruta_doc, formato=formato)
            
            if not db.query(ArchivoPaciente).filter_by(ruta_archivo=ruta_doc).first():
                db.add(ArchivoPaciente(paciente_id=paciente.id, nombre_archivo=filename, ruta_archivo=ruta_doc, tipo_archivo=formato.upper()))
                db.commit(); self.actualizar_tabla_archivos()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta_doc)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el documento de la historia médica: {e}", QMessageBox.Ok, self)
        finally: db.close()

    def imprimir_informe_seleccionado(self, formato="pdf"):
        if not hasattr(self, 'id_informe_actual'): return
        db = SessionLocal()
        try:
            inf = db.query(InformeMedico).get(self.id_informe_actual)
            paciente = inf.paciente
            doctor = db.query(PerfilDoctor).first()
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join(self.ruta_almacenamiento, f"{nombre_limpio}_{paciente.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato == "docx" else ".pdf"
            base_name = f"INFORME_{nombre_limpio}_{inf.fecha.strftime('%Y-%m-%d')}"
            ruta_doc = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_doc):
                ruta_doc = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
            
            filename = os.path.basename(ruta_doc)
            
            MotorImpresion.generar_pdf_informe(doctor, paciente, inf.informe_escrito, ruta_doc, formato=formato)
            
            if not db.query(ArchivoPaciente).filter_by(ruta_archivo=ruta_doc).first():
                db.add(ArchivoPaciente(paciente_id=paciente.id, nombre_archivo=filename, ruta_archivo=ruta_doc, tipo_archivo=formato.upper()))
                db.commit(); self.actualizar_tabla_archivos()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta_doc)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el informe médico: {e}", QMessageBox.Ok, self)
        finally: db.close()

    def imprimir_consentimiento_seleccionado(self, formato="pdf"):
        if not hasattr(self, 'id_consentimiento_actual'): return
        db = SessionLocal()
        try:
            cons = db.query(ConsentimientoCirugia).get(self.id_consentimiento_actual)
            paciente = cons.paciente
            doctor = db.query(PerfilDoctor).first()
            
            from ui_consentimientos import PLANTILLA_BASE
            plantilla = doctor.plantilla_consentimiento if doctor and doctor.plantilla_consentimiento else PLANTILLA_BASE
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join(self.ruta_almacenamiento, f"{nombre_limpio}_{paciente.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato == "docx" else ".pdf"
            base_name = f"CONSENTIMIENTO_{nombre_limpio}_{cons.fecha.strftime('%Y-%m-%d')}"
            ruta_doc = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_doc):
                ruta_doc = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
                
            filename = os.path.basename(ruta_doc)
            
            MotorImpresion.generar_pdf_consentimiento(doctor, paciente, cons, plantilla, ruta_doc, formato=formato)
            
            if not db.query(ArchivoPaciente).filter_by(ruta_archivo=ruta_doc).first():
                db.add(ArchivoPaciente(paciente_id=paciente.id, nombre_archivo=filename, ruta_archivo=ruta_doc, tipo_archivo=formato.upper()))
                db.commit(); self.actualizar_tabla_archivos()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta_doc)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el consentimiento: {e}", QMessageBox.Ok, self)
        finally: db.close()

    def imprimir_egreso_seleccionado(self, formato="pdf"):
        if not hasattr(self, 'id_egreso_actual'): return
        db = SessionLocal()
        try:
            e = db.query(InformeEgreso).get(self.id_egreso_actual)
            paciente = e.paciente
            doctor = db.query(PerfilDoctor).first()
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join(self.ruta_almacenamiento, f"{nombre_limpio}_{paciente.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato == "docx" else ".pdf"
            base_name = f"EGRESO_{nombre_limpio}_{e.fecha.strftime('%Y-%m-%d')}"
            ruta_doc = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_doc):
                ruta_doc = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
                
            filename = os.path.basename(ruta_doc)
            
            MotorImpresion.generar_pdf_egreso(doctor, paciente, e, ruta_doc, formato=formato)
            
            if not db.query(ArchivoPaciente).filter_by(ruta_archivo=ruta_doc).first():
                db.add(ArchivoPaciente(paciente_id=paciente.id, nombre_archivo=filename, ruta_archivo=ruta_doc, tipo_archivo=formato.upper()))
                db.commit(); self.actualizar_tabla_archivos()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta_doc)))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo generar el informe de egreso: {exc}", QMessageBox.Ok, self)
        finally: db.close()

    def imprimir_postop_seleccionado(self, formato="pdf"):
        if not hasattr(self, 'id_postop_actual'): return
        db = SessionLocal()
        try:
            p_op = db.query(NotaOperatoria).get(self.id_postop_actual)
            paciente = p_op.paciente
            doctor = db.query(PerfilDoctor).first()
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', paciente.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join(self.ruta_almacenamiento, f"{nombre_limpio}_{paciente.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato == "docx" else ".pdf"
            base_name = f"POSTOP_{nombre_limpio}_{p_op.fecha.strftime('%Y-%m-%d')}"
            ruta_doc = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_doc):
                ruta_doc = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
                
            filename = os.path.basename(ruta_doc)
            
            MotorImpresion.generar_pdf_postop(doctor, paciente, p_op, ruta_doc, formato=formato)
            
            if not db.query(ArchivoPaciente).filter_by(ruta_archivo=ruta_doc).first():
                db.add(ArchivoPaciente(paciente_id=paciente.id, nombre_archivo=filename, ruta_archivo=ruta_doc, tipo_archivo=formato.upper()))
                db.commit(); self.actualizar_tabla_archivos()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta_doc)))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo generar la nota post-operatoria: {exc}", QMessageBox.Ok, self)
        finally: db.close()
             
    def abrir_archivo(self):
        fila = self.tabla_archivos.currentRow()
        if fila == -1: return
        it_first = self.tabla_archivos.item(fila, 0)
        if not it_first: return
        id_arc = it_first.data(Qt.UserRole)
        if not id_arc: return 
        db = SessionLocal()
        arc = db.query(ArchivoPaciente).get(id_arc)
        if arc and os.path.exists(arc.ruta_archivo):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(arc.ruta_archivo)))
        db.close()

    def eliminar_adjunto(self):
        fila = self.tabla_archivos.currentRow()
        if fila == -1: return
        it_first = self.tabla_archivos.item(fila, 0)
        if not it_first: return
        id_arc = it_first.data(Qt.UserRole)
        if not id_arc: return 
        
        box = QMessageBox(QMessageBox.Question, "Eliminar Archivo", "¿Eliminar adjunto?\nNota: Se eliminará la copia física local.", QMessageBox.Yes | QMessageBox.No, self)
        box.setStyleSheet(tema.ESTILO_VENTANA)
        if box.exec() == QMessageBox.No: return
        
        db = SessionLocal()
        arc = db.query(ArchivoPaciente).get(id_arc)
        if arc:
            if os.path.exists(arc.ruta_archivo): os.remove(arc.ruta_archivo)
            db.delete(arc); db.commit(); self.actualizar_tabla_archivos()
        db.close()

    def verificar_cambios_historial(self):
        db = SessionLocal()
        try:
            pacientes_db = db.query(Paciente.id, Paciente.cedula, Paciente.nombre_completo).all()
            nueva_huella = str(pacientes_db)
            
            if self.huella_pacientes != nueva_huella:
                if self.huella_pacientes != "":
                    self.actualizar_lista()
                
                self.huella_pacientes = nueva_huella
        except Exception:
            pass  
        finally:
            db.close()

    def actualizar_lista(self):
        db = SessionLocal()
        filtro = self.in_buscador.text().strip()
        pacientes = db.query(Paciente).filter(
            (Paciente.nombre_completo.ilike(f"%{filtro}%")) | 
            (Paciente.cedula.ilike(f"%{filtro}%"))
        ).all()
        self.tabla_pacientes.setRowCount(len(pacientes))
        for i, p in enumerate(pacientes):
            self.tabla_pacientes.setItem(i, 0, QTableWidgetItem(p.cedula))
            self.tabla_pacientes.setItem(i, 1, QTableWidgetItem(p.nombre_completo))
        db.close()