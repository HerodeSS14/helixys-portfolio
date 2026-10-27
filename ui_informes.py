from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QMessageBox, QFrame, 
                             QCheckBox, QDateEdit, QLineEdit, QFormLayout,
                             QComboBox, QInputDialog, QToolBar)
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QDesktopServices, QColor
from database import SessionLocal
from models import Paciente, InformeMedico, ArchivoPaciente, PerfilDoctor, Consulta, PlantillaInforme
from servicios_impresion import MotorImpresion
import os
import re
from datetime import datetime
from estilos import tema  # Importación del motor de diseño centralizado
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction

class PantallaInforme(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.edad_clinica = 0
        self.ruta_base = "archivos_clinica"

        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)

        # --- 1. CABECERA DE IDENTIFICACIÓN ---
        self.frame_paciente = QFrame()
        lay_h = QHBoxLayout(self.frame_paciente)
        
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> Seleccione uno...")
        self.lbl_cedula = QLabel("<b>CÉDULA:</b> --")
        self.lbl_edad = QLabel("<b>EDAD AL MOMENTO:</b> --")
        
        lay_h.addWidget(self.lbl_paciente)
        lay_h.addWidget(self.lbl_cedula)
        lay_h.addWidget(self.lbl_edad)
        layout_principal.addWidget(self.frame_paciente)

        # --- 2. CONFIGURACIÓN DEL INFORME (Casillas Inteligentes) ---
        form_config = QFormLayout()
        form_config.setSpacing(10)
        
        self.in_fecha = QDateEdit(calendarPopup=True)
        self.in_fecha.setDate(QDate.currentDate())
        self.in_fecha.setFixedWidth(150)
        
        # Estilo unificado para el DateEdit de Qt de acuerdo al tema
        self.in_fecha.calendarWidget().setStyleSheet(f"""
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
        
        # Checkboxes
        self.check_antecedentes = QCheckBox("Incluir Antecedentes Completos al inicio")
        self.check_antecedentes.toggled.connect(self.actualizar_texto_antecedentes)

        lay_checks_opcionales = QHBoxLayout()
        self.check_referido = QCheckBox("Incluir Doctor Referido (Si aplica)")
        self.check_seguro = QCheckBox("Incluir Seguro Médico (Si aplica)")
        self.check_referido.setChecked(True)
        self.check_seguro.setChecked(True)
        lay_checks_opcionales.addWidget(self.check_referido)
        lay_checks_opcionales.addWidget(self.check_seguro)
        lay_checks_opcionales.addStretch()

        self.lbl_etiqueta_fecha = QLabel("Fecha del Informe:")
        self.lbl_etiqueta_opciones = QLabel("Opciones del Paciente:")

        form_config.addRow(self.lbl_etiqueta_fecha, self.in_fecha)
        form_config.addRow(self.check_antecedentes)
        form_config.addRow(self.lbl_etiqueta_opciones, lay_checks_opcionales)
        layout_principal.addLayout(form_config)

        # --- 3. ETIQUETAS INTELIGENTES (La Chuleta) ---
        self.lbl_titulo_redaccion = QLabel("<h3>📝 Redacción (Use los botones para insertar etiquetas):</h3>")
        layout_principal.addWidget(self.lbl_titulo_redaccion)
        
        self.lay_etiquetas = QHBoxLayout()
        self.lay_etiquetas.setSpacing(6)
        
        tags = [
            ("{edad}", "{edad}"), ("{motivo}", "{motivo}"), 
            ("{enf_actual}", "{enfermedad_actual}"), ("{ex_fisico}", "{examen_fisico}"), 
            ("{diagnostico}", "{diagnostico}"), 
            ("{bloque_referencia}", "{bloque_referencia}"), ("{bloque_seguro}", "{bloque_seguro}"),
            ("[Rellenar]", "[ ]")
        ]
        
        self.lista_botones_tags = []
        for texto_btn, tag_real in tags:
            btn = QPushButton(texto_btn)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked=False, t=tag_real: self.insertar_etiqueta(t))
            self.lay_etiquetas.addWidget(btn)
            self.lista_botones_tags.append(btn)
            
        layout_principal.addLayout(self.lay_etiquetas)

        # --- 4. GESTIÓN DE PLANTILLAS Y MAGIA ---
        lay_plantillas = QHBoxLayout()
        lay_plantillas.setSpacing(8)
        
        self.lbl_tit_plantillas = QLabel("<b>📄 Plantillas:</b>")
        lay_plantillas.addWidget(self.lbl_tit_plantillas)
        
        self.combo_plantillas = QComboBox()
        lay_plantillas.addWidget(self.combo_plantillas, stretch=1)
        
        self.btn_cargar_plantilla = QPushButton("📂 Cargar")
        self.btn_cargar_plantilla.setStyleSheet(tema.ESTILO_BTN_INFORME)
        self.btn_cargar_plantilla.clicked.connect(self.cargar_plantilla_en_cuerpo)

        self.btn_procesar = QPushButton("🪄 Procesar Plantilla")
        self.btn_procesar.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; font-size: 13px; border: none;")
        self.btn_procesar.clicked.connect(self.procesar_etiquetas_inteligentes)
        
        self.btn_guardar_plantilla = QPushButton("💾 Guardar Nueva")
        self.btn_guardar_plantilla.setStyleSheet(tema.ESTILO_BTN_ORDEN)
        self.btn_guardar_plantilla.clicked.connect(self.guardar_plantilla_actual)
        
        self.btn_eliminar_plantilla = QPushButton("🗑️ Eliminar")
        self.btn_eliminar_plantilla.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_eliminar_plantilla.clicked.connect(self.eliminar_plantilla_seleccionada)
        
        lay_plantillas.addWidget(self.btn_cargar_plantilla)
        lay_plantillas.addWidget(self.btn_procesar)
        lay_plantillas.addWidget(self.btn_guardar_plantilla)
        lay_plantillas.addWidget(self.btn_eliminar_plantilla)
        
        layout_principal.addLayout(lay_plantillas)
        self.actualizar_combo_plantillas()

        # --- 5. CUERPO DEL INFORME ---
        self.in_cuerpo = QTextEdit()
        self.in_cuerpo.setPlaceholderText("Escriba su informe o cargue una plantilla, luego presione '🪄 Procesar Plantilla'...")
        layout_principal.addWidget(self.in_cuerpo)

        self.lbl_comentario_privado = QLabel("<b>🗨️ Comentario Interno (Privado):</b>")
        layout_principal.addWidget(self.lbl_comentario_privado)
        
        self.in_comentario = QLineEdit()
        layout_principal.addWidget(self.in_comentario)

        # --- 6. BOTONERA FINAL ---
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(12)

        self.btn_guardar = QPushButton("💾 GUARDAR REGISTRO")
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar.setFixedHeight(45)
        self.btn_guardar.clicked.connect(self.guardar_datos_informe)

        # --- BOTÓN DE GENERACIÓN CON MENÚ DE FORMATOS (PDF / WORD) ---
        self.btn_generar_doc = QPushButton("🖨️ GENERAR INFORME ▾")
        self.btn_generar_doc.setStyleSheet("""
            QPushButton {
                background-color: #34495e; 
                color: white; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 14px; 
                border: none;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2C3E50;
                border: 1px solid #93F6E3;
            }
        """)
        self.btn_generar_doc.setFixedHeight(45)

        # Menú desplegable para elegir el formato
        menu_impresion = QMenu(self)
        menu_impresion.setStyleSheet(tema.ESTILO_VENTANA)

        action_pdf = QAction("📄 Generar en PDF (.pdf)", self)
        action_pdf.triggered.connect(lambda: self.procesar_documento(formato="pdf"))

        action_docx = QAction("📝 Generar en Word (.docx)", self)
        action_docx.triggered.connect(lambda: self.procesar_documento(formato="docx"))

        menu_impresion.addAction(action_pdf)
        menu_impresion.addAction(action_docx)

        self.btn_generar_doc.setMenu(menu_impresion)

        btns_layout.addWidget(self.btn_guardar)
        btns_layout.addWidget(self.btn_generar_doc)
        layout_principal.addLayout(btns_layout)

        # Conexión al motor de escucha reactiva
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def ajustar_emergente_parent(self, box):
        # Utilidad para enlazar el parent de la ventana y obligar al CSS a pintar de forma oscura
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    # ========================================================
    # GESTIÓN DINÁMICA DE ESTILOS (ADAPTACIÓN CENTRALIZADA)
    # ========================================================
    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        
        # 1. Cabecera superior adaptada
        self.frame_paciente.setStyleSheet(f"""
            QFrame {{
                background-color: {tema.BG_TARJETA}; 
                border-radius: 10px; 
                border: 1px solid {tema.BORDE_SUAVE};
            }}
            QLabel {{
                color: {color_txt};
                font-size: 14px;
                border: none;
                background: transparent;
            }}
        """)
        self.lbl_paciente.setStyleSheet(f"font-size: 15px; color: {color_txt}; font-weight: bold; background: transparent; border: none;")

        # 2. Re-estilizar casillas de entrada
        self.in_fecha.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 6px; font-size: 14px;")
        self.in_comentario.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 8px; font-size: 14px;")
        
        self.in_cuerpo.setStyleSheet(f"""
            QTextEdit {{
                background-color: {tema.BG_INPUT}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 15px; 
                border: 1px solid {tema.BORDE_SUAVE}; 
                border-radius: 8px;
            }}
            QTextEdit:focus {{ border: 2px solid {tema.MENTA_MEDICA}; }}
        """)

        # 3. Re-estilizar combos y casillas de verificación
        self.combo_plantillas.setStyleSheet(f"""
            QComboBox {{
                background-color: {tema.BG_INPUT}; 
                color: {color_txt}; 
                border: 1px solid {tema.BORDE_SUAVE}; 
                border-radius: 6px; 
                padding: 6px;
                font-size: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {tema.BG_INPUT};
                color: {color_txt};
                selection-background-color: {tema.MENTA_MEDICA};
                selection-color: #1C1C1C;
            }}
        """)

        for cb in [self.check_antecedentes, self.check_referido, self.check_seguro]:
            cb.setStyleSheet(f"color: {color_txt}; font-weight: bold; font-size: 13px; background: transparent;")

        # 4. Re-estilizar etiquetas de formularios e informativas
        for lbl in [self.lbl_etiqueta_fecha, self.lbl_etiqueta_opciones, self.lbl_tit_plantillas, self.lbl_comentario_privado]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 13px; font-weight: bold; background: transparent;")
        
        self.lbl_titulo_redaccion.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_txt}; background: transparent; margin-top: 5px;")

        # 5. Botones tipo Píldora de la Chuleta de Tags
        bg_tag_btn = "#424549" if tema.modo_actual == "oscuro" else "#E2E8F0"
        for btn in self.lista_botones_tags:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_tag_btn}; 
                    border: 1px solid {tema.BORDE_SUAVE}; 
                    border-radius: 6px; 
                    padding: 4px 8px; 
                    color: {color_txt}; 
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {tema.MENTA_MEDICA};
                    color: #1C1C1C;
                    border-color: {tema.MENTA_MEDICA};
                }}
            """)

        # 6. Forzar Hover del Botón PDF
        bg_pdf_hover = "#2C3E50" if tema.modo_actual == "oscuro" else "#1A252F"
        self.btn_generar_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: #34495e; 
                color: white; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 14px; 
                border: none;
            }}
            QPushButton:hover {{
                background-color: {bg_pdf_hover};
                border: 1px solid {tema.MENTA_MEDICA};
            }}
        """)

    # ========================================================
    # LÓGICA DE PLANTILLAS Y BASE DE DATOS
    # ========================================================
    def actualizar_combo_plantillas(self):
        self.combo_plantillas.clear()
        db = SessionLocal()
        plantillas = db.query(PlantillaInforme).order_by(PlantillaInforme.nombre).all()
        for p in plantillas:
            self.combo_plantillas.addItem(p.nombre)
        db.close()

    def guardar_plantilla_actual(self):
        texto = self.in_cuerpo.toPlainText().strip()
        if not texto:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "El área está vacía.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return

        # Ajuste estético para el QInputDialog nativo
        input_dialog = QInputDialog(self)
        input_dialog.setStyleSheet(tema.ESTILO_VENTANA)
        input_dialog.setWindowTitle("Guardar Plantilla")
        input_dialog.setLabelText("Nombre para esta plantilla:")
        ok = input_dialog.exec()
        nombre = input_dialog.textValue()

        if ok and nombre.strip():
            db = SessionLocal()
            existente = db.query(PlantillaInforme).filter(PlantillaInforme.nombre == nombre.strip()).first()
            if existente:
                existente.texto = texto
            else:
                db.add(PlantillaInforme(nombre=nombre.strip(), texto=texto))
            db.query(PlantillaInforme).filter()
            db.commit()
            db.close()
            self.actualizar_combo_plantillas()
            self.combo_plantillas.setCurrentText(nombre.strip())
            box = QMessageBox(QMessageBox.Information, "Éxito", "Plantilla guardada en la base de datos.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()

    def cargar_plantilla_en_cuerpo(self):
        nombre = self.combo_plantillas.currentText()
        if not nombre: return
        
        db = SessionLocal()
        plantilla = db.query(PlantillaInforme).filter(PlantillaInforme.nombre == nombre).first()
        texto_plantilla = plantilla.texto if plantilla else ""
        db.close()
        
        if self.in_cuerpo.toPlainText().strip():
            box = QMessageBox(QMessageBox.Question, "Cargar", "¿Sobrescribir (Yes) o Añadir al final (No)?", 
                              QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, self)
            self.ajustar_emergente_parent(box)
            reply = box.exec()
            if reply == QMessageBox.Cancel: return
            elif reply == QMessageBox.Yes: self.in_cuerpo.setPlainText(texto_plantilla)
            elif reply == QMessageBox.No: self.in_cuerpo.insertPlainText(f"\n\n{texto_plantilla}")
        else:
            self.in_cuerpo.setPlainText(texto_plantilla)

    def eliminar_plantilla_seleccionada(self):
        nombre = self.combo_plantillas.currentText()
        if not nombre: return
        
        box = QMessageBox(QMessageBox.Question, "Confirmar", f"¿Eliminar plantilla '{nombre}'?", QMessageBox.Yes | QMessageBox.No, self)
        self.ajustar_emergente_parent(box)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            plantilla = db.query(PlantillaInforme).filter(PlantillaInforme.nombre == nombre).first()
            if plantilla:
                db.delete(plantilla)
                db.commit()
            db.close()
            self.actualizar_combo_plantillas()

    # ========================================================
    # MAGIA: PROCESADOR DE ETIQUETAS
    # ========================================================
    def insertar_etiqueta(self, etiqueta):
        self.in_cuerpo.insertPlainText(etiqueta)

    def procesar_etiquetas_inteligentes(self):
        if not self.paciente_id:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione un paciente primero.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return
            
        texto = self.in_cuerpo.toPlainText()
        if not texto: return

        db = SessionLocal()
        p = db.query(Paciente).get(self.paciente_id)
        c = db.query(Consulta).filter(Consulta.paciente_id == p.id).order_by(Consulta.fecha_consulta.desc()).first()

        texto = texto.replace("{edad}", str(p.edad_actual) if p else "")
        texto = texto.replace("{motivo}", c.motivo_consulta if c and c.motivo_consulta else "No registrado")
        texto = texto.replace("{enfermedad_actual}", c.enfermedad_actual if c and c.enfermedad_actual else "No registrada")
        
        diag = c.diagnostico if c and c.diagnostico else (c.impresion_diagnostica if c and c.impresion_diagnostica else "No registrado")
        texto = texto.replace("{diagnostico}", diag)

        if "{ex_ficico}" in texto or "{ex_fisico}" in texto or "{examen_fisico}" in texto:
            ef_resumen = ""
            if c:
                biometria = []
                if c.peso: biometria.append(f"Peso: {c.peso} Kg")
                if c.altura: biometria.append(f"Altura: {c.altura} m")
                if c.imc: biometria.append(f"IMC: {c.imc:.2f}")
                if c.tension_arterial and c.tension_arterial != "No aplica": biometria.append(f"TA: {c.tension_arterial}")
                if c.pulso: biometria.append(f"Pulso: {c.pulso} PPM")
                
                if biometria:
                    ef_resumen += " - " + ", ".join(biometria) + "\n"
                
                diccionario_campos_ef = [
                    ("piel", "Piel"), ("ojos", "Ojos"), ("oidos", "Oídos"), 
                    ("orofaringe", "Orofaringe"), ("tiroides", "Tiroides"), 
                    ("axilas", "Axilas"), ("supraclaviculares", "Región Supraclavicular"), 
                    ("abdomen", "Abdomen"), ("lumbar", "Región Lumbar"), 
                    ("neurologico", "Neurológico"), ("mamas", "Mamas"), 
                    ("vulva", "Vulva"), ("vagina", "Vagina"), ("cervix", "Cérvix"), 
                    ("colposcopia", "Colposcopia"), ("tacto_recto_vaginal", "TRVR"),
                    ("pene_testiculos", "Genitales Masculinos"), ("prostata", "Próstata"),
                    ("otros_examen_fisico", "Otros hallazgos físicos")
                ]
                
                for columna_bd, etiqueta_visible in diccionario_campos_ef:
                    if hasattr(c, columna_bd):
                        valor = getattr(c, columna_bd)
                        if valor and valor.strip() and valor.strip() != "No aplica":
                            ef_resumen += f" - {etiqueta_visible}: {valor.strip()}\n"
            
            if not ef_resumen: 
                ef_resumen = " - Sin hallazgos patológicos relevantes en la última consulta.\n"
                
            texto = texto.replace("{ex_ficico}", ef_resumen.rstrip())
            texto = texto.replace("{ex_fisico}", ef_resumen.rstrip())
            texto = texto.replace("{examen_fisico}", ef_resumen.rstrip())

        if "{bloque_referencia}" in texto:
            if self.check_referido.isChecked() and p.referido and p.referido.lower() not in ["no", "ninguno", "n/a", ""]:
                texto = texto.replace("{bloque_referencia}", f"Referido por: Dr(a). {p.referido.title()}")
            else:
                texto = texto.replace("{bloque_referencia}", "") 

        if "{bloque_seguro}" in texto:
            if self.check_seguro.isChecked() and p.seguro and p.seguro.lower() not in ["no", "ninguno", "n/a", ""]:
                texto = texto.replace("{bloque_seguro}", f"Seguro Médico: {p.seguro.title()}")
            else:
                texto = texto.replace("{bloque_seguro}", "") 

        texto = os.linesep.join([s for s in texto.splitlines() if s.strip() or s == ""])
        texto = texto.replace("\n\n\n", "\n\n")

        self.in_cuerpo.setPlainText(texto)
        db.close()

    # ========================================================
    # RESTO DE FUNCIONES (DATOS, ANTECEDENTES Y GUARDADO)
    # ========================================================
    def cargar_datos_paciente(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_cedula.setText(f"<b>CÉDULA:</b> {p.cedula}")
            self.edad_clinica = p.edad_actual
            self.lbl_edad.setText(f"<b>EDAD:</b> {self.edad_clinica} años")
            self.in_cuerpo.clear()
            self.in_comentario.clear()
            self.check_antecedentes.setChecked(False)
            
            tiene_referido = p.referido and p.referido.lower() not in ["no", "ninguno", "n/a", ""]
            tiene_seguro = p.seguro and p.seguro.lower() not in ["no", "ninguno", "n/a", ""]
            
            self.check_referido.setEnabled(bool(tiene_referido))
            self.check_referido.setChecked(bool(tiene_referido))
            self.check_seguro.setEnabled(bool(tiene_seguro))
            self.check_seguro.setChecked(bool(tiene_seguro))
            
        db.close()

    def actualizar_texto_antecedentes(self, checked):
        if not checked or not self.paciente_id: return
        db = SessionLocal()
        p = db.query(Paciente).get(self.paciente_id)
        if p and p.antecedentes:
            ant = p.antecedentes
            texto_ant = "ANTECEDENTES Y EXAMEN FUNCIONAL:\n"
            texto_ant += f"- Alergias: {ant.alergias or 'Negadas'}\n"
            texto_ant += f"- Personales: {ant.personales or 'Sin datos'}\n"
            texto_ant += f"- Familiares: {ant.familiares or 'Sin datos'}\n"
            texto_ant += f"- Operaciones Realizadas: {ant.operaciones_realizadas or 'Sin datos'}\n"
            texto_ant += f"- Hábitos: Fuma ({ant.habito_fuma or 'No aplica'}), Bebe ({ant.habito_bebe or 'No aplica'}), Otros ({ant.otros_habitos or 'No aplica'})\n"
            texto_ant += f"- Examen Funcional: {ant.examen_funcional or 'Sin datos'}\n"
            texto_ant += "-"*40 + "\n\n"
            
            cuerpo_actual = self.in_cuerpo.toPlainText()
            self.in_cuerpo.setPlainText(texto_ant + cuerpo_actual)
        db.close()

    def guardar_datos_informe(self):
        if not self.paciente_id or not self.in_cuerpo.toPlainText().strip():
            box = QMessageBox(QMessageBox.Warning, "Aviso", "El informe está vacío o no hay paciente seleccionado.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return None

        db = SessionLocal()
        try:
            nuevo_inf = InformeMedico(
                paciente_id=self.paciente_id,
                fecha=self.in_fecha.date().toPython(),
                edad_al_momento=self.edad_clinica,
                informe_escrito=self.in_cuerpo.toPlainText(),
                incluir_antecedentes=self.check_antecedentes.isChecked(),
                incluir_referido=self.check_referido.isChecked(),
                incluir_seguro=self.check_seguro.isChecked(),
                comentario=self.in_comentario.text()
            )
            db.add(nuevo_inf)
            db.commit()
            box = QMessageBox(QMessageBox.Information, "Éxito", "Informe guardado en la base de datos.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return nuevo_inf.id
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"No se pudo guardar: {str(e)}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return None
        finally:
            db.close()

    def procesar_documento(self, formato="pdf"):
        id_informe = self.guardar_datos_informe()
        if not id_informe: 
            return

        db = SessionLocal()
        try:
            p = db.query(Paciente).get(self.paciente_id)
            doctor = db.query(PerfilDoctor).first()
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
            ruta_paciente = os.path.join(self.ruta_base, f"{nombre_limpio}_{p.cedula}")
            os.makedirs(ruta_paciente, exist_ok=True)

            # Define extensión y sufijos según el formato solicitado
            ext = ".docx" if formato.lower() == "docx" else ".pdf"
            tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

            # --- LÓGICA DE NOMBRES ÚNICOS ---
            base_name = f"INFORME_{nombre_limpio}_{datetime.now().strftime('%Y-%m-%d')}"
            ruta_completa = os.path.join(ruta_paciente, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_completa):
                ruta_completa = os.path.join(ruta_paciente, f"{base_name}_{contador}{ext}")
                contador += 1
            
            nombre_archivo = os.path.basename(ruta_completa)
            # -------------------------------

            # Llamada al motor pasando el parámetro 'formato'
            ruta_generada = MotorImpresion.generar_pdf_informe(
                doctor=doctor, 
                paciente=p, 
                texto_informe=self.in_cuerpo.toPlainText(),
                ruta_salida=ruta_completa,
                formato=formato
            )

            nuevo_archivo = ArchivoPaciente(
                paciente_id=self.paciente_id,
                nombre_archivo=nombre_archivo,
                ruta_archivo=ruta_generada,
                tipo_archivo=tipo_reg
            )
            db.add(nuevo_archivo)
            db.commit()
            
            # Apertura del archivo generado
            MotorImpresion.abrir_documento_generado(ruta_generada)
            
            box = QMessageBox(QMessageBox.Information, "Documento Generado", f"Informe guardado como {nombre_archivo}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box)
            box.exec()
            
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error al generar", f"Error al generar archivo: {str(e)}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box)
            box.exec()
        finally:
            db.close()