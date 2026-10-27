from PySide6.QtCore import QTimer, Signal, Qt, QDate
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QComboBox, QDateEdit, QPushButton, 
                             QMessageBox, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QScrollArea, QRadioButton, QButtonGroup, QSizePolicy, QToolButton)
from PySide6.QtGui import QColor
from datetime import datetime, date
from database import SessionLocal
from models import Paciente, AgendaDiaria
from estilos import tema  # Importación del motor de diseño centralizado

class FichaIdentificacion(QWidget):
    paciente_registrado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id_edicion = None 
        
        # Seteo de la ventana base adaptable
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        layout_principal.setSpacing(15)

        # --- SECCIÓN IZQUIERDA: FORMULARIO EN CARD COMPACTO (SIN SCROLLBAR) ---
        self.frame_registro = QFrame()
        self.frame_registro.setStyleSheet(tema.ESTILO_TARJETA)
        self.frame_registro.setFixedWidth(410)  
        
        layout_reg_master = QVBoxLayout(self.frame_registro)
        layout_reg_master.setContentsMargins(15, 15, 15, 15)
        layout_reg_master.setSpacing(10)  
        
        self.titulo_form = QLabel("📝 Registro")
        self.titulo_form.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        layout_reg_master.addWidget(self.titulo_form)

        contenedor_formulario = QWidget()
        contenedor_formulario.setStyleSheet("background-color: transparent;")
        self.form = QFormLayout(contenedor_formulario)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setVerticalSpacing(6)  
        self.form.setLabelAlignment(Qt.AlignLeft)
        
        # 🎨 1) HOJA DE ESTILO OPTIMIZADA PARA LOS ENTRYS
        estilo_input_corregido = f"""
            QLineEdit, QTextEdit {{
                background-color: {tema.BG_INPUT};
                color: {tema.TEXTO_MAIN};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                padding-top: 4px;      
                padding-bottom: 4px;   
                padding-left: 10px;
                padding-right: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {tema.MENTA_MEDICA};
                background-color: {tema.BG_INPUT};
            }}
        """
        
        # 🎨 2) COMBOBOX TRADICIONAL, LIMPIO Y NATIVO
        estilo_combobox = f"""
            QComboBox {{
                background-color: {tema.BG_INPUT};
                color: {tema.TEXTO_MAIN};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
            }}
            QComboBox:focus {{
                border: 2px solid {tema.MENTA_MEDICA};
            }}
            QComboBox QAbstractItemView {{
                background-color: {tema.BG_TARJETA};
                color: {tema.TEXTO_MAIN};
                selection-background-color: {tema.MENTA_MEDICA};
                selection-color: #1C1C1C;
            }}
        """

        # 🎨 3) CALENDARIO ADAPTABLE CORREGIDO
        estilo_calendario_fijo = f"""
            QDateEdit {{
                background-color: {tema.BG_INPUT};
                color: {tema.TEXTO_MAIN};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
            }}
            QDateEdit:focus {{
                border: 2px solid {tema.MENTA_MEDICA};
            }}
        """

        # Componente combinado de Cédula
        layout_cedula = QHBoxLayout()
        layout_cedula.setSpacing(6)
        self.in_prefijo = QComboBox()
        self.in_prefijo.addItems(["V", "E"])
        self.in_prefijo.setFixedWidth(55)
        self.in_prefijo.setStyleSheet(estilo_combobox)
        self.in_prefijo.setFixedHeight(34)
        
        self.in_cedula_num = QLineEdit()
        self.in_cedula_num.setPlaceholderText("Cédula...")
        self.in_cedula_num.setStyleSheet(estilo_input_corregido)
        self.in_cedula_num.setFixedHeight(34)
        layout_cedula.addWidget(self.in_prefijo)
        layout_cedula.addWidget(self.in_cedula_num)

        # Inicialización de campos con alturas optimizadas
        self.in_nombre = QLineEdit()
        
        # 🗓️ CONFIGURACIÓN DEL CALENDARIO CLÁSICO EXPANDIDO POR CÓDIGO
        self.in_fecha_nac = QDateEdit()
        self.in_fecha_nac.setCalendarPopup(True)
        
        calendario_interno = self.in_fecha_nac.calendarWidget()
        if calendario_interno:
            calendario_interno.setMinimumSize(420, 300) 
            calendario_interno.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            botones_internos = calendario_interno.findChildren(QPushButton) + calendario_interno.findChildren(QToolButton)
            for btn in botones_internos:
                btn.setMinimumHeight(35)
                fuente = btn.font()
                fuente.setPointSize(14)
                fuente.setBold(True)
                btn.setFont(fuente)

        self.in_fecha_nac.setDate(QDate.currentDate().addYears(0))
        self.in_genero = QComboBox(); self.in_genero.addItems(["Femenino", "Masculino"])
        self.in_nacionalidad = QLineEdit(text="Venezolana")
        self.in_pais = QLineEdit(text="Venezuela")
        self.in_estado_civil = QComboBox(); self.in_estado_civil.addItems(["Soltero(a)", "Casado(a)", "Divorciado(a)", "Viudo(a)", "Concubinato"])
        self.in_profesion = QLineEdit()
        self.in_celular = QLineEdit(); self.in_casa = QLineEdit(); self.in_direccion = QLineEdit()

        # Aplicación controlada de los estilos corregidos
        campos_lineedits = [self.in_nombre, self.in_nacionalidad, self.in_pais, self.in_profesion, 
                            self.in_celular, self.in_casa, self.in_direccion]
        for widget in campos_lineedits:
            widget.setStyleSheet(estilo_input_corregido)
            widget.setFixedHeight(34)  

        for combo in [self.in_genero, self.in_estado_civil]:
            combo.setStyleSheet(estilo_combobox)
            combo.setFixedHeight(34)

        # Aplicamos el estilo al calendario
        self.in_fecha_nac.setStyleSheet(estilo_calendario_fijo)
        self.in_fecha_nac.setFixedHeight(34)

        # Radio Buttons de Seguro
        self.group_seguro = QButtonGroup(self); self.btn_seguro_no = QRadioButton("No"); self.btn_seguro_si = QRadioButton("Sí")
        self.btn_seguro_no.setChecked(True); self.group_seguro.addButton(self.btn_seguro_no); self.group_seguro.addButton(self.btn_seguro_si)
        layout_btns_seguro = QHBoxLayout(); layout_btns_seguro.setSpacing(15); layout_btns_seguro.addWidget(self.btn_seguro_no); layout_btns_seguro.addWidget(self.btn_seguro_si)
        self.in_seguro = QLineEdit(); self.in_seguro.setVisible(False); self.in_seguro.setStyleSheet(estilo_input_corregido); self.in_seguro.setFixedHeight(34)

        # Radio Buttons de Referido
        self.group_referido = QButtonGroup(self); self.btn_ref_no = QRadioButton("No"); self.btn_ref_si = QRadioButton("Sí")
        self.btn_ref_no.setChecked(True); self.group_referido.addButton(self.btn_ref_no); self.group_referido.addButton(self.btn_ref_si)
        layout_btns_ref = QHBoxLayout(); layout_btns_ref.setSpacing(15); layout_btns_ref.addWidget(self.btn_ref_no); layout_btns_ref.addWidget(self.btn_ref_si)
        self.in_referido = QLineEdit(); self.in_referido.setVisible(False); self.in_referido.setStyleSheet(estilo_input_corregido); self.in_referido.setFixedHeight(34)

        for rb in [self.btn_seguro_no, self.btn_seguro_si, self.btn_ref_no, self.btn_ref_si]:
            rb.setStyleSheet(f"color: {tema.TEXTO_MAIN}; font-size: 13px; background: transparent;")

        self.btn_seguro_si.toggled.connect(self.in_seguro.setVisible); self.btn_ref_si.toggled.connect(self.in_referido.setVisible)

        # Construcción compacta del formulario en la tarjeta
        labels_form = [
            ("Cédula:", layout_cedula), ("Nombre:", self.in_nombre), ("F. Nac:", self.in_fecha_nac),
            ("Género:", self.in_genero), ("Nacionalidad:", self.in_nacionalidad), ("País:", self.in_pais),
            ("Estado Civil:", self.in_estado_civil), ("Profesión:", self.in_profesion), ("Celular:", self.in_celular),
            ("Tlf Casa:", self.in_casa), ("Dirección:", self.in_direccion), ("¿Seguro?", layout_btns_seguro),
            ("", self.in_seguro), ("¿Referido?", layout_btns_ref), ("", self.in_referido)
        ]
        
        for texto_label, campo_w in labels_form:
            if texto_label:
                lbl_obj = QLabel(texto_label)
                lbl_obj.setStyleSheet("font-size: 13px; font-weight: bold; color: " + tema.TEXTO_MUTED + ";")
                self.form.addRow(lbl_obj, campo_w)
            else:
                self.form.addRow(texto_label, campo_w)

        # Conexión para Mayúsculas Automáticas
        for edit in [self.in_nombre, self.in_nacionalidad, self.in_pais, self.in_profesion, 
                     self.in_direccion, self.in_seguro, self.in_referido]:
            edit.textChanged.connect(lambda text, e=edit: self.formatear_mayusculas(text, e))

        layout_reg_master.addWidget(contenedor_formulario)
        
        self.btn_guardar = QPushButton("💾 GUARDAR PACIENTE")
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar.setMinimumHeight(40)
        self.btn_guardar.clicked.connect(self.guardar_datos)
        layout_reg_master.addWidget(self.btn_guardar)

        # --- SECCIÓN DERECHA: LISTADO / BASE DE DATOS ---
        self.frame_lista = QFrame()
        self.frame_lista.setStyleSheet(tema.ESTILO_TARJETA)
        layout_lista = QVBoxLayout(self.frame_lista)
        layout_lista.setContentsMargins(15, 15, 15, 15)
        layout_lista.setSpacing(12)
        
        lbl_db_title = QLabel("🔍 Base de Datos de Pacientes")
        lbl_db_title.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        layout_lista.addWidget(lbl_db_title)
        
        self.in_buscador = QLineEdit()
        self.in_buscador.setPlaceholderText("Buscar por nombre o cédula...")
        self.in_buscador.setStyleSheet(estilo_input_corregido)
        self.in_buscador.setMinimumHeight(38)
        self.in_buscador.textChanged.connect(self.actualizar_tabla)
        layout_lista.addWidget(self.in_buscador)

        # Configuración Estilizada de la Tabla
        self.tabla = QTableWidget()
        columnas = [
            "Cédula", "Nombre Completo", "Género", "Edad", "F. Nacimiento", 
            "Seguro", "Estado Civil", "Profesión", "Celular", "Casa", 
            "Dirección", "Referido", "F. Registro"
        ]
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        layout_lista.addWidget(self.tabla)

        layout_btns_tabla = QHBoxLayout()
        layout_btns_tabla.setSpacing(15)
        
        self.btn_modificar = QPushButton("✏️ Cargar para Editar")
        self.btn_modificar.setStyleSheet(tema.ESTILO_BTN_INFORME)  
        self.btn_modificar.setMinimumHeight(40)
        self.btn_modificar.clicked.connect(self.cargar_datos_para_editar)
        
        self.btn_espera = QPushButton("📥 Añadir a Lista de Espera")
        self.btn_espera.setStyleSheet(tema.ESTILO_BTN_ORDEN)  
        self.btn_espera.setMinimumHeight(40)
        self.btn_espera.clicked.connect(self.poner_en_espera)
        
        layout_btns_tabla.addWidget(self.btn_modificar)
        layout_btns_tabla.addWidget(self.btn_espera)
        layout_lista.addLayout(layout_btns_tabla)

        layout_principal.addWidget(self.frame_registro)
        layout_principal.addWidget(self.frame_lista, 1)

        tema.tema_cambiado.connect(self.actualizar_tabla)
        self.actualizar_tabla()
        self.ultimo_conteo_pacientes = -1  # Variable para guardar la memoria del conteo
        self.timer_sincronizacion = QTimer(self)
        self.timer_sincronizacion.timeout.connect(self.verificar_cambios_silenciosos)
        self.timer_sincronizacion.start(5000)  # Chequeo ligero cada 5 segundos
        
    def formatear_mayusculas(self, text, edit_widget):
        pos = edit_widget.cursorPosition()
        edit_widget.blockSignals(True) 
        edit_widget.setText(text.title()) 
        edit_widget.setCursorPosition(pos)
        edit_widget.blockSignals(False)

    def verificar_cambios_silenciosos(self):
        """ 
        Genera una huella ligera con los datos clave.
        Si se edita un paciente o se registra uno nuevo, se actualiza en silencio.
        """
        db = SessionLocal()
        try:
            # Consulta ultra ligera: solo traemos las columnas necesarias, no los objetos completos
            pacientes_db = db.query(Paciente.id, Paciente.cedula, Paciente.nombre_completo, Paciente.genero).all()
            nueva_huella = str(pacientes_db)
            
            if self.huella_pacientes_ui != nueva_huella:
                if self.huella_pacientes_ui != "":
                    self.actualizar_tabla()
                self.huella_pacientes_ui = nueva_huella
        except Exception:
            pass  # Ignora micro-cortes de red
        finally:
            db.close()

    def actualizar_tabla(self):
        filtro = self.in_buscador.text().strip()
        db = SessionLocal()
        query = db.query(Paciente)
        if filtro:
            query = query.filter((Paciente.nombre_completo.ilike(f"%{filtro}%")) | (Paciente.cedula.ilike(f"%{filtro}%")))
        pacientes = query.order_by(Paciente.nombre_completo).all()
        
        self.tabla.setRowCount(len(pacientes))
        
        # 🎨 DETERMINAMOS TONOS EXACTOS SEGÚN EL MODO ACTIVO
        if tema.modo_actual == "oscuro":
            color_titulos = "#FFFFFF"  
            color_fondo_tarjetas = "#36393e" 
            color_fondo_tabla = "#424549"    
        else:
            color_titulos = tema.TEXTO_MAIN
            color_fondo_tarjetas = tema.BG_TARJETA
            color_fondo_tabla = tema.BG_INPUT

        # 1) Forzar color exacto a los Frames Laterales
        self.frame_registro.setStyleSheet(f"background-color: {color_fondo_tarjetas}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 8px;")
        self.frame_lista.setStyleSheet(f"background-color: {color_fondo_tarjetas}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 8px;")
        
        # 2) Forzar color exacto a las etiquetas estáticas del formulario y títulos principales
        self.titulo_form.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_titulos}; border: none; background: transparent;")
        lbl_db_title = self.frame_lista.findChild(QLabel)
        if lbl_db_title:
            lbl_db_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_titulos}; border: none; background: transparent;")

        # Buscar todos los labels pequeños y pintarlos en blanco/negro dinámico
        for lbl in self.frame_registro.findChildren(QLabel):
            if lbl != self.titulo_form:
                lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color_titulos}; background: transparent; border: none;")

        # 3) 🚀 FIJACIÓN BRUTAL DEL TREEVIEW: Cabeceras (#93F6E3), Divisiones y Scrollbars Cápsula integrados localmente
        self.tabla.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {color_fondo_tabla}; 
                color: {color_titulos}; 
                gridline-color: {tema.COLOR_DIVISION_TABLA}; 
                font-size: 13px;
                border-radius: 4px;
                border: 1px solid {tema.BORDE_SUAVE};
                alternate-background-color: {'#2f3136' if tema.modo_actual == "oscuro" else '#F1F5F9'};
            }}
            QHeaderView::section {{
                background-color: #93F6E3;
                color: #1C1C1C;
                font-weight: bold;
                padding: 6px;
                border: 1px solid {tema.BORDE_SUAVE};
            }}
            /* 📌 CORRECCIÓN TOTAL DE SCROLLBAR VERTICAL PÍLDORA */
            QScrollBar:vertical {{
                background: transparent;
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {tema.COLOR_SCROLLBAR};
                min-height: 30px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {tema.MENTA_HOVER if tema.modo_actual == "oscuro" else "#475569"};
            }}
            /* 📌 CORRECCIÓN TOTAL DE SCROLLBAR HORIZONTAL PÍLDORA */
            QScrollBar:horizontal {{
                background: transparent;
                height: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {tema.COLOR_SCROLLBAR};
                min-width: 30px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {tema.MENTA_HOVER if tema.modo_actual == "oscuro" else "#475569"};
            }}
            QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
                border: none;
            }}
        """)

        # 4) Forzar los estilos de los campos de texto y desplegables tradicionales
        estilo_dinamico_input = f"background-color: {color_fondo_tabla}; color: {color_titulos}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 4px 10px; font-size: 14px;"
        for widget in [self.in_nombre, self.in_nacionalidad, self.in_pais, self.in_profesion, 
                       self.in_celular, self.in_casa, self.in_direccion, self.in_buscador, 
                       self.in_cedula_num, self.in_prefijo, self.in_genero, self.in_estado_civil]:
            widget.setStyleSheet(estilo_dinamico_input)

        # 🔒 TU CALENDARIO CON CABECERA #93F6E3 ASEGURADA
        self.in_fecha_nac.setStyleSheet(f"""
            QDateEdit {{
                background-color: {color_fondo_tabla};
                color: {color_titulos};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 14px;
            }}
            QDateEdit:focus {{
                border: 2px solid {tema.MENTA_MEDICA};
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
            QCalendarWidget QNavigationBar QToolButton {{
                background-color: transparent;
                color: #1C1C1C;
                font-size: 15px;         
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;       
                height: 24px;            
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #ffffff;
                color: #1C1C1C;
                selection-background-color: #93F6E3;
                selection-color: #1C1C1C;
            }}
            QCalendarWidget QMenu {{
                background-color: #ffffff;
                color: #1C1C1C;
            }}
        """)

        for rb in [self.btn_seguro_no, self.btn_seguro_si, self.btn_ref_no, self.btn_ref_si]:
            rb.setStyleSheet(f"color: {color_titulos}; font-size: 13px; background: transparent; border: none;")

        # 5) Pintar las celdas sin machacar el fondo para que las gridlines sean visibles
        for i, p in enumerate(pacientes):
            datos = [
                p.cedula, p.nombre_completo, p.genero, f"{p.edad_actual} años",
                p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else "--",
                p.seguro, p.estado_civil, p.profesion, p.telefono_celular, p.telefono_casa,
                p.direccion, p.referido, p.fecha_registro.strftime('%d/%m/%Y %H:%M')
            ]
            
            for j, valor in enumerate(datos):
                item = QTableWidgetItem(str(valor) if valor else "--")
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                # Al quitar el setBackground sólido por celda, Qt respeta al 100% las divisiones de la tabla
                item.setForeground(QColor(color_titulos))
                
                self.tabla.setItem(i, j, item)
            
        self.tabla.resizeColumnsToContents()
        db.close()

    def guardar_datos(self):
        cedula_num = self.in_cedula_num.text().strip()
        if not cedula_num or not self.in_nombre.text():
            QMessageBox.warning(self, "Error", "Cédula y Nombre son obligatorios.")
            return

        cedula_final = f"{self.in_prefijo.currentText()}-{cedula_num}"
        db = SessionLocal()
        try:
            val_seguro = self.in_seguro.text() if self.btn_seguro_si.isChecked() else "No Aplica"
            val_referido = self.in_referido.text() if self.btn_ref_si.isChecked() else "No Aplica"

            if self.paciente_id_edicion:
                p = db.query(Paciente).get(self.paciente_id_edicion)
                if p:
                    p.cedula, p.nombre_completo = cedula_final, self.in_nombre.text().strip()
                    p.fecha_nacimiento = self.in_fecha_nac.date().toPython()
                    p.genero, p.nacionalidad, p.pais = self.in_genero.currentText(), self.in_nacionalidad.text(), self.in_pais.text()
                    p.estado_civil, p.profesion = self.in_estado_civil.currentText(), self.in_profesion.text()
                    p.telefono_celular, p.telefono_casa, p.direccion = self.in_celular.text(), self.in_casa.text(), self.in_direccion.text()
                    p.seguro, p.referido = val_seguro, val_referido
            else:
                p = Paciente(
                    cedula=cedula_final, nombre_completo=self.in_nombre.text().strip(), 
                    fecha_nacimiento=self.in_fecha_nac.date().toPython(),
                    genero=self.in_genero.currentText(), nacionalidad=self.in_nacionalidad.text(),
                    pais=self.in_pais.text(), estado_civil=self.in_estado_civil.currentText(),
                    profesion=self.in_profesion.text(), telefono_celular=self.in_celular.text(),
                    telefono_casa=self.in_casa.text(), direccion=self.in_direccion.text(),
                    seguro=val_seguro, referido=val_referido
                )
                db.add(p)
            db.commit(); self.limpiar_campos(); self.actualizar_tabla(); self.paciente_registrado.emit()
        except Exception as e:
            db.rollback(); QMessageBox.critical(self, "Error", f"Fallo: {e}")
        finally: db.close()

    def cargar_datos_para_editar(self):
        fila = self.tabla.currentRow()
        if fila == -1: return
        cedula_full = self.tabla.item(fila, 0).text()
        db = SessionLocal(); p = db.query(Paciente).filter(Paciente.cedula == cedula_full).first()
        if p:
            self.paciente_id_edicion = p.id
            self.titulo_form.setText("✏️ Editando Paciente")
            self.titulo_form.setStyleSheet("font-size: 18px; font-weight: bold; color: #e67e22; border: none; background: transparent;")
            if "-" in p.cedula:
                pref, num = p.cedula.split("-", 1)
                self.in_prefijo.setCurrentText(pref); self.in_cedula_num.setText(num)
            else: self.in_cedula_num.setText(p.cedula)
            self.in_nombre.setText(p.nombre_completo); self.in_fecha_nac.setDate(p.fecha_nacimiento)
            self.in_genero.setCurrentText(p.genero); self.in_profesion.setText(p.profesion)
            self.in_celular.setText(p.telefono_celular); self.in_direccion.setText(p.direccion)
            if p.seguro and p.seguro != "No Aplica":
                self.btn_seguro_si.setChecked(True); self.in_seguro.setText(p.seguro)
            else: self.btn_seguro_no.setChecked(True)
        db.close()

    def poner_en_espera(self):
        fila = self.tabla.currentRow()
        if fila == -1: return
        cedula_p = self.tabla.item(fila, 0).text()
        db = SessionLocal(); p = db.query(Paciente).filter(Paciente.cedula == cedula_p).first()
        if p:
            hoy = date.today()
            if not db.query(AgendaDiaria).filter(AgendaDiaria.paciente_id == p.id, AgendaDiaria.fecha_dia == hoy).first():
                db.add(AgendaDiaria(paciente_id=p.id, fecha_dia=hoy, estado="En espera"))
                db.commit(); self.paciente_registrado.emit()
        db.close()

    def limpiar_campos(self):
        self.paciente_id_edicion = None; self.titulo_form.setText("📝 Registro")
        self.titulo_form.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        for w in self.findChildren(QLineEdit): w.clear()
        self.in_pais.setText("Venezuela"); self.in_nacionalidad.setText("Venezolana")