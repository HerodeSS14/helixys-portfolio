from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, 
                             QCheckBox, QDateEdit, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QButtonGroup, 
                             QRadioButton, QGridLayout, QFormLayout, QScrollArea, QSizePolicy, QToolButton)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIntValidator, QPixmap, QColor
from database import SessionLocal
from models import Paciente, PerfilDoctor
import os
from datetime import datetime
from estilos import tema  # Importación del motor de diseño centralizado

# ========================================================
# CLASE PERSONALIZADA: INPUT DE PRECIO ESTIVO PUNTO DE VENTA
# ========================================================
class InputPrecioPOS(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._valor_centavos = 0  
        self.setAlignment(Qt.AlignRight)
        self.setText("0.00")
        # Estilo base del input POS adaptado a las variables del sistema
        self.setStyleSheet(f"border:none; background:transparent; font-size:15px; padding-right:10px; font-weight: bold; color: {tema.TEXTO_MAIN};")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            self._valor_centavos = self._valor_centavos // 10
            self.setText(f"{self._valor_centavos / 100:.2f}")
        elif event.key() == Qt.Key_Delete:
            self._valor_centavos = 0
            self.setText("0.00")
        elif event.text().isdigit():
            digito = int(event.text())
            if self._valor_centavos < 100000000: 
                self._valor_centavos = (self._valor_centavos * 10) + digito
                self.setText(f"{self._valor_centavos / 100:.2f}")
        elif event.key() in (Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Enter, Qt.Key_Return):
            super().keyPressEvent(event)


class PantallaFactura(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        
        # Seteo de la ventana base adaptable
        self.setStyleSheet(tema.ESTILO_VENTANA)
        
        # ========================================================
        # CONTENEDOR CON SCROLL GENERAL
        # ========================================================
        layout_base = QVBoxLayout(self)
        layout_base.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) 
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        self.lienzo = QWidget()
        layout_principal = QVBoxLayout(self.lienzo)
        layout_principal.setContentsMargins(25, 25, 25, 25)
        layout_principal.setSpacing(20)

        # ========================================================
        # 1. MEMBRETE SUPERIOR OPTIMIZADO (70% AL CENTRO)
        # ========================================================
        self.frame_membrete = QFrame()
        self.frame_membrete.setMinimumHeight(150) 
        self.frame_membrete.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay_membrete = QHBoxLayout(self.frame_membrete)
        lay_membrete.setContentsMargins(15, 15, 15, 15)
        lay_membrete.setSpacing(10)

        # Lado Izquierdo - Logo reducido
        lay_logo = QVBoxLayout()
        lay_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo_imagen = QLabel()
        self.lbl_logo_imagen.setFixedSize(100, 80)
        self.lbl_logo_imagen.setAlignment(Qt.AlignCenter)
        self.lbl_logo_imagen.setText("<span style='color: #94a3b8; font-size: 40px;'>🖾</span>")
        
        self.lbl_clinica_nombre = QLabel("<b>CENTRO MÉDICO</b>")
        self.lbl_clinica_nombre.setAlignment(Qt.AlignCenter)
        self.lbl_clinica_nombre.setStyleSheet("font-size: 13px; font-weight: bold; border: none; background: transparent;")
        
        lay_logo.addWidget(self.lbl_logo_imagen)
        lay_logo.addWidget(self.lbl_clinica_nombre)
        lay_membrete.addLayout(lay_logo, 15) 

        # Centro - EXPANSIÓN TOTAL (70%)
        lay_centro_doc = QVBoxLayout()
        lay_centro_doc.setSpacing(4)
        lay_centro_doc.setAlignment(Qt.AlignCenter)
        
        self.lbl_doc_nombre = QLabel("<h2>Especialista Médico</h2>")
        self.lbl_doc_nombre.setStyleSheet("font-family: 'Times New Roman'; font-style: italic; font-size: 26px; margin: 0; border: none; background: transparent;")
        self.lbl_doc_nombre.setAlignment(Qt.AlignCenter)
        self.lbl_doc_nombre.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.lbl_doc_especialidad = QLabel("ESPECIALIDAD MÉDICA")
        self.lbl_doc_especialidad.setAlignment(Qt.AlignCenter)
        self.lbl_doc_especialidad.setStyleSheet("font-size: 14px; color: #0284c7; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        self.lbl_doc_especialidad.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.lbl_doc_direccion = QLabel("Dirección del Consultorio Clínico...")
        self.lbl_doc_direccion.setWordWrap(True)
        self.lbl_doc_direccion.setAlignment(Qt.AlignCenter)
        self.lbl_doc_direccion.setStyleSheet("font-size: 13px; border: none; padding-left: 5px; padding-right: 5px; background: transparent;")
        self.lbl_doc_direccion.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.lbl_doc_registro = QLabel("MSDS: -- | C.I: --")
        self.lbl_doc_registro.setAlignment(Qt.AlignCenter)
        self.lbl_doc_registro.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        self.lbl_doc_registro.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.lbl_doc_tlf = QLabel("Contacto: --")
        self.lbl_doc_tlf.setAlignment(Qt.AlignCenter)
        self.lbl_doc_tlf.setStyleSheet("font-size: 13px; font-weight: bold; border: none; background: transparent;")
        self.lbl_doc_tlf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        lay_centro_doc.addWidget(self.lbl_doc_nombre)
        lay_centro_doc.addWidget(self.lbl_doc_especialidad)
        lay_centro_doc.addWidget(self.lbl_doc_direccion)
        lay_centro_doc.addWidget(self.lbl_doc_registro)
        lay_centro_doc.addWidget(self.lbl_doc_tlf)
        lay_membrete.addLayout(lay_centro_doc, 70) 

        # Lado Derecho - Ajustado (15%)
        lay_der = QVBoxLayout()
        lay_der.setSpacing(8)
        lay_der.setAlignment(Qt.AlignCenter)
        
        self.lbl_rif = QLabel("<b>RIF: --</b>")
        self.lbl_rif.setStyleSheet("font-size: 14px; font-weight: bold; border: none; background: transparent;")
        self.lbl_rif.setAlignment(Qt.AlignCenter)
        
        self.frame_fecha = QFrame()
        lay_f_box = QVBoxLayout(self.frame_fecha)
        lay_f_box.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_tit_f = QLabel("Fecha de Emisión")
        self.lbl_tit_f.setAlignment(Qt.AlignCenter)
        self.lbl_tit_f.setStyleSheet("font-size: 11px; font-weight: bold; border: none; background: transparent;")
        
        self.in_fecha_factura = QDateEdit(calendarPopup=True)
        self.in_fecha_factura.setDate(QDate.currentDate())
        self.in_fecha_factura.setAlignment(Qt.AlignCenter)
        
        # Expandir botones internos del calendario integrado por código
        cal_factura = self.in_fecha_factura.calendarWidget()
        if cal_factura:
            cal_factura.setMinimumSize(420, 300)
            for btn in cal_factura.findChildren(QPushButton) + cal_factura.findChildren(QToolButton):
                btn.setMinimumHeight(35)
                fuente = btn.font()
                fuente.setPointSize(14)
                fuente.setBold(True)
                btn.setFont(fuente)
        
        lay_f_box.addWidget(self.lbl_tit_f)
        lay_f_box.addWidget(self.in_fecha_factura)
        
        lay_der.addWidget(self.lbl_rif)
        lay_der.addWidget(self.frame_fecha)
        lay_membrete.addLayout(lay_der, 15) 

        layout_principal.addWidget(self.frame_membrete)

        # ========================================================
        # 2. NÚMEROS LEGALES
        # ========================================================
        self.frame_numeros = QFrame()
        self.frame_numeros.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay_num = QHBoxLayout(self.frame_numeros)
        lay_num.setContentsMargins(20, 15, 20, 15)
        
        self.in_num_control = QLineEdit()
        self.in_num_control.setReadOnly(True)
        self.in_num_control.setMinimumHeight(42) 
        self.in_num_control.setAlignment(Qt.AlignCenter)
        
        self.in_num_factura = QLineEdit()
        self.in_num_factura.setReadOnly(True)
        self.in_num_factura.setMinimumHeight(42)
        self.in_num_factura.setAlignment(Qt.AlignCenter)

        self.lbl_c = QLabel("<b>Nº de Control:</b>"); self.lbl_c.setStyleSheet("font-size: 15px; border:none; background: transparent;")
        self.lbl_f = QLabel("<b>Factura Nº:</b>"); self.lbl_f.setStyleSheet("font-size: 15px; border:none; background: transparent;")

        lay_num.addWidget(self.lbl_c)
        lay_num.addWidget(self.in_num_control)
        lay_num.addSpacing(60)
        lay_num.addWidget(self.lbl_f)
        lay_num.addWidget(self.in_num_factura)
        
        layout_principal.addWidget(self.frame_numeros)

        # ========================================================
        # 3. DATOS FISCALES DEL PACIENTE
        # ========================================================
        self.group_paciente = QFrame()
        self.group_paciente.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_paciente = QGridLayout(self.group_paciente)
        grid_paciente.setContentsMargins(20, 20, 20, 20)
        grid_paciente.setSpacing(15)

        self.in_nombre = QLineEdit(); self.in_nombre.setMinimumHeight(40)
        self.in_domicilio = QLineEdit(); self.in_domicilio.setMinimumHeight(40)
        self.in_cedula = QLineEdit(); self.in_cedula.setMinimumHeight(40)
        self.in_telefono = QLineEdit(); self.in_telefono.setMinimumHeight(40)
        
        self.combo_condiciones = QComboBox()
        self.combo_condiciones.addItems(["Contado", "Crédito a 15 días", "Crédito a 30 días", "Aseguradora"])
        self.combo_condiciones.setMinimumHeight(40)

        self.lbl_p_nom = QLabel("<b>Nombre / Razón Social:</b>")
        self.lbl_p_dom = QLabel("<b>Domicilio Fiscal:</b>")
        self.lbl_p_ced = QLabel("<b>RIF / C.I.:</b>")
        self.lbl_p_tlf = QLabel("<b>Teléfono:</b>")
        self.lbl_p_con = QLabel("<b>Condiciones:</b>")

        grid_paciente.addWidget(self.lbl_p_nom, 0, 0)
        grid_paciente.addWidget(self.in_nombre, 0, 1, 1, 5) 
        grid_paciente.addWidget(self.lbl_p_dom, 1, 0)
        grid_paciente.addWidget(self.in_domicilio, 1, 1, 1, 5) 
        grid_paciente.addWidget(self.lbl_p_ced, 2, 0)
        grid_paciente.addWidget(self.in_cedula, 2, 1, 1, 1)
        grid_paciente.addWidget(self.lbl_p_tlf, 2, 2)
        grid_paciente.addWidget(self.in_telefono, 2, 3, 1, 1)
        grid_paciente.addWidget(self.lbl_p_con, 2, 4)
        grid_paciente.addWidget(self.combo_condiciones, 2, 5, 1, 1)

        layout_principal.addWidget(self.group_paciente)

        # ========================================================
        # 4. TABLA DE CONCEPTOS
        # ========================================================
        self.lbl_tit_tabla = QLabel("<h3>🛒 Detalles de Cargos:</h3>")
        self.lbl_tit_tabla.setStyleSheet("border:none; background: transparent;")
        layout_principal.addWidget(self.lbl_tit_tabla)
        
        self.tabla_conceptos = QTableWidget(1, 3)
        self.tabla_conceptos.setHorizontalHeaderLabels(["Cant.", "Descripción del Servicio / Concepto", "Precio Unitario (Bs.)"])
        self.tabla_conceptos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla_conceptos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_conceptos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.tabla_conceptos.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla_conceptos.setMinimumHeight(150)
        
        self.configurar_fila_tabla(0)
        layout_principal.addWidget(self.tabla_conceptos)

        lay_ops_tabla = QHBoxLayout()
        self.btn_mas_fila = QPushButton("➕ Añadir Concepto")
        self.btn_mas_fila.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_mas_fila.setMinimumHeight(38)
        self.btn_mas_fila.clicked.connect(self.añadir_fila_concepto)
        lay_ops_tabla.addWidget(self.btn_mas_fila)
        lay_ops_tabla.addStretch()
        layout_principal.addLayout(lay_ops_tabla)

        # ========================================================
        # 5. PIE DE FACTURA
        # ========================================================
        self.frame_pie = QFrame()
        self.frame_pie.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay_pie = QHBoxLayout(self.frame_pie)
        lay_pie.setContentsMargins(25, 25, 25, 25)
        lay_pie.setSpacing(30)

        # Formas de Pago
        lay_formas_pago = QVBoxLayout()
        self.lbl_f_pago = QLabel("<b>Forma de Pago:</b>")
        lay_formas_pago.addWidget(self.lbl_f_pago)
        
        self.group_pagos = QButtonGroup(self)
        self.rb_efectivo = QRadioButton("Efectivo")
        self.rb_pagomovil = QRadioButton("Pago Móvil")
        self.rb_debito = QRadioButton("Tarjeta de Débito")
        self.rb_credito = QRadioButton("Tarjeta de Crédito")
        self.rb_otros = QRadioButton("Otros (Zelle / Transferencia)")
        self.rb_efectivo.setChecked(True)
        
        self.pagos_lista = [self.rb_efectivo, self.rb_pagomovil, self.rb_debito, self.rb_credito, self.rb_otros]
        for i, rb in enumerate(self.pagos_lista):
            self.group_pagos.addButton(rb, i)
            lay_formas_pago.addWidget(rb)
            
        lay_pie.addLayout(lay_formas_pago, 33)

        # Sello
        lay_sello = QVBoxLayout()
        lay_sello.setAlignment(Qt.AlignCenter)
        self.frame_sello_box = QFrame()
        self.frame_sello_box.setFixedSize(220, 120)
        lay_s_txt = QVBoxLayout(self.frame_sello_box)
        
        self.lbl_s_1 = QLabel("<b>SELLO</b><br><br><small>RECIBÍ CONFORME</small>")
        self.lbl_s_1.setAlignment(Qt.AlignCenter)
        self.lbl_s_1.setStyleSheet("color: #94a3b8; border: none; font-size: 14px; letter-spacing: 2px; background: transparent;")
        lay_s_txt.addWidget(self.lbl_s_1)
        
        lay_sello.addWidget(self.frame_sello_box, alignment=Qt.AlignCenter)
        lay_pie.addLayout(lay_sello, 33)

        # Totales
        lay_totales = QFormLayout()
        lay_totales.setSpacing(12)
        lay_totales.setLabelAlignment(Qt.AlignLeft)
        
        self.combo_moneda = QComboBox()
        self.combo_moneda.addItems(["Bolívares (Bs.)", "Divisa (USD $)"])
        self.combo_moneda.setMinimumHeight(40); self.combo_moneda.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_moneda.currentIndexChanged.connect(self.actualizar_moneda)

        self.in_total = QLineEdit("0.00"); self.in_total.setReadOnly(True); self.in_total.setMinimumHeight(60); self.in_total.setAlignment(Qt.AlignRight)

        self.lbl_m = QLabel("<b>Moneda Base:</b>")
        self.lbl_tot = QLabel("<b>TOTAL EXENTO:</b>")

        lay_totales.addRow(self.lbl_m, self.combo_moneda)
        lay_totales.addRow(self.lbl_tot, self.in_total)
        
        lay_pie.addLayout(lay_totales, 34)
        layout_principal.addWidget(self.frame_pie)

        # ========================================================
        # 6. BOTONERA FINAL
        # ========================================================
        lay_botones_final = QHBoxLayout()
        lay_botones_final.setSpacing(20)
        
        self.btn_guardar_f = QPushButton("💾 GUARDAR FACTURA")
        self.btn_guardar_f.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar_f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_guardar_f.setMinimumHeight(50)
        self.btn_guardar_f.clicked.connect(self.guardar_factura_bd)
        
        self.btn_imprimir_f = QPushButton("🖨️ GENERAR FACTURA LEGAL (PDF)")
        self.btn_imprimir_f.setStyleSheet(tema.ESTILO_BTN_RECIPE)
        self.btn_imprimir_f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_imprimir_f.setMinimumHeight(50)
        self.btn_imprimir_f.clicked.connect(self.imprimir_factura_pdf)
        
        lay_botones_final.addWidget(self.btn_guardar_f)
        lay_botones_final.addWidget(self.btn_imprimir_f)
        layout_principal.addLayout(lay_botones_final)

        # Ensamblaje final
        self.scroll_area.setWidget(self.lienzo)
        layout_base.addWidget(self.scroll_area)

        # Enlace de señal reactiva para el cambio de modo claro/oscuro
        tema.tema_cambiado.connect(self.actualizar_estilos_dinamicos)

        self.generar_numeracion_automatica()
        self.cargar_membrete_doctor_dinamico()
        self.actualizar_estilos_dinamicos()

    # ========================================================
    # GESTIÓN DINÁMICA DE ESTILOS (ADAPTACIÓN MODO CLARO / OSCURO)
    # ========================================================
    def actualizar_estilos_dinamicos(self):
        if tema.modo_actual == "oscuro":
            color_titulos = "#FFFFFF"
            color_fondo_tarjetas = "#36393e"
            color_fondo_tabla = "#424549"
            style_factura_num = "font-size: 18px; border: 1px solid #cbd5e1; color: #FFFFFF; font-weight: bold; background-color: #424549; border-radius: 4px;"
            style_sello = "border: 2px dashed #93F6E3; border-radius: 6px; background: #282b30;"
        else:
            color_titulos = tema.TEXTO_MAIN
            color_fondo_tarjetas = tema.BG_TARJETA
            color_fondo_tabla = tema.BG_INPUT
            style_factura_num = "font-size: 18px; border: 1px solid #fda4af; color: #e11d48; font-weight: bold; background-color: #fff1f2; border-radius: 4px;"
            style_sello = "border: 2px dashed #94a3b8; border-radius: 6px; background: #f8fafc;"

        # Actualizar fondos base de la vista
        self.lienzo.setStyleSheet(f"background-color: {tema.BG_PRINCIPAL};")
        
        # Seteo de tarjetas contenedoras
        for frame in [self.frame_membrete, self.frame_numeros, self.group_paciente, self.frame_pie]:
            frame.setStyleSheet(f"background-color: {color_fondo_tarjetas}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 8px;")

        self.frame_sello_box.setStyleSheet(style_sello)

        # Seteo de los Labels e ítems de texto estáticos
        lbls_blancos = [self.lbl_clinica_nombre, self.lbl_doc_nombre, self.lbl_doc_direccion, self.lbl_doc_registro, 
                        self.lbl_doc_tlf, self.lbl_rif, self.lbl_tit_f, self.lbl_c, self.lbl_f, self.lbl_p_nom, 
                        self.lbl_p_dom, self.lbl_p_ced, self.lbl_p_tlf, self.lbl_p_con, self.lbl_tit_tabla, 
                        self.lbl_f_pago, self.lbl_m, self.lbl_tot]
        for lbl in lbls_blancos: lbl.setStyleSheet(f"color: {color_titulos}; border: none; background: transparent; font-weight: bold;")
        
        # Forzar estilos grandes en títulos
        self.lbl_doc_nombre.setStyleSheet(f"font-family: 'Times New Roman'; font-style: italic; font-size: 26px; color: {color_titulos}; border: none; background: transparent;")
        self.lbl_doc_especialidad.setStyleSheet("font-size: 14px; color: #0284c7; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        self.lbl_tit_tabla.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_titulos}; border: none; background: transparent;")
        self.lbl_f.setStyleSheet(f"font-size: 15px; border:none; background: transparent; color: {'#93F6E3' if tema.modo_actual == 'oscuro' else '#e11d48'};")

        # Refrescar los RadioButtons de Formas de Pago
        for rb in self.pagos_lista:
            rb.setStyleSheet(f"color: {color_titulos}; font-size: 14px; border:none; background: transparent;")

        # Aplicación controlada de estilos en inputs y combos
        estilo_inputs = f"background-color: {color_fondo_tabla}; color: {color_titulos}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 8px; font-size: 14px;"
        for inp in [self.in_nombre, self.in_domicilio, self.in_cedula, self.in_telefono, self.in_num_control, self.combo_condiciones, self.combo_moneda]:
            inp.setStyleSheet(estilo_inputs)

        # Inputs con diseños particulares
        self.in_num_factura.setStyleSheet(style_factura_num)
        self.in_total.setStyleSheet(f"font-size: 24px; font-weight: bold; padding: 10px; background-color: {color_fondo_tabla}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 4px; color: {'#93F6E3' if tema.modo_actual == 'oscuro' else '#0f172a'};")

        # Ajuste de estilos del QDateEdit del membrete
        self.in_fecha_factura.setStyleSheet(f"""
            QDateEdit {{
                background-color: transparent;
                color: {color_titulos};
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
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

        # 🚀 RE-APLICACIÓN DE TU PALETA EN EL TREEVIEW DE CONCEPTOS
        self.tabla_conceptos.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {color_fondo_tabla}; 
                color: {color_titulos}; 
                gridline-color: {tema.COLOR_DIVISION_TABLA}; 
                font-size: 14px;
                border-radius: 6px;
                border: 1px solid {tema.BORDE_SUAVE};
            }}
            QHeaderView::section {{
                background-color: #93F6E3;
                color: #1C1C1C;
                font-weight: bold;
                padding: 6px;
                border: 1px solid {tema.BORDE_SUAVE};
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: transparent;
                border: none;
            }}
        """)

        # Seteo interno de celdas dinámicas de la tabla de cobros
        for i in range(self.tabla_conceptos.rowCount()):
            for j in range(self.tabla_conceptos.columnCount()):
                item = self.tabla_conceptos.item(i, j)
                if item:
                    item.setForeground(QColor(color_titulos))
            
            # Forzar estilo en los widgets embebidos (inputs de las celdas)
            w_cant = self.tabla_conceptos.cellWidget(i, 0)
            w_desc = self.tabla_conceptos.cellWidget(i, 1)
            w_prec = self.tabla_conceptos.cellWidget(i, 2)
            
            if w_cant: w_cant.setStyleSheet(f"border:none; background:transparent; font-size:15px; color:{color_titulos};")
            if w_desc: w_desc.setStyleSheet(f"border:none; background:transparent; font-size:15px; padding-left:10px; color:{color_titulos};")
            if w_prec: w_prec.setStyleSheet(f"border:none; background:transparent; font-size:15px; padding-right:10px; font-weight: bold; color:{color_titulos};")

    # ========================================================
    # MÉTODOS LÓGICOS
    # ========================================================
    def actualizar_moneda(self):
        simbolo = "$" if "Divisa" in self.combo_moneda.currentText() else "Bs."
        item_precio = self.tabla_conceptos.horizontalHeaderItem(2)
        if item_precio:
            item_precio.setText(f"Precio Unitario ({simbolo})")
        self.calcular_totales_factura()

    def generar_numeracion_automatica(self):
        ahora = datetime.now()
        secuencia_control = ahora.strftime("%m-%d%H%M")
        secuencia_factura = ahora.strftime("%H%M%S")
        self.in_num_control.setText(f"00-{secuencia_control}")
        self.in_num_factura.setText(f"00{secuencia_factura}")

    def configurar_fila_tabla(self, fila):
        in_cant = QLineEdit("1")
        in_cant.setValidator(QIntValidator(1, 99))
        in_cant.setAlignment(Qt.AlignCenter)
        in_cant.textChanged.connect(self.calcular_totales_factura)
        self.tabla_conceptos.setCellWidget(fila, 0, in_cant)
        
        in_desc = QLineEdit()
        in_desc.setPlaceholderText("Escriba el servicio cobrado (ej: Consulta Médica, Procedimiento, etc.)")
        self.tabla_conceptos.setCellWidget(fila, 1, in_desc)
        
        in_precio = InputPrecioPOS()
        in_precio.textChanged.connect(self.calcular_totales_factura)
        self.tabla_conceptos.setCellWidget(fila, 2, in_precio)
        
        # Sincroniza los colores del tema en la nueva fila creada
        

    def añadir_fila_concepto(self):
        row = self.tabla_conceptos.rowCount()
        self.tabla_conceptos.insertRow(row)
        self.configurar_fila_tabla(row)

    def calcular_totales_factura(self):
        total_exento = 0.0
        for i in range(self.tabla_conceptos.rowCount()):
            widget_cant = self.tabla_conceptos.cellWidget(i, 0)
            widget_precio = self.tabla_conceptos.cellWidget(i, 2)
            
            if widget_cant and widget_precio:
                cant = int(widget_cant.text()) if widget_cant.text() else 0
                precio_txt = widget_precio.text()
                precio = float(precio_txt) if precio_txt else 0.0
                total_exento += (cant * precio)
                
        simbolo = "$" if "Divisa" in self.combo_moneda.currentText() else "Bs."
        self.in_total.setText(f"{simbolo} {total_exento:.2f}")

    def cargar_membrete_doctor_dinamico(self):
        db = SessionLocal()
        doc = db.query(PerfilDoctor).first()
        if doc:
            es_femenino = hasattr(doc, 'genero_doctor') and doc.genero_doctor and doc.genero_doctor.strip().lower() in ["femenino", "mujer"]
            prefijo = "Dra." if es_femenino else "Dr."
            
            nombre_doc = doc.nombre_doctor if doc.nombre_doctor else "Especialista"
            self.lbl_doc_nombre.setText(f"<h2>{prefijo} {nombre_doc}</h2>")
            
            if doc.nombre_clinica:
                self.lbl_clinica_nombre.setText(f"<b>{doc.nombre_clinica.upper()}</b>")
            
            if doc.especialidades:
                self.lbl_doc_especialidad.setText(doc.especialidades.upper())
                
            self.lbl_doc_registro.setText(f"C.I: {doc.cedula_doctor or '--'}  |  MSDS: {doc.matricula_msds or '--'}")
            
            rif_val = doc.rif_clinica if doc.rif_clinica else "--"
            self.lbl_rif.setText(f"<b>RIF: {rif_val.upper()}</b>")
            
            if doc.direccion_clinica:
                self.lbl_doc_direccion.setText(doc.direccion_clinica)
                
            tlf_val = doc.correo_doctor if doc.correo_doctor else "--"
            self.lbl_doc_tlf.setText(f"Contacto: {tlf_val}")
            
            if doc.logo_ruta and os.path.exists(doc.logo_ruta):
                pixmap = QPixmap(doc.logo_ruta)
                self.lbl_logo_imagen.setPixmap(pixmap.scaled(self.lbl_logo_imagen.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        db.close()
        self.actualizar_estilos_dinamicos()

    def cargar_datos_paciente(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        if p:
            self.in_nombre.setText(p.nombre_completo.upper())
            self.in_cedula.setText(p.cedula)
            self.in_telefono.setText(p.telefono_celular or "")
            
            if hasattr(p, 'direccion') and p.direccion:
                self.in_domicilio.setText(p.direccion.upper())
            else:
                self.in_domicilio.setText("CARACAS, VENEZUELA")
                
            if self.tabla_conceptos.rowCount() > 0:
                widget_desc = self.tabla_conceptos.cellWidget(0, 1)
                if widget_desc and not widget_desc.text():
                    widget_desc.setText("CONSULTA MÉDICA")
                    
        db.close()
        self.generar_numeracion_automatica()
        self.calcular_totales_factura()
        self.actualizar_estilos_dinamicos()

    def guardar_factura_bd(self):
        if not self.paciente_id:
            QMessageBox.warning(self, "Aviso", "Asegúrese de seleccionar un paciente de la sala de espera.")
            return False
            
        tiene_conceptos = False
        for i in range(self.tabla_conceptos.rowCount()):
            widget_desc = self.tabla_conceptos.cellWidget(i, 1)
            if widget_desc and widget_desc.text().strip():
                tiene_conceptos = True
                break
                
        if not tiene_conceptos:
            QMessageBox.warning(self, "Aviso", "Debe ingresar al menos un concepto o servicio válido en la tabla.")
            return False
            
        return True

    def imprimir_factura_pdf(self):
        if not self.guardar_factura_bd():
            return

        db = SessionLocal()
        doc = db.query(PerfilDoctor).first()
        paciente_obj = db.query(Paciente).get(self.paciente_id)
        
        if not doc or not paciente_obj:
            QMessageBox.critical(self, "Error", "No se pudieron cargar los datos del perfil médico o del paciente para el PDF.")
            db.close()
            return

        datos_factura = {
            "num_control": self.in_num_control.text(),
            "num_factura": self.in_num_factura.text(),
            "fecha_emision": self.in_fecha_factura.date().toPython().strftime("%d/%m/%Y"),
            "cliente_nombre": self.in_nombre.text().strip(),
            "cliente_domicilio": self.in_domicilio.text().strip(),
            "cliente_cedula": self.in_cedula.text().strip(),
            "cliente_telefono": self.in_telefono.text().strip(),
            "condiciones_pago": self.combo_condiciones.currentText(),
            "forma_pago": self.group_pagos.checkedButton().text() if self.group_pagos.checkedButton() else "Efectivo",
            "moneda": "USD" if "Divisa" in self.combo_moneda.currentText() else "Bs.",
            "total_pagar": self.in_total.text()
        }

        conceptos_facturados = []
        for i in range(self.tabla_conceptos.rowCount()):
            widget_cant = self.tabla_conceptos.cellWidget(i, 0)
            widget_desc = self.tabla_conceptos.cellWidget(i, 1)
            widget_precio = self.tabla_conceptos.cellWidget(i, 2)
            
            if widget_desc and widget_desc.text().strip():
                cantidad = widget_cant.text().strip() if widget_cant else "1"
                descripcion = widget_desc.text().strip().upper()
                precio_unitario = widget_precio.text().strip() if widget_precio else "0.00"
                
                try:
                    total_fila = f"{int(cantidad) * float(precio_unitario):.2f}"
                except:
                    total_fila = precio_unitario
                    
                conceptos_facturados.append({
                    "cantidad": cantidad,
                    "descripcion": descripcion,
                    "precio_unitario": precio_unitario,
                    "total_renglon": total_fila
                })

        db.close()

        try:
            from servicios_impresion import MotorImpresion 
            
            carpeta_base = os.path.dirname(os.path.abspath(__file__))
            carpeta_facturas = os.path.join(carpeta_base, "Facturas_Medicas")

            if not os.path.exists(carpeta_facturas):
                os.makedirs(carpeta_facturas)
                
            ruta_pdf = os.path.join(carpeta_facturas, f"Factura_{datos_factura['num_factura']}.pdf")
            
            MotorImpresion.generar_pdf_factura(
                doctor=doc, 
                datos=datos_factura, 
                conceptos=conceptos_facturados, 
                ruta_salida=ruta_pdf
            )
            
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta_pdf))
            
        except ImportError:
            QMessageBox.critical(self, "Error de Sistema", "No se encontró el módulo 'servicios_impresion.py' o el método 'generar_pdf_factura'.")
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", f"Ocurrió un problema construyendo el reporte digital:\n{str(e)}")