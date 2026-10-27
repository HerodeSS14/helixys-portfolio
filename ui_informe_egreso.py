from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTextEdit, QPushButton, QMessageBox, QFrame, 
                               QScrollArea, QMenu)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QColor, QAction
from database import SessionLocal
from models import Paciente, InformeEgreso, PerfilDoctor, ArchivoPaciente
from servicios_impresion import MotorImpresion
import os
import re
from datetime import datetime
from estilos import tema  # Importación del motor de diseño centralizado

class PantallaInformeEgreso(QWidget):
    volver_historial = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.edad_clinica = 0
        self.ruta_base = "archivos_clinica"

        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)

        # --- 1. CABECERA DE IDENTIFICACIÓN ---
        self.frame_paciente = QFrame()
        lay_h = QVBoxLayout(self.frame_paciente)
        
        lay_datos = QHBoxLayout()
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_cedula = QLabel("<b>CÉDULA:</b> --")
        self.lbl_nacimiento = QLabel("<b>FECHA NAC.:</b> --")
        self.lbl_edad = QLabel("<b>EDAD:</b> --")
        
        lay_datos.addWidget(self.lbl_paciente)
        lay_datos.addWidget(self.lbl_cedula)
        lay_datos.addWidget(self.lbl_nacimiento)
        lay_datos.addWidget(self.lbl_edad)
        
        self.lbl_doctor = QLabel("<b>MÉDICO TRATANTE:</b> --")
        
        lay_h.addLayout(lay_datos)
        lay_h.addWidget(self.lbl_doctor)
        layout_principal.addWidget(self.frame_paciente)

        # --- 2. ÁREA DESPLAZABLE PARA EL FORMULARIO ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        
        self.content = QWidget()
        self.form_vbox = QVBoxLayout(self.content)
        self.form_vbox.setSpacing(15)

        self.lbl_titulo_egreso = QLabel("<h3>🏥 Redacción del Informe de Egreso</h3>")
        self.form_vbox.addWidget(self.lbl_titulo_egreso)

        # Creación dinámica de los campos de texto
        self.campos_texto = {}
        self.lista_labels_dinamicos = []
        secciones = [
            ("Resumen del Egreso", "resumen_egreso"),
            ("Evaluación", "evaluacion"),
            ("Examen Físico", "examen_fisico"),
            ("Paraclínicos", "paraclinicos"),
            ("Diagnóstico de Egreso", "diagnostico_egreso"),
            ("Procedimiento Realizado", "procedimiento_realizado"),
            ("Plan de Manejo", "plan_manejo")
        ]

        for etiqueta, atributo in secciones:
            lbl = QLabel(f"<b>{etiqueta}:</b>")
            txt = QTextEdit()
            txt.setMinimumHeight(120)
            
            self.form_vbox.addWidget(lbl)
            self.form_vbox.addWidget(txt)
            self.campos_texto[atributo] = txt
            self.lista_labels_dinamicos.append(lbl)

        self.scroll.setWidget(self.content)
        layout_principal.addWidget(self.scroll)

        # --- 3. BOTONERA ---
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(12)
        
        self.btn_guardar = QPushButton("💾 GUARDAR INFORME DE EGRESO")
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_ORDEN) # Morado semántico de egresos/órdenes
        self.btn_guardar.setFixedHeight(45)
        self.btn_guardar.clicked.connect(self.guardar_datos)

        # Botón de Generación con menú desplegable para elegir formato
        self.btn_generar_doc = QPushButton("🖨️ GENERAR INFORME DE EGRESO ▾")
        self.btn_generar_doc.setFixedHeight(45)

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
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        
        # 1. Cabecera superior adaptada estilo tarjeta
        self.frame_paciente.setStyleSheet(f"""
            QFrame {{
                background-color: {tema.BG_TARJETA}; 
                border-radius: 10px; 
                border: 1px solid {tema.BORDE_SUAVE};
            }}
            QLabel {{
                color: {color_txt};
                font-size: 13px;
                border: none;
                background: transparent;
            }}
        """)
        self.lbl_paciente.setStyleSheet(f"font-size: 15px; color: {color_txt}; font-weight: bold; background: transparent; border: none;")
        
        color_doctor_txt = "#93F6E3" if tema.modo_actual == "oscuro" else "#2c3e50"
        self.lbl_doctor.setStyleSheet(f"color: {color_doctor_txt}; font-weight: bold; background: transparent; border: none; font-size: 13px;")

        # 2. Control estricto de fondos del QScrollArea y su contenido
        self.scroll.setStyleSheet(f"background-color: {tema.BG_PRINCIPAL}; border: none;")
        self.content.setStyleSheet(f"background-color: {tema.BG_PRINCIPAL}; border: none;")

        # 3. Estilo unificado para los títulos y etiquetas internas del formulario
        self.lbl_titulo_egreso.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_txt}; background: transparent;")
        
        for lbl in self.lista_labels_dinamicos:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 13px; font-weight: bold; background: transparent;")

        # 4. Estilo unificado y reactivo para las cajas de entrada de texto (QTextEdit)
        for txt in self.campos_texto.values():
            txt.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {tema.BG_INPUT}; 
                    color: {color_txt}; 
                    font-size: 14px; 
                    padding: 12px; 
                    border: 1px solid {tema.BORDE_SUAVE}; 
                    border-radius: 8px;
                }}
                QTextEdit:focus {{ border: 2px solid {tema.MENTA_MEDICA}; }}
            """)

        # 5. Forzar hover y diseño del botón de Generar Documento corporativo
        bg_pdf_hover = "#2C3E50" if tema.modo_actual == "oscuro" else "#1A252F"
        self.btn_generar_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: #34495e; 
                color: white; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 14px; 
                border: none;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {bg_pdf_hover};
                border: 1px solid {tema.MENTA_MEDICA};
            }}
        """)

    # ========================================================
    # LÓGICA DE PACIENTES Y BASE DE DATOS
    # ========================================================
    def cargar_datos_paciente(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        doctor = db.query(PerfilDoctor).first()
        
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_cedula.setText(f"<b>CÉDULA:</b> {p.cedula}")
            nacimiento_str = p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else "No registrada"
            self.lbl_nacimiento.setText(f"<b>FECHA NAC.:</b> {nacimiento_str}")
            self.edad_clinica = p.edad_actual
            self.lbl_edad.setText(f"<b>EDAD:</b> {self.edad_clinica} años")
            
            for txt in self.campos_texto.values():
                txt.clear()
        
        if doctor:
            self.lbl_doctor.setText(f"<b>MÉDICO TRATANTE:</b> Dr(a). {doctor.nombre_doctor}")
        else:
            self.lbl_doctor.setText("<b>MÉDICO TRATANTE:</b> No configurado en el perfil")
            
        db.close()

    def guardar_datos(self):
        if not self.paciente_id:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "No hay paciente seleccionado.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return None

        db = SessionLocal()
        try:
            nuevo_egreso = InformeEgreso(
                paciente_id=self.paciente_id,
                fecha=datetime.now(),
                edad_al_momento=self.edad_clinica,
                resumen_egreso=self.campos_texto["resumen_egreso"].toPlainText(),
                evaluacion=self.campos_texto["evaluacion"].toPlainText(),
                examen_fisico=self.campos_texto["examen_fisico"].toPlainText(),
                paraclinicos=self.campos_texto["paraclinicos"].toPlainText(),
                diagnostico_egreso=self.campos_texto["diagnostico_egreso"].toPlainText(),
                procedimiento_realizado=self.campos_texto["procedimiento_realizado"].toPlainText(),
                plan_manejo=self.campos_texto["plan_manejo"].toPlainText()
            )
            db.add(nuevo_egreso)
            db.commit()
            box = QMessageBox(QMessageBox.Information, "Éxito", "Informe de Egreso guardado en la base de datos.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return nuevo_egreso.id
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"No se pudo guardar: {str(e)}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
            return None
        finally:
            db.close()

    def procesar_documento(self, formato="pdf"):
        id_egreso = self.guardar_datos()
        if not id_egreso: return

        db = SessionLocal()
        try:
            p = db.query(Paciente).get(self.paciente_id)
            doctor = db.query(PerfilDoctor).first()
            egreso = db.query(InformeEgreso).get(id_egreso)
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
            ruta_paciente = os.path.join(self.ruta_base, f"{nombre_limpio}_{p.cedula}")
            os.makedirs(ruta_paciente, exist_ok=True)

            ext = ".docx" if formato.lower() == "docx" else ".pdf"
            tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

            # --- LÓGICA DE NOMBRES ÚNICOS CON CONTADOR ---
            base_name = f"EGRESO_{nombre_limpio}_{datetime.now().strftime('%Y-%m-%d')}"
            ruta_salida = os.path.join(ruta_paciente, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_salida):
                ruta_salida = os.path.join(ruta_paciente, f"{base_name}_{contador}{ext}")
                contador += 1
                
            nombre_archivo = os.path.basename(ruta_salida)
            # ---------------------------------------------

            if hasattr(MotorImpresion, 'generar_pdf_egreso'):
                ruta_generada = MotorImpresion.generar_pdf_egreso(
                    doctor=doctor, 
                    paciente=p, 
                    egreso=egreso, 
                    ruta_salida=ruta_salida, 
                    formato=formato
                )
            else:
                box = QMessageBox(QMessageBox.Warning, "Pendiente", "Falta crear el diseño para Egresos en servicios_impresion.py", QMessageBox.Ok, self)
                self.ajustar_emergente_parent(box); box.exec()
                return

            nuevo_archivo = ArchivoPaciente(
                paciente_id=self.paciente_id,
                nombre_archivo=nombre_archivo,
                ruta_archivo=ruta_generada,
                tipo_archivo=tipo_reg
            )
            db.add(nuevo_archivo)
            db.commit()
            
            MotorImpresion.abrir_documento_generado(ruta_generada)
            self.volver_historial.emit()
            
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error al generar", f"Error al generar archivo: {str(e)}", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec()
        finally:
            db.close()