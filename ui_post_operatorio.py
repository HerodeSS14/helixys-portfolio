from PySide6.QtWidgets import (QMenu, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QMessageBox, QFrame, 
                             QScrollArea)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QColor
from database import SessionLocal
from models import Paciente, NotaOperatoria, PerfilDoctor, ArchivoPaciente
from servicios_impresion import MotorImpresion
import os
import re
from datetime import datetime
from estilos import tema  # Motor de diseño centralizado

class PantallaPostOperatorio(QWidget):
    volver_historial = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.edad_clinica = 0
        self.ruta_base = "archivos_clinica"

        layout_principal = QVBoxLayout(self)

        # --- 1. CABECERA DE IDENTIFICACIÓN ---
        self.frame_paciente = QFrame()
        lay_v = QVBoxLayout(self.frame_paciente)
        
        lay_datos = QHBoxLayout()
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_cedula = QLabel("<b>CÉDULA:</b> --")
        self.lbl_nacimiento = QLabel("<b>FECHA NAC.:</b> --")
        self.lbl_edad = QLabel("<b>EDAD:</b> --")
        
        lay_datos.addWidget(self.lbl_paciente)
        lay_datos.addWidget(self.lbl_cedula)
        lay_datos.addWidget(self.lbl_nacimiento)
        lay_datos.addWidget(self.lbl_edad)
        
        self.lbl_doctor = QLabel("<b>MÉDICO / ESPECIALIDADES:</b> --")
        
        lay_v.addLayout(lay_datos)
        lay_v.addWidget(self.lbl_doctor)
        layout_principal.addWidget(self.frame_paciente)

        # --- 2. ÁREA DESPLAZABLE PARA EL FORMULARIO ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.form_vbox = QVBoxLayout(self.scroll_content)
        self.form_vbox.setSpacing(15)

        self.lbl_titulo = QLabel("<h3>Protocolo / Informe Post-Operatorio</h3>")
        self.form_vbox.addWidget(self.lbl_titulo)

        # Secciones del formulario quirúrgico
        self.campos_texto = {}
        self.labels_secciones = []
        secciones = [
            ("Diagnóstico Pre-operatorio", "diagnostico_pre"),
            ("Cirugía Realizada", "cirugia_realizada"),
            ("Diagnóstico Post-operatorio", "diagnostico_post"),
            ("Descripción detallada de la intervención", "descripcion_detallada"),
            ("Hallazgos", "hallazgos"),
            ("Biopsia", "biopsia"),
            ("Plan de Manejo", "plan_manejo")
        ]

        # Configuración de colores iniciales para evitar parpadeos de Qt al renderizar
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        for etiqueta, atributo in secciones:
            lbl = QLabel(f"<b>{etiqueta}:</b>")
            txt = QTextEdit()
            txt.setMinimumHeight(120)
            
            # Blindaje nativo focus al instanciar
            txt.setStyleSheet(f"""
                QTextEdit {{
                    border: {border_entry}; 
                    background-color: {color_fondo_entry}; 
                    color: {color_txt}; 
                    font-size: 15px; 
                    padding: 10px;
                    border-radius: 5px;
                }}
                QTextEdit:focus {{
                    border: 1px solid {tema.MENTA_MEDICA};
                    background-color: {color_fondo_entry};
                    color: {color_txt}; 
                }}
            """)
            
            self.form_vbox.addWidget(lbl)
            self.form_vbox.addWidget(txt)
            self.campos_texto[atributo] = txt
            self.labels_secciones.append(lbl)

        self.scroll.setWidget(self.scroll_content)
        layout_principal.addWidget(self.scroll)

        # --- 3. BOTONERA ---
        btns_layout = QHBoxLayout()
        
        self.btn_guardar = QPushButton("💾 GUARDAR POST-OPERATORIO")
        self.btn_guardar.setFixedHeight(45)
        self.btn_guardar.clicked.connect(lambda: self.guardar_datos())

        # --- BOTÓN DE GENERACIÓN CON MENÚ DE FORMATOS (PDF / WORD) ---
        self.btn_generar_doc = QPushButton("🖨️ GENERAR INFORME ▾")
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

        # Conectar reactividad de diseño centralizado
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        # Refrescar cuadro superior del paciente
        border_head = "#4f545c" if tema.modo_actual == "oscuro" else "#feb2b2"
        bg_head = tema.BG_TARJETA if tema.modo_actual == "oscuro" else "#fff5f5"
        self.frame_paciente.setStyleSheet(f"background-color: {bg_head}; border-radius: 10px; border: 1px solid {border_head};")
        
        for lbl in [self.lbl_paciente, self.lbl_cedula, self.lbl_nacimiento, self.lbl_edad]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")
        
        color_doctor_txt = "#93F6E3" if tema.modo_actual == "oscuro" else "#c53030"
        self.lbl_doctor.setStyleSheet(f"color: {color_doctor_txt}; font-weight: bold; font-size: 15px; border: none; background: transparent;")

        # Estilo del scroll viewport
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {color_fondo_paginas}; }}")
        self.scroll_content.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.lbl_titulo.setStyleSheet(f"color: {color_txt}; background: transparent;")

        for lbl in self.labels_secciones:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent;")

        # Actualización en caliente de cajas de texto con persistencia en focus
        for txt in self.campos_texto.values():
            txt.setStyleSheet(f"""
                QTextEdit {{
                    border: {border_entry}; 
                    background-color: {color_fondo_entry}; 
                    color: {color_txt}; 
                    font-size: 15px; 
                    padding: 10px;
                    border-radius: 5px;
                }}
                QTextEdit:focus {{
                    border: 1px solid {tema.MENTA_MEDICA};
                    background-color: {color_fondo_entry}; 
                    color: {color_txt}; 
                }}
            """)

        # Aplicación limpia de estilos a botones
        # Aplicación limpia de estilos a botones
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        
        bg_dark_btn = "#2d3748" if tema.modo_actual == "oscuro" else "#1A202C"
        self.btn_generar_doc.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_dark_btn}; 
                color: white; 
                font-weight: bold; 
                font-size: 14px; 
                border-radius: 5px; 
                border: none;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: #4A5568;
                border: 1px solid {tema.MENTA_MEDICA};
            }}
        """)

    def cargar_datos_paciente(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        doctor = db.query(PerfilDoctor).first()
        
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_cedula.setText(f"<b>CÉDULA:</b> {p.cedula}")
            nac_str = p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else "S/D"
            self.lbl_nacimiento.setText(f"<b>FECHA NAC.:</b> {nac_str}")
            self.edad_clinica = p.edad_actual
            self.lbl_edad.setText(f"<b>EDAD:</b> {self.edad_clinica} años")
            
            for txt in self.campos_texto.values():
                txt.clear()
        
        if doctor:
            self.lbl_doctor.setText(f"<b>MÉDICO:</b> {doctor.nombre_doctor} | {doctor.especialidades}")
        db.close()

    def guardar_datos(self):
        if not self.paciente_id:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione un paciente primero.", QMessageBox.Ok, self)
            box.setWindowFlags(box.windowFlags() | Qt.Dialog)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            return None

        db = SessionLocal()
        try:
            nueva_nota = NotaOperatoria(
                paciente_id=self.paciente_id,
                fecha=datetime.now(),
                edad_al_momento=self.edad_clinica,
                diagnostico_preoperatorio=self.campos_texto["diagnostico_pre"].toPlainText(),
                cirugia_realizada=self.campos_texto["cirugia_realizada"].toPlainText(),
                diagnostico_postoperatorio=self.campos_texto["diagnostico_post"].toPlainText(),
                descripcion_intervencion=self.campos_texto["descripcion_detallada"].toPlainText(),
                hallazgos=self.campos_texto["hallazgos"].toPlainText(),
                biopsia=self.campos_texto["biopsia"].toPlainText(),
                plan_manejo=self.campos_texto["plan_manejo"].toPlainText()
            )
            db.add(nueva_nota)
            db.commit()
            
            # Guardamos el ID antes de cerrar la sesión
            id_guardado = nueva_nota.id
            
            box = QMessageBox(QMessageBox.Information, "Éxito", "Informe Post-operatorio guardado con éxito.", QMessageBox.Ok, self)
            box.setWindowFlags(box.windowFlags() | Qt.Dialog)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            
            return id_guardado
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"Fallo en base de datos: {str(e)}", QMessageBox.Ok, self)
            box.setWindowFlags(box.windowFlags() | Qt.Dialog)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            return None
        finally:
            db.close()

    def procesar_documento(self, formato="pdf"):
        # Ejecuta el guardado y captura el ID limpio
        id_nota = self.guardar_datos()
        if not id_nota: 
            return # Evita continuar si falló el guardado o no hay paciente

        db = SessionLocal()
        try:
            p = db.query(Paciente).get(self.paciente_id)
            doctor = db.query(PerfilDoctor).first()
            nota = db.query(NotaOperatoria).get(id_nota)
            
            nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
            ruta_paciente = os.path.join(self.ruta_base, f"{nombre_limpio}_{p.cedula}")
            os.makedirs(ruta_paciente, exist_ok=True)

            ext = ".docx" if formato.lower() == "docx" else ".pdf"
            tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

            # --- LÓGICA DE NOMBRES ÚNICOS CON CONTADOR ---
            base_name = f"POSTOP_{nombre_limpio}_{datetime.now().strftime('%Y-%m-%d')}"
            ruta_salida = os.path.join(ruta_paciente, f"{base_name}{ext}")
            
            contador = 1
            while os.path.exists(ruta_salida):
                ruta_salida = os.path.join(ruta_paciente, f"{base_name}_{contador}{ext}")
                contador += 1
                
            nombre_archivo = os.path.basename(ruta_salida)
            # ---------------------------------------------

            if hasattr(MotorImpresion, 'generar_pdf_postop'):
                ruta_generada = MotorImpresion.generar_pdf_postop(
                    doctor=doctor, 
                    paciente=p, 
                    nota=nota, 
                    ruta_salida=ruta_salida, 
                    formato=formato
                )
            else:
                box = QMessageBox(QMessageBox.Warning, "Pendiente", "Diseño para Post-operatorio pendiente en servicios_impresion.py", QMessageBox.Ok, self)
                box.setWindowFlags(box.windowFlags() | Qt.Dialog)
                box.setStyleSheet(tema.ESTILO_VENTANA)
                box.exec()
                return

            db.add(ArchivoPaciente(
                paciente_id=self.paciente_id, 
                nombre_archivo=nombre_archivo, 
                ruta_archivo=ruta_generada, 
                tipo_archivo=tipo_reg
            ))
            db.commit()
            
            MotorImpresion.abrir_documento_generado(ruta_generada)
            self.volver_historial.emit()
            
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error al generar", f"Fallo al compilar el reporte digital: {str(e)}", QMessageBox.Ok, self)
            box.setWindowFlags(box.windowFlags() | Qt.Dialog)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
        finally: 
            db.close()