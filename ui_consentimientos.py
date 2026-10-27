from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                               QLabel, QFrame, QScrollArea, QGroupBox, QSplitter, QDialog, QSizePolicy, QMenu)
from PySide6.QtGui import QDesktopServices, QColor, QAction
from database import SessionLocal
from models import Paciente, ConsentimientoCirugia, PerfilDoctor, ArchivoPaciente
from servicios_impresion import MotorImpresion
import os
import re
from datetime import datetime
from estilos import tema  # Motor de diseño centralizado

# --- LA PLANTILLA MAESTRA ---
PLANTILLA_BASE = """Yo, [PACIENTE], CI: [CEDULA_PACIENTE], mayor de edad y en pleno uso de mis facultades mentales autorizo al Dr(a). [DOCTOR], CI: [CEDULA_DOCTOR], médico, especialista en [ESPECIALIDAD], matrícula del MSDS: [MSDS] a actuar como médico tratante, cirujano principal, y los ayudantes que designe, en la intervención quirúrgica que a continuación se describe:

«[INTERVENCION]»

y que entiendo es un procedimiento médico estándar para el tratamiento de la enfermedad que padezco y cuyo diagnóstico es:

«[DIAGNOSTICO]»

Entiendo que la práctica de la medicina y la cirugía no son una ciencia exacta, debiendo el médico colocar todo su conocimiento y su pericia en buscar los mejores resultados con el objetivo de mejorar el problema por el cual consulté. Entiendo que puede haber cambio de conducta y/o técnica quirúrgica según hallazgos intraoperatorios. Entiendo que en toda intervención quirúrgica se pueden presentar complicaciones por causas independientes del actuar de mi médico, complicaciones comunes y potencialmente serias que podrían requerir tratamientos complementarios, tanto médicos como quirúrgicos, siendo las complicaciones más frecuentes: náuseas, vómitos, dolor, inflamación, moretones, hematomas (acumulación de sangre), cistitis, retención urinaria, sangrado o hemorragias con la posible necesidad de transfusión (intra o postoperatoria) y re intervención, así como infecciones con posible evolución febril (urinarias, de pared abdominal, pélvicas, pulmonares), reacciones alérgicas, irritación frénica, hipo, anemia, heridas involuntarias en vasos sanguíneos, vejiga, intestinos, perforación de útero u otros órganos, fístulas.

Existen otras complicaciones o secuelas como: Neumonía, Embolismo Pulmonar, Trombosis venosa profunda. También se me informa la posibilidad de complicaciones severas como sepsis, shock hemorrágico o trombosis que, aunque son poco frecuentes, representan, como en toda intervención quirúrgica, un riesgo excepcional de perder la vida derivado del acto quirúrgico o de la situación vital de cada paciente.

En mi caso particular, el (la) doctor(a) me ha explicado que presento los siguientes riesgos adicionales:

«[RIESGOS]»

Entiendo que para esta cirugía se necesita anestesia, la cual se evaluará y realizará por el Servicio de Anestesia. Entiendo que, si es necesario extraer algún tejido, se someterá a estudio. He entendido las condiciones and objetivos de la cirugía que se me va a practicar, los cuidados que debo tener antes y después de ella, estoy satisfecho(a) con la información recibida del médico tratante quien lo ha hecho en un lenguaje claro y sencillo, y me ha dado la oportunidad de preguntar y resolver las dudas a satisfacción, además comprendo y acepto el alcance y los riesgos justificados de posible previsión que conlleva el procedimiento quirúrgico que aquí autorizo.

Autorizo también de manera expresa la toma de fotografías, videos e imágenes en formato físico y/o digital para documentar mi patología, así como para el intercambio de información y conocimientos médicos en revistas biomédicas, congresos médicos y seminarios de carácter científico, siempre y cuando mi identidad o mi condición de paciente no sea revelada a terceros, comprometiéndose mi médico tratante a proteger mi anonimato.

En tales condiciones consiento que se me realice la cirugía arriba mencionada.[BLOQUE_TESTIGO]"""


class DialogoPlantilla(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personalizar Plantilla Legal")
        self.setMinimumSize(850, 650)
        
        # Heredar el color de fondo general de ventanas modales
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout = QVBoxLayout(self)
        
        self.lbl_info = QLabel("<b>Etiquetas disponibles:</b> [PACIENTE], [CEDULA_PACIENTE], [DOCTOR], [CEDULA_DOCTOR], [ESPECIALIDAD], [MSDS], [INTERVENCION], [DIAGNOSTICO], [RIESGOS], [BLOQUE_TESTIGO]")
        layout.addWidget(self.lbl_info)
        
        self.editor = QTextEdit()
        layout.addWidget(self.editor)
        
        self.btn_guardar = QPushButton("💾 Guardar Plantilla")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.clicked.connect(self.guardar_plantilla)
        layout.addWidget(self.btn_guardar)
        
        # Conexión reactiva al diseño dinámico
        self.actualizar_diseno_emergente()
        self.cargar_plantilla()

    def actualizar_emergente_parent(self, box):
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def actualizar_diseno_emergente(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        bg_banner = "#2c3e50" if tema.modo_actual == "oscuro" else "#ecf0f1"
        txt_banner = "#93F6E3" if tema.modo_actual == "oscuro" else "#2980b9"

        self.lbl_info.setStyleSheet(f"color: {txt_banner}; background: {bg_banner}; padding: 10px; border-radius: 5px; font-size: 13px;")
        
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 10px;
                border-radius: 6px;
            }}
            QTextEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
            }}
        """)
        
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)

    def cargar_plantilla(self):
        db = SessionLocal()
        doctor = db.query(PerfilDoctor).first()
        if doctor and hasattr(doctor, 'plantilla_consentimiento') and doctor.plantilla_consentimiento:
            self.editor.setPlainText(doctor.plantilla_consentimiento)
        else:
            self.editor.setPlainText(PLANTILLA_BASE)
        db.close()

    def guardar_plantilla(self):
        db = SessionLocal()
        doctor = db.query(PerfilDoctor).first()
        if not doctor:
            box = QMessageBox(QMessageBox.Warning, "Error", "Debe configurar el perfil del doctor primero.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
            db.close(); return
            
        try:
            doctor.plantilla_consentimiento = self.editor.toPlainText()
            db.commit()
            box = QMessageBox(QMessageBox.Information, "Éxito", "Plantilla legal actualizada correctamente.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
            self.accept()
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error de Estructura", "Por favor asegúrese de haber añadido la columna 'plantilla_consentimiento' en su base de datos.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
        finally:
            db.close()


class PantallaConsentimiento(QWidget):
    solicitar_historial = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_actual_id = None
        self.dict_datos_doctor = {}
        self.plantilla_actual = ""
        self.paciente_nombre = ""
        self.paciente_cedula = ""
        
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)

        # --- 1. CABECERA 
        self.frame_header = QFrame()
        self.frame_header.setMaximumHeight(60) 
        
        layout_h = QHBoxLayout(self.frame_header)
        layout_h.setContentsMargins(15, 5, 15, 5) 
        
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_id = QLabel("<b>ID:</b> --")
        
        self.btn_volver = QPushButton("⬅️ Volver al Historial")
        self.btn_volver.setFixedHeight(32) 
        self.btn_volver.clicked.connect(self.ejecutar_retorno_historial)
        
        self.btn_plantilla = QPushButton("⚙️ Configurar Plantilla Legal")
        self.btn_plantilla.setFixedHeight(32) 
        self.btn_plantilla.clicked.connect(self.abrir_editor_plantilla)
        
        layout_h.addWidget(self.lbl_paciente)
        layout_h.addWidget(self.lbl_id)
        layout_h.addStretch()
        layout_h.addWidget(self.btn_plantilla)
        layout_h.addWidget(self.btn_volver)
        layout_principal.addWidget(self.frame_header)

        # --- 2. SPLITTER ---
        self.splitter = QSplitter(Qt.Horizontal)
        
        # PANEL IZQUIERDO: FORMULARIO
        self.panel_formulario = QWidget()
        lay_form_main = QVBoxLayout(self.panel_formulario)
        lay_form_main.setContentsMargins(0, 0, 10, 0)
        lay_form_main.setSpacing(10)
        
        # 1. Datos del Procedimiento
        self.group_proc = QGroupBox("⚕️ Datos del Procedimiento")
        self.group_proc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        lay_proc = QFormLayout(self.group_proc)
        lay_proc.setSpacing(12)
        
        self.lbl_form_diag = QLabel("Diagnóstico:")
        self.in_diagnostico = QLineEdit()
        self.lbl_form_inter = QLabel("Intervención:")
        self.in_intervencion = QLineEdit()
        self.lbl_form_ries = QLabel("Riesgos:")
        self.in_riesgos = QTextEdit()
        
        lay_proc.addRow(self.lbl_form_diag, self.in_diagnostico)
        lay_proc.addRow(self.lbl_form_inter, self.in_intervencion)
        lay_proc.addRow(self.lbl_form_ries, self.in_riesgos)
        lay_form_main.addWidget(self.group_proc)
        
        # 2. Familiar / Testigo
        self.group_fam = QGroupBox("👥 Familiar / Testigo (Si queda vacío, no saldrá en el PDF)")
        self.group_fam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        lay_fam = QFormLayout(self.group_fam)
        lay_fam.setSpacing(12)
        
        self.lbl_form_test_nom = QLabel("Nombre:")
        self.in_fam_nombre = QLineEdit()
        self.lbl_form_test_ced = QLabel("Cédula:")
        self.in_fam_cedula = QLineEdit()
        
        lay_fam.addRow(self.lbl_form_test_nom, self.in_fam_nombre)
        lay_fam.addRow(self.lbl_form_test_ced, self.in_fam_cedula)
        lay_form_main.addWidget(self.group_fam)
        
        # 3. Botón Maestro de Guardar con Menú Desplegable (PDF / Word)
        self.btn_generar_doc = QPushButton("💾 GUARDAR Y GENERAR DOCUMENTO ▾")
        self.btn_generar_doc.setFixedHeight(50)

        menu_impresion = QMenu(self)
        menu_impresion.setStyleSheet(tema.ESTILO_VENTANA)

        action_pdf = QAction("📄 Generar en PDF (.pdf)", self)
        action_pdf.triggered.connect(lambda: self.guardar_y_imprimir(formato="pdf"))

        action_docx = QAction("📝 Generar en Word (.docx)", self)
        action_docx.triggered.connect(lambda: self.guardar_y_imprimir(formato="docx"))

        menu_impresion.addAction(action_pdf)
        menu_impresion.addAction(action_docx)

        self.btn_generar_doc.setMenu(menu_impresion)
        lay_form_main.addWidget(self.btn_generar_doc)

        # PANEL DERECHO: VISTA PREVIA
        self.panel_vista = QWidget()
        lay_vista = QVBoxLayout(self.panel_vista)
        lay_vista.setContentsMargins(10, 0, 0, 0)
        
        self.lbl_tit_preview = QLabel("<b>📄 Vista Previa:</b>")
        self.visor_legal = QTextEdit()
        self.visor_legal.setReadOnly(True)
        
        lay_vista.addWidget(self.lbl_tit_preview)
        lay_vista.addWidget(self.visor_legal)

        self.splitter.addWidget(self.panel_formulario)
        self.splitter.addWidget(self.panel_vista)
        self.splitter.setSizes([420, 580])
        layout_principal.addWidget(self.splitter)

        # Conexiones reactivas en tiempo real
        self.in_diagnostico.textChanged.connect(self.actualizar_vista_previa)
        self.in_intervencion.textChanged.connect(self.actualizar_vista_previa)
        self.in_riesgos.textChanged.connect(self.actualizar_vista_previa)
        self.in_fam_nombre.textChanged.connect(self.actualizar_vista_previa)
        self.in_fam_cedula.textChanged.connect(self.actualizar_vista_previa)

        # Conectar reactividad central
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def actualizar_emergente_parent(self, box):
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def ejecutar_retorno_historial(self):
        if self.paciente_actual_id:
            self.solicitar_historial.emit(self.paciente_actual_id)

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        # 1. Cabecera superior unificada
        border_head = "#4f545c" if tema.modo_actual == "oscuro" else "#bdc3c7"
        bg_head = tema.BG_TARJETA if tema.modo_actual == "oscuro" else "#ecf0f1"
        self.frame_header.setStyleSheet(f"background-color: {bg_head}; border-radius: 10px; border: 1px solid {border_head}; padding: 5px;")
        
        self.lbl_paciente.setStyleSheet(f"color: {color_txt}; font-size: 15px; background: transparent; border: none;")
        self.lbl_id.setStyleSheet(f"color: {color_txt}; font-size: 15px; background: transparent; border: none;")
        
        self.btn_volver.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_plantilla.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)

        # 2. Splitter e Interiores de Paneles
        self.panel_formulario.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.panel_vista.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        
        # Línea divisoria del Splitter estilizada
        color_div = tema.BORDE_SUAVE if tema.modo_actual == "oscuro" else "#bdc3c7"
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {color_div}; width: 2px; }}")

        # Labels del Formulario
        for l_form in [self.lbl_form_diag, self.lbl_form_inter, self.lbl_form_ries, self.lbl_form_test_nom, self.lbl_form_test_ced, self.lbl_tit_preview]:
            l_form.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent;")

        # GroupBoxes corporativos
        style_group = f"""
            QGroupBox {{
                color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'};
                font-weight: bold;
                font-size: 14px;
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
            }}
        """
        self.group_proc.setStyleSheet(style_group)
        self.group_fam.setStyleSheet(style_group)

        # 3. Blindar Inputs (Líneas y Cajas de Texto)
        style_inputs = f"""
            QLineEdit, QTextEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 8px;
                border-radius: 5px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
            }}
        """
        for w in [self.in_diagnostico, self.in_intervencion, self.in_riesgos, self.in_fam_nombre, self.in_fam_cedula]:
            w.setStyleSheet(style_inputs)

        # 4. Visor Legal de Documentos
        color_fondo_visor = "#2d3033" if tema.modo_actual == "oscuro" else "#fcfcfc"
        color_txt_visor = "#E0E0E0" if tema.modo_actual == "oscuro" else "#2c3e50"
        border_visor = tema.BORDE_SUAVE if tema.modo_actual == "oscuro" else "#ccc"
        
        self.visor_legal.setStyleSheet(f"""
            QTextEdit {{
                background-color: {color_fondo_visor}; 
                border: 1px solid {border_visor}; 
                font-family: 'Times New Roman'; 
                font-size: 16px; 
                padding: 20px; 
                color: {color_txt_visor};
                border-radius: 6px;
            }}
        """)

        # Botón Maestro de Guardado
        self.btn_generar_doc.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        
        # Forzar refresco visual instantáneo del visor HTML
        self.actualizar_vista_previa()

    def abrir_editor_plantilla(self):
        dlg = DialogoPlantilla(self)
        if dlg.exec():
            self.cargar_datos_doctor()
            self.actualizar_vista_previa()

    def cargar_datos_doctor(self):
        db = SessionLocal()
        doctor = db.query(PerfilDoctor).first()
        if doctor:
            self.dict_datos_doctor = {
                "[DOCTOR]": doctor.nombre_doctor or "___",
                "[CEDULA_DOCTOR]": doctor.cedula_doctor or "___",
                "[ESPECIALIDAD]": doctor.especialidades or "___",
                "[MSDS]": doctor.matricula_msds or "___",
            }
            if hasattr(doctor, 'plantilla_consentimiento') and doctor.plantilla_consentimiento:
                self.plantilla_actual = doctor.plantilla_consentimiento
            else:
                self.plantilla_actual = PLANTILLA_BASE
        db.close()

    def cargar_datos_paciente(self, paciente_id):
        self.limpiar_todo()
        self.paciente_actual_id = paciente_id
        self.cargar_datos_doctor()
        
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_id.setText(f"<b>ID:</b> {p.cedula}")
            self.paciente_nombre = p.nombre_completo
            self.paciente_cedula = p.cedula
            
            ultima_consulta = p.consultas[-1] if p.consultas else None
            if ultima_consulta and ultima_consulta.enfermedad_actual:
                self.in_diagnostico.setText(ultima_consulta.enfermedad_actual[:100])
        db.close()
        self.actualizar_vista_previa()

    def actualizar_vista_previa(self):
        if not self.paciente_actual_id: return
        
        texto_final = self.plantilla_actual
        
        # Reemplazar tags del doctor
        for tag, valor in self.dict_datos_doctor.items():
            texto_final = texto_final.replace(tag, valor)
            
        # Reemplazar tags estáticos del paciente
        texto_final = texto_final.replace("[PACIENTE]", f"<b>{self.paciente_nombre}</b>")
        texto_final = texto_final.replace("[CEDULA_PACIENTE]", f"<b>{self.paciente_cedula}</b>")
        
        # Reemplazar campos del formulario dinámico
        texto_final = texto_final.replace("[DIAGNOSTICO]", f"<b>{self.in_diagnostico.text().strip() or '___'}</b>")
        texto_final = texto_final.replace("[INTERVENCION]", f"<b>{self.in_intervencion.text().strip() or '___'}</b>")
        texto_final = texto_final.replace("[RIESGOS]", f"<b>{self.in_riesgos.toPlainText().strip() or '___'}</b>")
        
        # Estructuración condicional del Testigo/Familiar
        f_nom = self.in_fam_nombre.text().strip()
        f_ced = self.in_fam_cedula.text().strip()
        if f_nom:
            txt_testigo = f"<br><br>Actuando en representación de mi familiar <b>{f_nom}</b> (C.I. {f_ced})."
        else:
            txt_testigo = ""
        texto_final = texto_final.replace("[BLOQUE_TESTIGO]", txt_testigo)
        
        # Ajustar colores HTML internos del visor según el tema activo para contraste óptimo
        color_html_txt = "#E0E0E0" if tema.modo_actual == "oscuro" else "#2c3e50"
        html = f"<div style='text-align: justify; line-height: 1.6; color: {color_html_txt};'>{texto_final.replace(chr(10), '<br>')}</div>"
        self.visor_legal.setHtml(html)

    def guardar_y_imprimir(self, formato="pdf"):
        if not self.in_intervencion.text().strip() or not self.in_diagnostico.text().strip():
            box = QMessageBox(QMessageBox.Warning, "Incompleto", "Debe llenar al menos el Diagnóstico y la Intervención para procesar el marco legal.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
            return

        db = SessionLocal()
        try:
            doctor = db.query(PerfilDoctor).first()
            nuevo_consentimiento = ConsentimientoCirugia(
                paciente_id=self.paciente_actual_id,
                intervencion=self.in_intervencion.text().strip(),
                diagnostico=self.in_diagnostico.text().strip(),
                riesgos_especificos=self.in_riesgos.toPlainText().strip(),
                familiar_nombre=self.in_fam_nombre.text().strip() or None,
                familiar_cedula=self.in_fam_cedula.text().strip() or None
            )
            db.add(nuevo_consentimiento)
            db.commit()
            
            p = db.query(Paciente).get(self.paciente_actual_id)
            nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
            ruta_folder = os.path.join("archivos_clinica", f"{nombre_limpio}_{p.cedula}")
            os.makedirs(ruta_folder, exist_ok=True)
            
            ext = ".docx" if formato.lower() == "docx" else ".pdf"
            tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

            # --- LÓGICA DE NOMBRES ÚNICOS CON CONTADOR ---
            base_name = f"CONSENTIMIENTO_{nombre_limpio}_{datetime.now().strftime('%Y-%m-%d')}"
            ruta_salida = os.path.join(ruta_folder, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_salida):
                ruta_salida = os.path.join(ruta_folder, f"{base_name}_{contador}{ext}")
                contador += 1
                
            nombre_archivo = os.path.basename(ruta_salida)
            # ---------------------------------------------
            
            # Compilación del documento digital (PDF o DOCX)
           # Compilación del documento digital (PDF o DOCX)
            ruta_generada = MotorImpresion.generar_pdf_consentimiento(
                doctor, 
                p, 
                nuevo_consentimiento, 
                self.plantilla_actual, 
                ruta_salida,
                formato
            )
            
            nuevo_archivo = ArchivoPaciente(
                paciente_id=self.paciente_actual_id,
                nombre_archivo=nombre_archivo,
                ruta_archivo=ruta_generada,
                tipo_archivo=tipo_reg
            )
            db.add(nuevo_archivo)
            db.commit()

            MotorImpresion.abrir_documento_generado(ruta_generada)
            
            box = QMessageBox(QMessageBox.Information, "Éxito", "Consentimiento quirúrgico guardado y generado correctamente.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
            
            self.limpiar_todo()
            self.solicitar_historial.emit(self.paciente_actual_id)
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error Quirúrgico", f"Fallo al compilar los registros médicos: {str(e)}", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec()
        finally: 
            db.close()

    def limpiar_todo(self):
        self.in_diagnostico.clear()
        self.in_intervencion.clear()
        self.in_riesgos.clear()
        self.in_fam_nombre.clear()
        self.in_fam_cedula.clear()
        self.visor_legal.clear()