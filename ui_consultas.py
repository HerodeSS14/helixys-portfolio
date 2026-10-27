from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (QApplication, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                               QLabel, QFrame, QScrollArea, QRadioButton, QButtonGroup, 
                               QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QDialog, QListWidget, QInputDialog, QListWidgetItem, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QSizePolicy)
from PySide6.QtGui import QAction, QDesktopServices, QBrush, QColor
from database import SessionLocal
from models import (Paciente, Consulta, GinecoObstetrico, Antecedentes, 
                    PerfilDoctor, RecipeOrden, ArchivoPaciente,
                    CategoriaExamen, ExamenCatalogo, CategoriaMedicamento, MedicamentoCatalogo)
from servicios_impresion import MotorImpresion
from estilos import tema  # Importación del motor de diseño centralizado
import os

# ========================================================
# DIÁLOGO DE GESTIÓN DEL CATÁLOGO DE EXÁMENES
# ========================================================
class DialogoGestionExamenes(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Catálogo de Exámenes")
        self.setMinimumSize(600, 400)
        
        # Sincronización base con el tema modal
        self.setStyleSheet(tema.ESTILO_VENTANA)
        
        layout = QHBoxLayout(self)
        
        # Panel Categorías
        panel_cat = QVBoxLayout()
        self.lbl_cat = QLabel("<b>Categorías de Exámenes</b>")
        panel_cat.addWidget(self.lbl_cat)
        self.list_cat = QListWidget()
        self.list_cat.currentRowChanged.connect(self.cargar_examenes)
        panel_cat.addWidget(self.list_cat)
        
        btn_add_cat = QPushButton("➕ Nueva Categoría")
        btn_add_cat.clicked.connect(self.add_categoria)
        
        btn_del_cat = QPushButton("🗑️ Eliminar Categoría")
        btn_del_cat.clicked.connect(self.del_categoria)
        
        panel_cat.addWidget(btn_add_cat); panel_cat.addWidget(btn_del_cat)
        
        # Panel Exámenes
        panel_ex = QVBoxLayout()
        self.lbl_ex_title = QLabel("<b>Exámenes en la Categoría</b>")
        panel_ex.addWidget(self.lbl_ex_title)
        self.list_ex = QListWidget()
        panel_ex.addWidget(self.list_ex)
        
        btn_add_ex = QPushButton("➕ Nuevo Examen")
        btn_add_ex.clicked.connect(self.add_examen)
        
        btn_del_ex = QPushButton("🗑️ Eliminar Examen")
        btn_del_ex.clicked.connect(self.del_examen)
        
        panel_ex.addWidget(btn_add_ex); panel_ex.addWidget(btn_del_ex)
        
        layout.addLayout(panel_cat); layout.addLayout(panel_ex)
        
        # Aplicación y conexión de estilos
        self.actualizar_diseno_dialogo()
        self.cargar_categorias()

    def actualizar_diseno_dialogo(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        self.lbl_cat.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent;")
        self.lbl_ex_title.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent;")

        style_listas = f"""
            QListWidget {{
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                border: {border_entry}; 
                border-radius: 6px;
                padding: 5px;
            }}
            QListWidget::item {{ padding: 4px; color: {color_txt}; }}
            QListWidget::item:hover {{ background-color: {tema.MENTA_FOCUS}; }}
            QListWidget::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; }}
        """
        self.list_cat.setStyleSheet(style_listas)
        self.list_ex.setStyleSheet(style_listas)

        # Estilizar botones internos del diálogo de forma explícita
        for btn in self.findChildren(QPushButton):
            if "Eliminar" in btn.text() or "🗑️" in btn.text():
                btn.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
            else:
                btn.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)

    # 🚀 BLINDAJE 2: Función auxiliar interna para generar QInputDialogs perfectamente estilizados en modo oscuro
    def obtener_texto_dialogo_oscuro(self, titulo, etiqueta, texto_previo=""):
        app = QApplication.instance()
        manejador = getattr(app, "manejador_voz", None)
        
        # 🔒 1. BLOQUEAR LA TRANSCRIPCIÓN ANTES DE ABRIR EL DIÁLOGO
        if manejador:
            manejador.bloquear_voz()

        self.clearFocus()

        dialogo = QInputDialog(self)
        dialogo.setWindowTitle(titulo)
        dialogo.setLabelText(etiqueta)
        dialogo.setTextValue(texto_previo)
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        dialogo.setStyleSheet(f"""
            QInputDialog {{ background-color: {'#36393e' if tema.modo_actual == 'oscuro' else tema.BG_TARJETA}; color: {color_txt}; }}
            QLabel {{ color: {"#ffffff" if tema.modo_actual == 'oscuro' else "#000000"}; font-size: 14px; background-color: transparent; }}
            QLineEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; font-size: 14px; padding: 6px; border-radius: 5px; }}
            QLineEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; }}
            QPushButton {{ background-color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'}; color: {'#1C1C1C' if tema.modo_actual == 'oscuro' else '#FFFFFF'}; font-weight: bold; padding: 6px 14px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {tema.MENTA_FOCUS if tema.modo_actual == 'oscuro' else '#34495e'}; }}
        """)
        
        ok = dialogo.exec() == QInputDialog.Accepted
        texto = dialogo.textValue()

        # 🔓 2. DESBLOQUEAR LA TRANSCRIPCIÓN TRAS CERRAR EL DIÁLOGO
        if manejador:
            manejador.desbloquear_voz()

        return texto, ok

    def cargar_categorias(self):
        self.list_cat.clear()
        self.list_ex.clear()
        db = SessionLocal()
        cats = db.query(CategoriaExamen).all()
        for c in cats:
            item = QListWidgetItem(c.nombre)
            item.setData(Qt.UserRole, c.id)
            self.list_cat.addItem(item)
        db.close()

    def cargar_examenes(self):
        self.list_ex.clear()
        item = self.list_cat.currentItem()
        if not item: return
        cat_id = item.data(Qt.UserRole)
        db = SessionLocal()
        exams = db.query(ExamenCatalogo).filter_by(categoria_id=cat_id).all()
        for e in exams:
            it = QListWidgetItem(e.nombre)
            it.setData(Qt.UserRole, e.id)
            self.list_ex.addItem(it)
        db.close()

    def add_categoria(self):
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nueva Categoría", "Nombre de la categoría:")
        if ok and nombre.strip():
            db = SessionLocal()
            if not db.query(CategoriaExamen).filter_by(nombre=nombre.strip().upper()).first():
                db.add(CategoriaExamen(nombre=nombre.strip().upper()))
                db.commit()
                self.cargar_categorias()
            db.close()

    def del_categoria(self):
        item = self.list_cat.currentItem()
        if not item: return
        box = QMessageBox(QMessageBox.Question, "Confirmar", "¿Eliminar categoría y TODOS sus exámenes?", QMessageBox.Yes | QMessageBox.No, self)
        box.setStyleSheet(tema.ESTILO_VENTANA)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            cat = db.query(CategoriaExamen).get(item.data(Qt.UserRole))
            if cat: db.delete(cat); db.commit()
            db.close()
            self.cargar_categorias()

    def add_examen(self):
        item_cat = self.list_cat.currentItem()
        if not item_cat: 
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione una categoría primero.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
            return
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nuevo Examen", "Nombre del examen:")
        if ok and nombre.strip():
            db = SessionLocal()
            db.add(ExamenCatalogo(nombre=nombre.strip().title(), categoria_id=item_cat.data(Qt.UserRole)))
            db.commit()
            db.close()
            self.cargar_examenes()

    def del_examen(self):
        item = self.list_ex.currentItem()
        if not item: return
        db = SessionLocal()
        ex = db.query(ExamenCatalogo).get(item.data(Qt.UserRole))
        if ex: db.delete(ex); db.commit()
        db.close()
        self.cargar_examenes()


# ========================================================
# PANTALLA PRINCIPAL DE CONSULTAS
# ========================================================
class PantallaConsulta(QWidget):
    solicitar_informe = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_actual_id = None
        self.edad_calculada = 0
        
        # Inicialización previa absoluta de la lista de tracking de labels fijos
        self.labels_dinamicos = []
        
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        layout_principal.setSpacing(15)

        # --- 1. CABECERA (Ficha Médica Modernizada) ---
        self.frame_header = QFrame()
        self.frame_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout_h = QHBoxLayout(self.frame_header)
        layout_h.setContentsMargins(20, 12, 20, 12)
        
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_id = QLabel("<b>ID:</b> --")
        self.lbl_edad = QLabel("<b>EDAD CLÍNICA:</b> --")
        
        for lbl in [self.lbl_paciente, self.lbl_id, self.lbl_edad]:
            layout_h.addWidget(lbl)
        layout_principal.addWidget(self.frame_header)

        # --- 2. ÁREA SCROLLABLE ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.form_vbox = QVBoxLayout(self.scroll_content)
        self.form_vbox.setContentsMargins(0, 0, 5, 0)
        self.form_vbox.setSpacing(20)

        # ========================================================
        # 1. SECCIÓN: MOTIVO DE CONSULTA Y ENFERMEDAD ACTUAL
        # ========================================================
        self.group_motivo = QGroupBox("📌 Motivo de Consulta y Enfermedad Actual")
        layout_motivo = QFormLayout(self.group_motivo)
        layout_motivo.setLabelAlignment(Qt.AlignLeft)
        layout_motivo.setSpacing(12)
        
        self.in_motivo = QTextEdit(); self.in_motivo.setMinimumHeight(70)
        self.in_enfermedad = QTextEdit(); self.in_enfermedad.setMinimumHeight(90)
        
        lbl_motivo_obj = QLabel("<b>Motivo Consulta:</b>")
        lbl_enfermedad_obj = QLabel("<b>Enfermedad Actual:</b>")
        self.labels_dinamicos.extend([lbl_motivo_obj, lbl_enfermedad_obj])
        
        layout_motivo.addRow(lbl_motivo_obj, self.in_motivo)
        layout_motivo.addRow(lbl_enfermedad_obj, self.in_enfermedad)
        self.form_vbox.addWidget(self.group_motivo)

        # ========================================================
        # 2. SECCIÓN: ANTECEDENTES
        # ========================================================
        # SECCIÓN ANTECEDENTES BASE
        self.group_ant_base = QGroupBox("📋 Antecedentes, Hábitos y Examen Funcional")
        self.group_ant_base.setCheckable(True); self.group_ant_base.setChecked(False)
        lay_ant_base = QFormLayout(self.group_ant_base)
        lay_ant_base.setSpacing(12)
        
        self.in_ant_alergias = QLineEdit()
        self.in_ant_personales = QTextEdit()
        self.in_ant_familiares = QTextEdit()
        self.in_ant_operaciones = QTextEdit()
        
        self.in_ant_alergias.setMinimumHeight(38)
        self.in_ant_personales.setMinimumHeight(80)
        self.in_ant_familiares.setMinimumHeight(80)
        self.in_ant_operaciones.setMinimumHeight(80)
        
        self.w_fuma, self.in_fuma, self.bg_fuma = self.crear_campo_dinamico("🚬 Fuma", "Cantidad...")
        self.w_bebe, self.in_bebe, self.bg_bebe = self.crear_campo_dinamico("🍺 Bebe", "Frecuencia...")
        self.w_otros_h, self.in_otros_h, self.bg_otros_h = self.crear_campo_dinamico("🧩 Otros Hábitos", "Especifique...")
        self.in_examen_funcional = QTextEdit(); self.in_examen_funcional.setMinimumHeight(80)

        lbl_al = QLabel("⚠️ Alergias:"); lbl_pe = QLabel("📋 Personales:"); lbl_fa = QLabel("👥 Familiares:"); lbl_op = QLabel("✂️ Operaciones:"); lbl_ef = QLabel("🩺 Examen Funcional:")
        self.labels_dinamicos.extend([lbl_al, lbl_pe, lbl_fa, lbl_op, lbl_ef])

        lay_ant_base.addRow(lbl_al, self.in_ant_alergias)
        lay_ant_base.addRow(lbl_pe, self.in_ant_personales)
        lay_ant_base.addRow(lbl_fa, self.in_ant_familiares)
        lay_ant_base.addRow(lbl_op, self.in_ant_operaciones)
        lay_ant_base.addRow(self.w_fuma)
        lay_ant_base.addRow(self.w_bebe)
        lay_ant_base.addRow(self.w_otros_h)
        lay_ant_base.addRow(lbl_ef, self.in_examen_funcional)
        self.form_vbox.addWidget(self.group_ant_base)

        # SECCIÓN GINECO-OBSTÉTRICO (SI APLICA)
        self.group_gineco = QGroupBox("🤰 Gineco-Obstétrico")
        self.group_gineco.setCheckable(True)
        self.group_gineco.setChecked(False)  
        layout_gineco = QVBoxLayout(self.group_gineco)
        layout_gineco.setSpacing(10)
        self.referencias_gin = {}
        
        layout_formulario_gin = QFormLayout()
        layout_formulario_gin.setSpacing(12)
        layout_formulario_gin.setLabelAlignment(Qt.AlignLeft)
        
        campos_gin = [
            ("Menarquia:", "menarquia"), ("Gestas:", "gestas"), ("Abortos:", "abortos"), 
            ("Emb. Ectópico:", "embarazo_ectopico"), ("Partos:", "partos"), ("Cesárea:", "cesarea"), 
            ("Menopausia:", "menopausia"), ("Sangramiento:", "sangramiento"), ("Flujo:", "flujo"), 
            ("DIU:", "diu"), ("ACO:", "aco")
        ]
        
        for label_text, db_name in campos_gin:
            lbl_obj = QLabel(f"<b>{label_text}</b>")
            self.labels_dinamicos.append(lbl_obj)
            
            entrada = QLineEdit()
            entrada.setPlaceholderText("Detalle...")
            entrada.setMinimumHeight(38)
            
            entrada.toPlainText = entrada.text
            
            layout_formulario_gin.addRow(lbl_obj, entrada)
            self.referencias_gin[db_name] = entrada
            
        layout_gineco.addLayout(layout_formulario_gin)
        
        self.w_incont, self.bg_incont = self.crear_campo_booleano("Incontinencia")
        layout_gineco.addWidget(self.w_incont)
        
        self.form_vbox.addWidget(self.group_gineco)

        # ========================================================
        # 3. SECCIÓN: EXAMEN FÍSICO
        # ========================================================
        # SIGNOS VITALES Y BIOMETRÍA
        self.group_vitals = QGroupBox("🩺 Signos Vitales y Biometría")
        layout_vitals = QFormLayout(self.group_vitals)
        layout_vitals.setSpacing(12)
        
        self.in_peso = QLineEdit(); self.in_altura = QLineEdit()
        self.in_peso.setPlaceholderText("kg"); self.in_altura.setPlaceholderText("Ej: 170 o 1.70")
        self.in_peso.setMinimumHeight(38); self.in_altura.setMinimumHeight(38)
        
        self.lbl_imc = QLabel("<b>IMC: --</b>")
        self.in_peso.textChanged.connect(self.calcular_imc); self.in_altura.textChanged.connect(self.calcular_imc)
        self.w_ta, self.in_ta, self.bg_ta = self.crear_campo_dinamico("Tensión Art.", "120/80")
        self.w_pulso, self.in_pulso, self.bg_pulso = self.crear_campo_dinamico("Pulso", "PPM")
        
        lbl_p = QLabel("Peso:"); lbl_p.setStyleSheet(tema.ESTILO_LABEL_DATO)
        lbl_a = QLabel("Altura:"); lbl_a.setStyleSheet(tema.ESTILO_LABEL_DATO)
        lbl_r = QLabel("Resultado:"); lbl_r.setStyleSheet(tema.ESTILO_LABEL_DATO)
        self.labels_dinamicos.extend([lbl_p, lbl_a, lbl_r])
        
        layout_vitals.addRow(lbl_p, self.in_peso)
        layout_vitals.addRow(lbl_a, self.in_altura)
        layout_vitals.addRow(lbl_r, self.lbl_imc)
        layout_vitals.addRow(self.w_ta)
        layout_vitals.addRow(self.w_pulso)
        self.form_vbox.addWidget(self.group_vitals)

        # EXAMEN FÍSICO GENERAL
        self.group_ef_gen = QGroupBox("🔍 Examen Físico General")
        layout_ef_gen = QVBoxLayout(self.group_ef_gen)
        layout_ef_gen.setSpacing(10)
        self.referencias_ef = {}
        campos_gen = [("Piel", "piel"), ("Ojos", "ojos"), ("Oídos", "oidos"), ("Orofaringe", "orofaringe"), 
                      ("Tiroides", "tiroides"), ("Axilas", "axilas"), ("Supraclaviculares", "supraclaviculares"), 
                      ("Abdomen", "abdomen"), ("Lumbar", "lumbar"), ("Neurológico", "neurologico"), 
                      ("Otros", "otros_examen_fisico")]
        for label, db_name in campos_gen:
            widget, entrada, bg = self.crear_campo_dinamico(label, "Hallazgos...")
            layout_ef_gen.addWidget(widget); self.referencias_ef[db_name] = (entrada, bg)
        self.form_vbox.addWidget(self.group_ef_gen)

        # EXAMEN FÍSICO FEMENINO
        self.group_ef_femenino = QGroupBox("♀️ Examen Físico Femenino")
        lay_fem = QVBoxLayout(self.group_ef_femenino)
        lay_fem.setSpacing(10)
        campos_fem = [("Mamas", "mamas"), ("Vulva", "vulva"), ("Vagina", "vagina"), ("Cervix", "cervix"), ("Colposcopia", "colposcopia"), ("Tacto Recto Vaginal", "tacto_recto_vaginal")]
        for label, db_name in campos_fem:
            widget, entrada, bg = self.crear_campo_dinamico(label, "Hallazgos...")
            lay_fem.addWidget(widget); self.referencias_ef[db_name] = (entrada, bg)
        self.form_vbox.addWidget(self.group_ef_femenino)

        # EXAMEN FÍSICO MASCULINO
        self.group_ef_masculino = QGroupBox("♂️ Examen Físico Masculino")
        lay_mas = QVBoxLayout(self.group_ef_masculino)
        lay_mas.setSpacing(10)
        campos_mas = [("Pene/Testículos", "pene_testiculos"), ("Próstata", "prostata")]
        for label, db_name in campos_mas:
            widget, entrada, bg = self.crear_campo_dinamico(label, "Hallazgos...")
            lay_mas.addWidget(widget); self.referencias_ef[db_name] = (entrada, bg)
        self.form_vbox.addWidget(self.group_ef_masculino)

        # ========================================================
        # 4. SECCIÓN: CONCLUSIÓN DIAGNÓSTICA Y EVOLUCIÓN
        # ========================================================
        self.group_conclusion = QGroupBox("📝 Conclusión Diagnóstica y Evolución")
        layout_conclusion = QFormLayout(self.group_conclusion)
        layout_conclusion.setLabelAlignment(Qt.AlignLeft)
        layout_conclusion.setSpacing(12)

        self.in_impresion_diag = QTextEdit(); self.in_impresion_diag.setMinimumHeight(70)
        self.in_estudios_ind = QTextEdit(); self.in_estudios_ind.setMinimumHeight(70)
        
        # Ocultable (Diagnóstico)
        self.w_diagnostico = QWidget(); lay_diag = QVBoxLayout(self.w_diagnostico); lay_diag.setContentsMargins(0,0,0,0)
        self.in_diagnostico = QTextEdit(); self.in_diagnostico.setMinimumHeight(70)
        lay_diag.addWidget(self.in_diagnostico)
        self.lbl_diagnostico = QLabel("<b>Diagnóstico:</b>")
        self.labels_dinamicos.append(self.lbl_diagnostico)
        
        self.w_nota, self.in_nota, self.bg_nota = self.crear_campo_dinamico("Nota Evolutiva", "Evolución...")

        lbl_imp_obj = QLabel("<b>Impresión Diagnóstica:</b>")
        lbl_est_obj = QLabel("<b>Estudios Indicados:</b>")
        self.labels_dinamicos.extend([lbl_imp_obj, lbl_est_obj])

        layout_conclusion.addRow(lbl_imp_obj, self.in_impresion_diag)
        layout_conclusion.addRow(lbl_est_obj, self.in_estudios_ind)
        layout_conclusion.addRow(self.lbl_diagnostico, self.w_diagnostico)
        layout_conclusion.addRow(self.w_nota)
        self.form_vbox.addWidget(self.group_conclusion)

        # --- SECCIONES FINALES (RÉCIPES Y EXÁMENES) ---
        self.crear_seccion_prescripcion()
        self.crear_seccion_examenes() 

        self.scroll.setWidget(self.scroll_content)
        layout_principal.addWidget(self.scroll)

        # --- BOTONERA FINAL INTERACTIVA ---
        self.frame_botones_final = QFrame()
        lay_botones = QHBoxLayout(self.frame_botones_final)
        lay_botones.setContentsMargins(0, 10, 0, 0)
        lay_botones.setSpacing(15)

        self.btn_ir_a_informe = QPushButton("📝 REDACTAR INFORME")
        self.btn_ir_a_informe.setMinimumHeight(45)
        self.btn_ir_a_informe.clicked.connect(lambda: self.solicitar_informe.emit(self.paciente_actual_id) if self.paciente_actual_id else None)
        
        self.btn_guardar = QPushButton("💾 GUARDAR CONSULTA COMPLETA")
        self.btn_guardar.setMinimumHeight(45)
        self.btn_guardar.clicked.connect(lambda: self.guardar_consulta())
        
        lay_botones.addWidget(self.btn_ir_a_informe, stretch=1)
        lay_botones.addWidget(self.btn_guardar, stretch=1)
        layout_principal.addWidget(self.frame_botones_final)

        # Vincular al motor central de temas
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        # 1. Cabecera superior unificada
        border_head = "#4f545c" if tema.modo_actual == "oscuro" else "#feb2b2"
        bg_head = tema.BG_TARJETA if tema.modo_actual == "oscuro" else "#fff5f5"
        self.frame_header.setStyleSheet(f"background-color: {bg_head}; border-radius: 10px; border: 1px solid {border_head};")
        
        for lbl in [self.lbl_paciente, self.lbl_id, self.lbl_edad]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 15px; font-weight: bold; background: transparent; border: none;")

        # 2. Control de Viewport y Scroll sin destellos
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {color_fondo_paginas}; }}")
        self.scroll_content.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")

        # 🚀 SOLUCIÓN 1: Obligamos al Frame inferior a acoplarse transparentemente al fondo y eliminar bordes fantasmas
        self.frame_botones_final.setStyleSheet("background-color: transparent; border: none; background: transparent;")

        # Títulos de Labels fijos
        for lbl in self.labels_dinamicos + [self.lbl_imc]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent; border: none;")

        # 3. Hojas de Estilos para GroupBoxes Corporativos Expandibles
        style_groups = f"""
            QGroupBox {{
                font-size: 15px; font-weight: bold;
                color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'};
                background-color: {'#2f3136' if tema.modo_actual == 'oscuro' else '#f9f9f9'};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 8px; padding-top: 22px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
        """
        for group in [self.group_motivo, self.group_conclusion, self.group_vitals, self.group_ef_gen, self.group_ef_femenino, self.group_ef_masculino, self.group_recipe, self.group_examenes]:
            group.setStyleSheet(style_groups)

        # Sombreado condicional estricto para Checkable GroupBoxes
        bg_disabled_g = "#242528" if tema.modo_actual == "oscuro" else "#eaeaea"
        bg_enabled_g = "#2f3136" if tema.modo_actual == "oscuro" else "#f9f9f9"
        style_checkable = f"""
            QGroupBox {{ font-size: 15px; font-weight: bold; color: {color_txt}; background-color: {bg_disabled_g}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 8px; padding-top: 22px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }}
            QGroupBox:checked {{ background-color: {bg_enabled_g}; color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'}; }}
        """
        self.group_gineco.setStyleSheet(style_checkable)
        self.group_ant_base.setStyleSheet(style_checkable)

        # 4. BLINDAJE FOCUS MASIVO: Re-mapeo dinámico de cajas de entrada
        style_campos_texto = f"""
            QLineEdit, QTextEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; padding: 6px; border-radius: 5px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
            }}
        """
        for qle in self.findChildren(QLineEdit):
            qle.setStyleSheet(style_campos_texto)
            
        for qte in self.findChildren(QTextEdit):
            if qte.parent() and "Table" in qte.parent().metaObject().className():
                continue
            qte.setStyleSheet(style_campos_texto)

        # Adaptar botones de radio y selectores del entorno
        for rb in self.findChildren(QRadioButton):
            rb.setStyleSheet(f"QRadioButton {{ color: {color_txt}; font-size: 13px; background: transparent; }} QRadioButton::handle {{ border: 1px solid {tema.BORDE_SUAVE}; }}")

        # 5. Estilización de Listados y Árboles de Catálogo
        style_listas_arboles = f"""
            QTreeWidget, QListWidget {{
                background-color: {color_fondo_entry}; color: {color_txt};
                border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 4px;
            }}
            QTreeWidget::item, QListWidget::item {{ padding: 4px; color: {color_txt}; }}
            QTreeView::item:hover, QListWidget::item:hover {{ background-color: {tema.MENTA_FOCUS}; }}
            QTreeView::item:selected, QListWidget::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; }}
        """
        for component in [self.arbol_busqueda_med, self.arbol_busqueda_ex, self.lista_cat_med, self.lista_meds_cat, self.lista_cat_ex, self.lista_examenes_cat_ex]:
            component.setStyleSheet(style_listas_arboles)

        # Tablas de Récipe y Órdenes
        style_tablas = f"""
            QTableWidget {{ background-color: {color_fondo_entry}; color: {color_txt}; gridline-color: {tema.BORDE_SUAVE}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; }}
            QHeaderView::section {{ background-color: #93F6E3; color: #1C1C1C; font-weight: bold; padding: 5px; border: 1px solid {tema.BORDE_SUAVE}; }}
            QTableWidget::item {{ color: {color_txt}; }}
        """
        self.tabla_recipe.setStyleSheet(style_tablas)
        self.tabla_examenes.setStyleSheet(style_tablas)

        # 6. Sincronizar Celdas Internas y Botoneras de Tablas Activas
        self.actualizar_estilo_celdas_internas_tabla(self.tabla_recipe)
        self.actualizar_estilo_celdas_internas_tabla(self.tabla_examenes)

        # Estilo de las Pestañas QTabWidget
        style_tabs = f"""
            QTabWidget::panel {{ border: 1px solid {tema.BORDE_SUAVE}; background-color: {tema.BG_TARJETA}; border-radius: 6px; }} 
            QTabBar::tab {{ color: {color_txt}; background-color: {color_fondo_entry}; border: 1px solid {tema.BORDE_SUAVE}; padding: 6px 14px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
            QTabBar::tab:selected {{ background-color: {tema.BG_TARJETA}; border-bottom-color: {tema.BG_TARJETA}; font-weight: bold; color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'}; }}
        """
        self.tabs_recipe.setStyleSheet(style_tabs)
        self.tabs_examenes.setStyleSheet(style_tabs)

        # 7. Botoneras del sistema
        self.btn_ir_a_informe.setStyleSheet(tema.ESTILO_BTN_INFORME)
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_imprimir.setStyleSheet(tema.ESTILO_BTN_RECIPE)
        self.btn_imprimir_ex.setStyleSheet(tema.ESTILO_BTN_ORDEN)
        
        # Botones pequeños de edición de los catálogos
        for btn_s in self.findChildren(QPushButton):
            if btn_s in [self.btn_ir_a_informe, self.btn_guardar, self.btn_imprimir, self.btn_imprimir_ex]:
                continue
            if btn_s.text() == "❌" or btn_s.text() == "🗑️":
                btn_s.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
            else:
                btn_s.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)

    def actualizar_estilo_celdas_internas_tabla(self, tabla_obj):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        for row in range(tabla_obj.rowCount()):
            item_celda = tabla_obj.item(row, 0)
            if item_celda:
                item_celda.setForeground(QBrush(QColor(color_txt)))
            
            in_widget = tabla_obj.cellWidget(row, 1)
            if in_widget and isinstance(in_widget, QTextEdit):
                in_widget.setStyleSheet(f"""
                    QTextEdit {{
                        border: {border_entry}; 
                        background-color: {color_fondo_entry}; 
                        color: {color_txt}; 
                        font-size: 14px; padding: 4px; border-radius: 4px;
                    }}
                    QTextEdit:focus {{
                        border: 1px solid {tema.MENTA_MEDICA};
                        background-color: {color_fondo_entry}; 
                        color: {color_txt}; 
                    }}
                """)

    # 🚀 BLINDAJE 2: Función interna mapeada en PantallaConsulta para dar soporte a las ventanas emergentes del catálogo de Medicamentos
    def obtener_texto_dialogo_oscuro(self, titulo, etiqueta, texto_previo=""):
        app = QApplication.instance()
        manejador = getattr(app, "manejador_voz", None)
        
        # 🔒 1. BLOQUEAR LA TRANSCRIPCIÓN ANTES DE ABRIR EL DIÁLOGO
        if manejador:
            manejador.bloquear_voz()

        self.clearFocus()

        dialogo = QInputDialog(self)
        dialogo.setWindowTitle(titulo)
        dialogo.setLabelText(etiqueta)
        dialogo.setTextValue(texto_previo)
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        dialogo.setStyleSheet(f"""
            QInputDialog {{ background-color: {'#36393e' if tema.modo_actual == 'oscuro' else tema.BG_TARJETA}; color: {color_txt}; }}
            QLabel {{ color: {"#ffffff" if tema.modo_actual == 'oscuro' else "#000000"}; font-size: 14px; background-color: transparent; }}
            QLineEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; font-size: 14px; padding: 6px; border-radius: 5px; }}
            QLineEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; }}
            QPushButton {{ background-color: {tema.MENTA_MEDICA if tema.modo_actual == 'oscuro' else '#2c3e50'}; color: {'#1C1C1C' if tema.modo_actual == 'oscuro' else '#FFFFFF'}; font-weight: bold; padding: 6px 14px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {tema.MENTA_FOCUS if tema.modo_actual == 'oscuro' else '#34495e'}; }}
        """)
        
        ok = dialogo.exec() == QInputDialog.Accepted
        texto = dialogo.textValue()

        # 🔓 2. DESBLOQUEAR LA TRANSCRIPCIÓN TRAS CERRAR EL DIÁLOGO
        if manejador:
            manejador.desbloquear_voz()

        return texto, ok

    def crear_seccion_prescripcion(self):
        self.group_recipe = QGroupBox("💊 Prescripción Médica (Rp)")
        layout = QVBoxLayout(self.group_recipe)
        self.tabs_recipe = QTabWidget()
        
        # --- PESTAÑA A: GENERAR RÉCIPE ---
        tab_generar = QWidget()
        lay_gen = QHBoxLayout(tab_generar)
        
        panel_izq = QVBoxLayout()
        lbl_bmed = QLabel("<b>🔍 Buscar Medicamento:</b>")
        self.labels_dinamicos.append(lbl_bmed)
        panel_izq.addWidget(lbl_bmed)
        
        self.in_buscador_med = QLineEdit()
        self.in_buscador_med.setPlaceholderText("Escriba para filtrar...")
        self.in_buscador_med.setMinimumHeight(38)
        self.in_buscador_med.textChanged.connect(self.filtrar_catalogo_med)
        panel_izq.addWidget(self.in_buscador_med)
        
        self.arbol_busqueda_med = QTreeWidget()
        self.arbol_busqueda_med.setHeaderHidden(True)
        self.arbol_busqueda_med.itemDoubleClicked.connect(self.agregar_al_recipe)
        panel_izq.addWidget(self.arbol_busqueda_med)
        lay_gen.addLayout(panel_izq, 35) 

        # Panel Derecho: Tabla y Botón Desplegable
        panel_der = QVBoxLayout()
        lbl_mrec = QLabel("<b>📋 Medicamentos en este Récipe:</b>")
        self.labels_dinamicos.append(lbl_mrec)
        panel_der.addWidget(lbl_mrec)

        self.tabla_recipe = QTableWidget(0, 3)
        self.tabla_recipe.setHorizontalHeaderLabels(["Medicamento", "Indicaciones", "Acción"])
        self.tabla_recipe.setColumnWidth(0, 200) 
        self.tabla_recipe.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_recipe.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_recipe.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla_recipe.setMinimumHeight(250) 
        panel_der.addWidget(self.tabla_recipe)
        
        # Botón Desplegable (PDF / Word)
        self.btn_imprimir = QPushButton("🖨️ GENERAR RÉCIPE ▾")
        self.btn_imprimir.setMinimumHeight(42)

        menu_recipe = QMenu(self)
        menu_recipe.setStyleSheet(tema.ESTILO_VENTANA)

        action_pdf = QAction("📄 Generar Récipe en PDF (.pdf)", self)
        action_pdf.triggered.connect(lambda: self.imprimir_recipe_actual(formato="pdf"))

        action_docx = QAction("📝 Generar Récipe en Word (.docx)", self)
        action_docx.triggered.connect(lambda: self.imprimir_recipe_actual(formato="docx"))

        menu_recipe.addAction(action_pdf)
        menu_recipe.addAction(action_docx)
        self.btn_imprimir.setMenu(menu_recipe)

        panel_der.addWidget(self.btn_imprimir) 
        lay_gen.addLayout(panel_der, 65) 
        self.tabs_recipe.addTab(tab_generar, "📝 Redactar Récipe")

        # --- PESTAÑA B: ADMINISTRAR CATÁLOGO ---
        tab_admin = QWidget()
        lay_admin = QHBoxLayout(tab_admin)
        
        col_cat = QVBoxLayout()
        lbl_cat_list = QLabel("<b>📁 Categorías:</b>")
        self.labels_dinamicos.append(lbl_cat_list)
        col_cat.addWidget(lbl_cat_list)
        
        self.lista_cat_med = QListWidget()
        self.lista_cat_med.currentRowChanged.connect(self.cargar_meds_categoria)
        col_cat.addWidget(self.lista_cat_med)
        
        lay_btn_cat = QHBoxLayout()
        btn_add_cat = QPushButton("➕"); btn_add_cat.clicked.connect(self.admin_add_cat_med)
        btn_edit_cat = QPushButton("✏️"); btn_edit_cat.clicked.connect(self.admin_edit_cat_med)
        btn_del_cat = QPushButton("🗑️"); btn_del_cat.clicked.connect(self.admin_del_cat_med)
        lay_btn_cat.addWidget(btn_add_cat); lay_btn_cat.addWidget(btn_edit_cat); lay_btn_cat.addWidget(btn_del_cat)
        col_cat.addLayout(lay_btn_cat)
        lay_admin.addLayout(col_cat)

        col_med = QVBoxLayout()
        lbl_med_list = QLabel("<b>💊 Medicamentos:</b>")
        self.labels_dinamicos.append(lbl_med_list)
        col_med.addWidget(lbl_med_list)
        
        self.lista_meds_cat = QListWidget()
        col_med.addWidget(self.lista_meds_cat)
        
        lay_btn_med = QHBoxLayout()
        btn_add_med = QPushButton("➕"); btn_add_med.clicked.connect(self.admin_add_med)
        btn_edit_med = QPushButton("✏️"); btn_edit_med.clicked.connect(self.admin_edit_med)
        btn_del_med = QPushButton("🗑️"); btn_del_med.clicked.connect(self.admin_del_med)
        lay_btn_med.addWidget(btn_add_med); lay_btn_med.addWidget(btn_edit_med); lay_btn_med.addWidget(btn_del_med)
        col_med.addLayout(lay_btn_med)
        lay_admin.addLayout(col_med)

        self.tabs_recipe.addTab(tab_admin, "⚙️ Catálogo")
        layout.addWidget(self.tabs_recipe)
        self.form_vbox.addWidget(self.group_recipe)
        self.actualizar_catalogo_meds()

    def crear_seccion_examenes(self):
        self.group_examenes = QGroupBox("🧪 Órdenes de Exámenes (Laboratorio/Imágenes)")
        layout = QVBoxLayout(self.group_examenes)
        self.tabs_examenes = QTabWidget()
        
        # --- PESTAÑA A: GENERAR ORDEN ---
        tab_generar = QWidget()
        lay_gen = QHBoxLayout(tab_generar)
        
        panel_izq = QVBoxLayout()
        lbl_bex = QLabel("<b>🔍 Buscar Examen:</b>")
        self.labels_dinamicos.append(lbl_bex)
        panel_izq.addWidget(lbl_bex)
        
        self.in_buscador_ex = QLineEdit()
        self.in_buscador_ex.setPlaceholderText("Escriba para filtrar...")
        self.in_buscador_ex.setMinimumHeight(38)
        self.in_buscador_ex.textChanged.connect(self.filtrar_catalogo_ex)
        panel_izq.addWidget(self.in_buscador_ex)
        
        self.arbol_busqueda_ex = QTreeWidget()
        self.arbol_busqueda_ex.setHeaderHidden(True)
        self.arbol_busqueda_ex.itemDoubleClicked.connect(self.agregar_a_orden_ex)
        panel_izq.addWidget(self.arbol_busqueda_ex)
        lay_gen.addLayout(panel_izq, 35)

        # Panel Derecho: Tabla y Botón Desplegable
        panel_der = QVBoxLayout()
        lbl_eord = QLabel("<b>📋 Exámenes en esta Orden:</b>")
        self.labels_dinamicos.append(lbl_eord)
        panel_der.addWidget(lbl_eord)

        self.tabla_examenes = QTableWidget(0, 3)
        self.tabla_examenes.setHorizontalHeaderLabels(["Examen Solicitado", "Observación", "Acción"])
        self.tabla_examenes.setColumnWidth(0, 200) 
        self.tabla_examenes.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_examenes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_examenes.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla_examenes.setMinimumHeight(250) 
        panel_der.addWidget(self.tabla_examenes)
        
        # Botón Desplegable (PDF / Word)
        self.btn_imprimir_ex = QPushButton("🖨️ GENERAR ORDEN ▾")
        self.btn_imprimir_ex.setMinimumHeight(42)

        menu_orden = QMenu(self)
        menu_orden.setStyleSheet(tema.ESTILO_VENTANA)

        action_pdf = QAction("📄 Generar Orden en PDF (.pdf)", self)
        action_pdf.triggered.connect(lambda: self.imprimir_orden_actual(formato="pdf"))

        action_docx = QAction("📝 Generar Orden en Word (.docx)", self)
        action_docx.triggered.connect(lambda: self.imprimir_orden_actual(formato="docx"))

        menu_orden.addAction(action_pdf)
        menu_orden.addAction(action_docx)
        self.btn_imprimir_ex.setMenu(menu_orden)

        panel_der.addWidget(self.btn_imprimir_ex)
        lay_gen.addLayout(panel_der, 65)
        self.tabs_examenes.addTab(tab_generar, "📝 Redactar Orden")

        # --- PESTAÑA B: ADMINISTRAR CATÁLOGO ---
        tab_admin = QWidget()
        lay_admin = QHBoxLayout(tab_admin)
        
        col_cat = QVBoxLayout()
        lbl_cat_ex_list = QLabel("<b>📁 Categorías:</b>")
        self.labels_dinamicos.append(lbl_cat_ex_list)
        col_cat.addWidget(lbl_cat_ex_list)
        
        self.lista_cat_ex = QListWidget()
        self.lista_cat_ex.currentRowChanged.connect(self.cargar_examenes_categoria)
        col_cat.addWidget(self.lista_cat_ex)
        
        lay_btn_cat = QHBoxLayout()
        btn_add_cat = QPushButton("➕"); btn_add_cat.clicked.connect(self.admin_add_cat_ex)
        btn_edit_cat = QPushButton("✏️"); btn_edit_cat.clicked.connect(self.admin_edit_cat_ex)
        btn_del_cat = QPushButton("🗑️"); btn_del_cat.clicked.connect(self.admin_del_cat_ex)
        lay_btn_cat.addWidget(btn_add_cat); lay_btn_cat.addWidget(btn_edit_cat); lay_btn_cat.addWidget(btn_del_cat)
        col_cat.addLayout(lay_btn_cat)
        lay_admin.addLayout(col_cat)

        col_ex = QVBoxLayout()
        lbl_ex_list_title = QLabel("<b>🔬 Exámenes:</b>")
        self.labels_dinamicos.append(lbl_ex_list_title)
        col_ex.addWidget(lbl_ex_list_title)
        
        self.lista_examenes_cat_ex = QListWidget()
        col_ex.addWidget(self.lista_examenes_cat_ex)
        
        lay_btn_ex = QHBoxLayout()
        btn_add_ex = QPushButton("➕"); btn_add_ex.clicked.connect(self.admin_add_ex)
        btn_edit_ex = QPushButton("✏️"); btn_edit_ex.clicked.connect(self.admin_edit_ex)
        btn_del_ex = QPushButton("🗑️"); btn_del_ex.clicked.connect(self.admin_del_ex)
        lay_btn_ex.addWidget(btn_add_ex); lay_btn_ex.addWidget(btn_edit_ex); lay_btn_ex.addWidget(btn_del_ex)
        col_ex.addLayout(lay_btn_ex)
        lay_admin.addLayout(col_ex)

        self.tabs_examenes.addTab(tab_admin, "⚙️ Catálogo")
        layout.addWidget(self.tabs_examenes)
        self.form_vbox.addWidget(self.group_examenes)
        self.actualizar_catalogo_examenes()

    def crear_campo_dinamico(self, etiqueta, placeholder):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        lbl = QLabel(f"<b>{etiqueta}:</b>")
        lbl.setFixedWidth(160)
        self.labels_dinamicos.append(lbl)
        
        btn_group = QButtonGroup(contenedor)
        rb_no = QRadioButton("No aplica")
        rb_si = QRadioButton("Aplica")
        
        rb_no.setChecked(True)
        btn_group.addButton(rb_no)
        btn_group.addButton(rb_si)
        
        entrada = QTextEdit()
        entrada.setPlaceholderText(placeholder)
        entrada.setVisible(False)
        entrada.setFixedHeight(40)
        
        def ajustar_altura():
            doc_height = entrada.document().size().height()
            nueva_altura = max(40, min(120, doc_height + 15)) 
            entrada.setFixedHeight(nueva_altura)
        entrada.textChanged.connect(ajustar_altura)
        
        def al_alternar(checked):
            entrada.setVisible(checked)
            if checked: 
                # Forzar refresco visual dinámico de estilos al aparecer
                color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
                color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
                border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
                entrada.setStyleSheet(f"QTextEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; padding: 6px; border-radius: 5px; }} QTextEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; background-color: {color_fondo_entry}; color: {color_txt}; }}")
                entrada.setFocus() 
                
        rb_si.toggled.connect(al_alternar)
        
        layout.addWidget(lbl)
        layout.addWidget(rb_no)
        layout.addWidget(rb_si)
        layout.addWidget(entrada, stretch=1)
        return contenedor, entrada, btn_group

    def crear_campo_simple(self, etiqueta, placeholder):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        lbl = QLabel(f"<b>{etiqueta}:</b>")
        lbl.setFixedWidth(160)
        self.labels_dinamicos.append(lbl)
        
        entrada = QTextEdit()
        entrada.setPlaceholderText(placeholder)
        entrada.setFixedHeight(40)
        
        def ajustar_altura():
            doc_height = entrada.document().size().height()
            nueva_altura = max(40, min(120, doc_height + 15))
            entrada.setFixedHeight(nueva_altura)
        entrada.textChanged.connect(ajustar_altura)
        
        layout.addWidget(lbl)
        layout.addWidget(entrada, stretch=1)
        return contenedor, entrada
    
    def crear_campo_booleano(self, etiqueta):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        lbl = QLabel(f"<b>{etiqueta}:</b>")
        lbl.setFixedWidth(160)
        self.labels_dinamicos.append(lbl)
        
        btn_group = QButtonGroup(contenedor)
        rb_no = QRadioButton("No")
        rb_si = QRadioButton("Sí")
        
        rb_no.setChecked(True) 
        btn_group.addButton(rb_no)
        btn_group.addButton(rb_si)
        
        layout.addWidget(lbl)
        layout.addWidget(rb_no)
        layout.addWidget(rb_si)
        layout.addStretch()
        return contenedor, btn_group

    # ==========================================================
    # LOS MÉTODOS DE LÓGICA Y DATOS PERMANECEN INTACTOS
    # ==========================================================
    def actualizar_catalogo_meds(self):
        db = SessionLocal()
        self.lista_cat_med.clear()
        self.arbol_busqueda_med.clear()
        
        categorias = db.query(CategoriaMedicamento).order_by(CategoriaMedicamento.nombre).all()
        for c in categorias: 
            self.lista_cat_med.addItem(c.nombre)
            
            cat_item = QTreeWidgetItem(self.arbol_busqueda_med, [f"📁 {c.nombre}"])
            cat_item.setData(0, Qt.UserRole, "CATEGORIA")
            cat_item.setForeground(0, QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
            font = cat_item.font(0); font.setBold(True); cat_item.setFont(0, font)
            
            for med in sorted(c.medicamentos, key=lambda x: x.nombre):
                med_item = QTreeWidgetItem(cat_item, [f"💊 {med.nombre}"])
                med_item.setData(0, Qt.UserRole, "MEDICAMENTO")
                med_item.setData(0, Qt.UserRole + 1, med.nombre)
                
        db.close()

    def filtrar_catalogo_med(self, texto):
        texto = texto.lower()
        for i in range(self.arbol_busqueda_med.topLevelItemCount()):
            cat_item = self.arbol_busqueda_med.topLevelItem(i)
            cat_match = texto in cat_item.text(0).lower()
            
            tiene_hijo_visible = False
            for j in range(cat_item.childCount()):
                med_item = cat_item.child(j)
                med_match = texto in med_item.text(0).lower()
                
                if cat_match or med_match:
                    med_item.setHidden(False)
                    tiene_hijo_visible = True
                else:
                    med_item.setHidden(True)
            
            if tiene_hijo_visible or cat_match:
                cat_item.setHidden(False)
                if texto: cat_item.setExpanded(True)
            else:
                cat_item.setHidden(True)

    def agregar_al_recipe(self, item, column):
        if item.data(0, Qt.UserRole) != "MEDICAMENTO":
            item.setExpanded(not item.isExpanded())
            return
            
        nombre_med = item.data(0, Qt.UserRole + 1)
        row = self.tabla_recipe.rowCount()
        self.tabla_recipe.insertRow(row)
        
        item_table = QTableWidgetItem(nombre_med)
        item_table.setForeground(QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
        self.tabla_recipe.setItem(row, 0, item_table)
        
        in_ind = QTextEdit()
        in_ind.setPlaceholderText("Indicaciones (Dosis, frecuencia...)")
        in_ind.setFixedHeight(40)
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        in_ind.setStyleSheet(f"""
            QTextEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; font-size: 14px; padding: 4px; border-radius: 4px; }}
            QTextEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; background-color: {color_fondo_entry}; color: {color_txt}; }}
        """)
        
        def adaptar_altura():
            doc_height = int(in_ind.document().size().height())
            in_ind.setFixedHeight(max(40, doc_height + 10))
            self.tabla_recipe.resizeRowsToContents()
            
        in_ind.textChanged.connect(adaptar_altura)
        self.tabla_recipe.setCellWidget(row, 1, in_ind)
        
        btn_del = QPushButton("❌")
        btn_del.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        btn_del.clicked.connect(lambda: self.tabla_recipe.removeRow(self.tabla_recipe.indexAt(btn_del.pos()).row()))
        self.tabla_recipe.setCellWidget(row, 2, btn_del)

    def cargar_meds_categoria(self):
        item = self.lista_cat_med.currentItem()
        if not item: return
        db = SessionLocal()
        cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
        self.lista_meds_cat.clear()
        if cat:
            for med in cat.medicamentos: self.lista_meds_cat.addItem(med.nombre)
        db.close()

    def restaurar_categoria_med(self, nombre_cat):
        items = self.lista_cat_med.findItems(nombre_cat, Qt.MatchExactly)
        if items: self.lista_cat_med.setCurrentItem(items[0])

    def admin_add_cat_med(self):
        self.clearFocus()
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nueva Categoría", "Nombre de la categoría:")
        if ok and nombre.strip():
            db = SessionLocal()
            db.add(CategoriaMedicamento(nombre=nombre.strip()))
            db.commit()
            db.close()
            self.actualizar_catalogo_meds()
        self.lista_cat_med.setFocus()

    def admin_edit_cat_med(self):
        item = self.lista_cat_med.currentItem()
        if not item: return
        self.clearFocus()
        nuevo, ok = self.obtener_texto_dialogo_oscuro("Editar Categoría", "Nuevo nombre:", texto_previo=item.text())
        if ok and nuevo.strip():
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
            if cat: 
                cat.nombre = nuevo.strip()
                db.commit()
            db.close()
            self.actualizar_catalogo_meds()
        self.lista_cat_med.setFocus()

    def admin_del_cat_med(self):
        item = self.lista_cat_med.currentItem()
        if not item: return
        self.clearFocus()
        box = QMessageBox(QMessageBox.Question, "Confirmar", f"¿Borrar '{item.text()}' y sus medicamentos?", QMessageBox.Yes | QMessageBox.No, self)
        box.setStyleSheet(tema.ESTILO_VENTANA)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
            if cat: 
                db.delete(cat)
                db.commit()
            db.close()
            self.actualizar_catalogo_meds()
        self.lista_cat_med.setFocus()

    def admin_add_med(self):
        item_cat = self.lista_cat_med.currentItem()
        if not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nuevo Medicamento", f"Medicamento para {cat_nombre}:")
        if ok and nombre.strip():
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == cat_nombre).first()
            if cat:
                db.add(MedicamentoCatalogo(nombre=nombre.strip(), categoria_id=cat.id))
                db.commit()
            db.close()
            self.actualizar_catalogo_meds()
            self.restaurar_categoria_med(cat_nombre)
        self.lista_meds_cat.setFocus()

    def admin_edit_med(self):
        item_med = self.lista_meds_cat.currentItem()
        item_cat = self.lista_cat_med.currentItem()
        if not item_med or not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        nuevo, ok = self.obtener_texto_dialogo_oscuro("Editar Medicamento", "Nuevo nombre:", texto_previo=item_med.text())
        if ok and nuevo.strip():
            db = SessionLocal()
            med = db.query(MedicamentoCatalogo).filter(MedicamentoCatalogo.nombre == item_med.text()).first()
            if med: 
                med.nombre = nuevo.strip()
                db.commit()
            db.close()
            self.actualizar_catalogo_meds()
            self.restaurar_categoria_med(cat_nombre)
        self.lista_meds_cat.setFocus()

    def admin_del_med(self):
        item_med = self.lista_meds_cat.currentItem()
        item_cat = self.lista_cat_med.currentItem()
        if not item_med or not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        db = SessionLocal()
        med = db.query(MedicamentoCatalogo).filter(MedicamentoCatalogo.nombre == item_med.text()).first()
        if med: 
            db.delete(med)
            db.commit()
        db.close()
        self.actualizar_catalogo_meds()
        self.restaurar_categoria_med(cat_nombre)
        self.lista_meds_cat.setFocus()

    def imprimir_recipe_actual(self, formato="pdf"):
        if not self.paciente_actual_id: return
        self.clearFocus()
        db = SessionLocal()
        doctor = db.query(PerfilDoctor).first()
        paciente = db.query(Paciente).get(self.paciente_actual_id)
        if not doctor:
            box = QMessageBox(QMessageBox.Warning, "Configuración", "Debe configurar el perfil primero.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            db.close()
            return
            
        meds = []
        for i in range(self.tabla_recipe.rowCount()):
            med_name = self.tabla_recipe.item(i, 0).text()
            ind_widget = self.tabla_recipe.cellWidget(i, 1)
            ind_text = ind_widget.toPlainText() if ind_widget else ""
            meds.append((med_name, ind_text))
            
        if not meds:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Añada medicamentos al récipe.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            db.close()
            return
            
        try:
            ruta = MotorImpresion.generar_pdf_recipe(doctor, paciente, meds, formato)
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta)))
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error", f"Fallo impresión del récipe: {e}", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
        finally: 
            db.close()

    def actualizar_catalogo_examenes(self):
        db = SessionLocal()
        self.lista_cat_ex.clear()
        self.arbol_busqueda_ex.clear()
        
        categorias = db.query(CategoriaExamen).order_by(CategoriaExamen.nombre).all()
        for c in categorias: 
            self.lista_cat_ex.addItem(c.nombre)
            
            cat_item = QTreeWidgetItem(self.arbol_busqueda_ex, [f"📁 {c.nombre}"])
            cat_item.setData(0, Qt.UserRole, "CATEGORIA")
            cat_item.setForeground(0, QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
            font = cat_item.font(0); font.setBold(True); cat_item.setFont(0, font)
            
            for ex in sorted(c.examenes, key=lambda x: x.nombre):
                ex_item = QTreeWidgetItem(cat_item, [f"🔬 {ex.nombre}"])
                ex_item.setData(0, Qt.UserRole, "EXAMEN")
                ex_item.setData(0, Qt.UserRole + 1, ex.nombre) 
                
        db.close()

    def filtrar_catalogo_ex(self, texto):
        texto = texto.lower()
        for i in range(self.arbol_busqueda_ex.topLevelItemCount()):
            cat_item = self.arbol_busqueda_ex.topLevelItem(i)
            cat_match = texto in cat_item.text(0).lower()
            
            tiene_hijo_visible = False
            for j in range(cat_item.childCount()):
                ex_item = cat_item.child(j)
                ex_match = texto in ex_item.text(0).lower()
                
                if cat_match or ex_match:
                    ex_item.setHidden(False)
                    tiene_hijo_visible = True
                else:
                    ex_item.setHidden(True)
            
            if tiene_hijo_visible or cat_match:
                cat_item.setHidden(False)
                if texto: cat_item.setExpanded(True)
            else:
                cat_item.setHidden(True)

    def agregar_a_orden_ex(self, item, column):
        if item.data(0, Qt.UserRole) != "EXAMEN":
            item.setExpanded(not item.isExpanded()) 
            return
            
        nombre_examen = item.data(0, Qt.UserRole + 1)
        row = self.tabla_examenes.rowCount()
        self.tabla_examenes.insertRow(row)
        
        item_table = QTableWidgetItem(nombre_examen)
        item_table.setForeground(QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
        self.tabla_examenes.setItem(row, 0, item_table)
        
        in_ind = QTextEdit()
        in_ind.setPlaceholderText("Observación / Justificación...")
        in_ind.setFixedHeight(40)
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        in_ind.setStyleSheet(f"""
            QTextEdit {{ border: {border_entry}; background-color: {color_fondo_entry}; color: {color_txt}; font-size: 14px; padding: 4px; border-radius: 4px; }}
            QTextEdit:focus {{ border: 1px solid {tema.MENTA_MEDICA}; background-color: {color_fondo_entry}; color: {color_txt}; }}
        """)
        
        def adaptar_altura():
            doc_height = int(in_ind.document().size().height())
            in_ind.setFixedHeight(max(40, doc_height + 10))
            self.tabla_examenes.resizeRowsToContents()
            
        in_ind.textChanged.connect(adaptar_altura)
        self.tabla_examenes.setCellWidget(row, 1, in_ind)
        
        btn_del = QPushButton("❌")
        btn_del.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        btn_del.clicked.connect(lambda: self.tabla_examenes.removeRow(self.tabla_examenes.indexAt(btn_del.pos()).row()))
        self.tabla_examenes.setCellWidget(row, 2, btn_del)

    def cargar_examenes_categoria(self):
        item = self.lista_cat_ex.currentItem()
        if not item: return
        db = SessionLocal()
        cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
        self.lista_examenes_cat_ex.clear()
        if cat:
            for ex in cat.examenes: self.lista_examenes_cat_ex.addItem(ex.nombre)
        db.close()

    def restaurar_categoria_ex(self, nombre_cat):
        items = self.lista_cat_ex.findItems(nombre_cat, Qt.MatchExactly)
        if items: self.lista_cat_ex.setCurrentItem(items[0])

    def admin_add_cat_ex(self):
        self.clearFocus()
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nueva Categoría", "Nombre de la categoría:")
        if ok and nombre.strip():
            db = SessionLocal()
            db.add(CategoriaExamen(nombre=nombre.strip()))
            db.commit()
            db.close()
            self.actualizar_catalogo_examenes()
        self.lista_cat_ex.setFocus()

    def admin_edit_cat_ex(self):
        item = self.lista_cat_ex.currentItem()
        if not item: return
        self.clearFocus()
        nuevo, ok = self.obtener_texto_dialogo_oscuro("Editar Categoría", "Nuevo nombre:", texto_previo=item.text())
        if ok and nuevo.strip():
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
            if cat: 
                cat.nombre = nuevo.strip()
                db.commit()
            db.close()
            self.actualizar_catalogo_examenes()
        self.lista_cat_ex.setFocus()

    def admin_del_cat_ex(self):
        item = self.lista_cat_ex.currentItem()
        if not item: return
        self.clearFocus()
        box = QMessageBox(QMessageBox.Question, "Confirmar", f"¿Borrar '{item.text()}' y sus exámenes?", QMessageBox.Yes | QMessageBox.No, self)
        box.setStyleSheet(tema.ESTILO_VENTANA)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
            if cat: 
                db.delete(cat)
                db.commit()
            db.close()
            self.actualizar_catalogo_examenes()
        self.lista_cat_ex.setFocus()

    def admin_add_ex(self):
        item_cat = self.lista_cat_ex.currentItem()
        if not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        nombre, ok = self.obtener_texto_dialogo_oscuro("Nuevo Examen", f"Examen para {cat_nombre}:")
        if ok and nombre.strip():
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == cat_nombre).first()
            if cat:
                db.add(ExamenCatalogo(nombre=nombre.strip(), categoria_id=cat.id))
                db.commit()
            db.close()
            self.actualizar_catalogo_examenes()
            self.restaurar_categoria_ex(cat_nombre)
        self.lista_examenes_cat_ex.setFocus()

    def admin_edit_ex(self):
        item_ex = self.lista_examenes_cat_ex.currentItem()
        item_cat = self.lista_cat_ex.currentItem()
        if not item_ex or not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        nuevo, ok = self.obtener_texto_dialogo_oscuro("Editar Examen", "Nuevo nombre:", texto_previo=item_ex.text())
        if ok and nuevo.strip():
            db = SessionLocal()
            ex = db.query(ExamenCatalogo).filter(ExamenCatalogo.nombre == item_ex.text()).first()
            if ex: 
                ex.nombre = nuevo.strip()
                db.commit()
            db.close()
            self.actualizar_catalogo_examenes()
            self.restaurar_categoria_ex(cat_nombre)
        self.lista_examenes_cat_ex.setFocus()

    def admin_del_ex(self):
        item_ex = self.lista_examenes_cat_ex.currentItem()
        item_cat = self.lista_cat_ex.currentItem()
        if not item_ex or not item_cat: return
        cat_nombre = item_cat.text()
        self.clearFocus()
        db = SessionLocal()
        ex = db.query(ExamenCatalogo).filter(ExamenCatalogo.nombre == item_ex.text()).first()
        if ex: 
            db.delete(ex)
            db.commit()
        db.close()
        self.actualizar_catalogo_examenes()
        self.restaurar_categoria_ex(cat_nombre)
        self.lista_examenes_cat_ex.setFocus()

    def imprimir_orden_actual(self, formato="pdf"):
        if not self.paciente_actual_id: return
        self.clearFocus()
        db = SessionLocal()
        doctor = db.query(PerfilDoctor).first()
        paciente = db.query(Paciente).get(self.paciente_actual_id)
        if not doctor:
            box = QMessageBox(QMessageBox.Warning, "Configuración", "Debe configurar el perfil primero.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            db.close()
            return
            
        lista = []
        for i in range(self.tabla_examenes.rowCount()):
            ex_name = self.tabla_examenes.item(i, 0).text()
            obs_widget = self.tabla_examenes.cellWidget(i, 1)
            obs_text = obs_widget.toPlainText() if obs_widget else ""
            lista.append((ex_name, obs_text))
            
        if not lista:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Añada exámenes a la orden médica.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
            db.close()
            return
            
        try:
            ruta = MotorImpresion.generar_pdf_ordenes(doctor, paciente, lista, formato)
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(ruta)))
        except Exception as e:
            box = QMessageBox(QMessageBox.Critical, "Error", f"Fallo impresión de ordenes: {e}", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA)
            box.exec()
        finally: 
            db.close()

    def guardar_consulta(self):
        if not self.paciente_actual_id: return
        db = SessionLocal()
        try:
            def val(ent, bg): return ent.toPlainText().strip() if bg.buttons()[1].isChecked() else "No aplica"
            def val_int(ent, bg): 
                t = ent.toPlainText().strip()
                return int(t) if bg.buttons()[1].isChecked() and t.isdigit() else 0
            
            p_val = self.in_peso.text().replace(",", ".")
            a_val = self.in_altura.text().replace(",", ".")
            if a_val.replace(".", "").isdigit() and len(a_val.replace(".", "")) >= 3 and "." not in a_val:
                a_val = f"{a_val[0]}.{a_val[1:]}"

            nueva_consulta = Consulta(
                paciente_id=self.paciente_actual_id,
                edad_paciente=self.edad_calculada,
                motivo_consulta=self.in_motivo.toPlainText().strip(),
                enfermedad_actual=self.in_enfermedad.toPlainText().strip(),
                nota_evolutiva=val(self.in_nota, self.bg_nota),
                impresion_diagnostica=self.in_impresion_diag.toPlainText().strip(),
                diagnostico=self.in_diagnostico.toPlainText().strip(),
                estudios_indicados=self.in_estudios_ind.toPlainText().strip(),
                peso=float(p_val) if p_val else 0.0,
                altura=float(a_val) if a_val else 0.0,
                imc=float(self.calcular_imc()),
                tension_arterial=val(self.in_ta, self.bg_ta),
                pulso=val_int(self.in_pulso, self.bg_pulso),
                **{k: val(v[0], v[1]) for k, v in self.referencias_ef.items() if hasattr(Consulta, k)}
            )
            db.add(nueva_consulta)
            db.flush()

            p = db.query(Paciente).get(self.paciente_actual_id)

            if self.group_ant_base.isChecked():
                if not p.antecedentes: 
                    p.antecedentes = Antecedentes(paciente_id=p.id)
                    db.add(p.antecedentes) 
                p.antecedentes.alergias = self.in_ant_alergias.text()
                p.antecedentes.personales = self.in_ant_personales.toPlainText()
                p.antecedentes.familiares = self.in_ant_familiares.toPlainText()
                p.antecedentes.operaciones_realizadas = self.in_ant_operaciones.toPlainText()
                
                p.antecedentes.habito_fuma = val(self.in_fuma, self.bg_fuma)
                p.antecedentes.habito_bebe = val(self.in_bebe, self.bg_bebe)
                p.antecedentes.otros_habitos = val(self.in_otros_h, self.bg_otros_h)
                p.antecedentes.examen_funcional = self.in_examen_funcional.toPlainText().strip()

            if p.genero and p.genero.strip().lower() in ["femenino", "mujer"] and self.group_gineco.isChecked():
                algun_dato_gineco = any(ent.toPlainText().strip() for ent in self.referencias_gin.values()) or self.bg_incont.buttons()[1].isChecked()
                
                if algun_dato_gineco:
                    nuevo_gin = GinecoObstetrico(paciente_id=p.id)
                    db.add(nuevo_gin)
                    
                    def t_val(clave): return self.referencias_gin[clave].toPlainText().strip()
                    def i_val(clave): 
                        txt = self.referencias_gin[clave].toPlainText().strip()
                        return int(txt) if txt.isdigit() else 0
                    
                    nuevo_gin.menarquia = t_val("menarquia")
                    nuevo_gin.menopausia = t_val("menopausia")
                    nuevo_gin.sangramiento = t_val("sangramiento")
                    nuevo_gin.flujo = t_val("flujo")
                    nuevo_gin.diu = t_val("diu")
                    nuevo_gin.aco = t_val("aco")
                    
                    nuevo_gin.gestas = i_val("gestas")
                    nuevo_gin.abortos = i_val("abortos")
                    nuevo_gin.embarazo_ectopico = i_val("embarazo_ectopico")
                    nuevo_gin.partos = i_val("partos")
                    nuevo_gin.cesarea = i_val("cesarea")
                    
                    nuevo_gin.incontinencia = self.bg_incont.buttons()[1].isChecked()

            if self.tabla_recipe.rowCount() > 0:
                it, ins = [], []
                for i in range(self.tabla_recipe.rowCount()):
                    med_item = self.tabla_recipe.item(i, 0)
                    ind_widget = self.tabla_recipe.cellWidget(i, 1)
                    if med_item and ind_widget:
                        it.append(med_item.text())
                        ins.append(ind_widget.toPlainText().strip())
                        
                nuevo_doc = RecipeOrden(
                    paciente_id=self.paciente_actual_id,
                    consulta_id=nueva_consulta.id,
                    tipo_documento="RÉCIPE MÉDICO",
                    items="\n".join(it),
                    instrucciones="\n".join(ins)
                )
                db.add(nuevo_doc)
                
            if self.tabla_examenes.rowCount() > 0:
                it_ex, ins_ex = [], []
                for i in range(self.tabla_examenes.rowCount()):
                    ex_item = self.tabla_examenes.item(i, 0)
                    obs_widget = self.tabla_examenes.cellWidget(i, 1)
                    if ex_item and obs_widget:
                        it_ex.append(ex_item.text())
                        ins_ex.append(obs_widget.toPlainText().strip())
                        
                nueva_orden = RecipeOrden(
                    paciente_id=self.paciente_actual_id,
                    consulta_id=nueva_consulta.id,
                    tipo_documento="ORDEN DE EXÁMENES",
                    items="\n".join(it_ex),
                    instrucciones="\n".join(ins_ex)
                )
                db.add(nueva_orden)

            db.commit()
            box = QMessageBox(QMessageBox.Information, "Éxito", "Historial clínico de consulta guardado correctamente.", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
            self.limpiar_todo()
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"Fallo crítico al sincronizar base de datos: {e}", QMessageBox.Ok, self)
            box.setStyleSheet(tema.ESTILO_VENTANA); box.exec()
        finally: 
            db.close()

    def calcular_imc(self):
        try:
            p_text = self.in_peso.text().replace(",", "."); a_text = self.in_altura.text().replace(",", ".")
            if a_text.replace(".", "").isdigit() and len(a_text.replace(".", "")) >= 3 and "." not in a_text:
                a_text = f"{a_text[0]}.{a_text[1:]}"
            if p_text and a_text:
                p, a = float(p_text), float(a_text)
                if a > 0:
                    imc = p / (a ** 2)
                    self.lbl_imc.setText(f"<b>IMC: {imc:.2f}</b>"); return imc
        except: pass
        self.lbl_imc.setText("<b>IMC: --</b>"); return 0.0

    def cargar_datos_paciente(self, paciente_id):
        self.limpiar_todo()
        self.paciente_actual_id = paciente_id
        db = SessionLocal(); p = db.query(Paciente).get(paciente_id)
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_id.setText(f"<b>ID:</b> {p.cedula}")
            self.edad_calculada = p.edad_actual
            self.lbl_edad.setText(f"<b>EDAD CLÍNICA:</b> {self.edad_calculada} años")
            es_fem = (p.genero == "Femenino")
            self.group_ef_femenino.setVisible(es_fem); self.group_gineco.setVisible(es_fem); self.group_ef_masculino.setVisible(not es_fem)
            
            consultas_previas = db.query(Consulta).filter(Consulta.paciente_id == p.id).order_by(Consulta.fecha_consulta.desc()).all()
            if consultas_previas:
                self.in_impresion_diag.setPlainText(consultas_previas[0].impresion_diagnostica or "")
                self.lbl_diagnostico.show()
                self.w_diagnostico.show()
            else:
                self.lbl_diagnostico.hide()
                self.w_diagnostico.hide()

            if p.antecedentes:
                self.in_ant_alergias.setText(p.antecedentes.alergias or "")
                self.in_ant_personales.setPlainText(p.antecedentes.personales or "")
                self.in_ant_familiares.setPlainText(p.antecedentes.familiares or "")
                self.in_ant_operaciones.setPlainText(p.antecedentes.operaciones_realizadas or "")
                self.in_examen_funcional.setPlainText(p.antecedentes.examen_funcional or "")
                
                def cargar_habito(texto_bd, entrada, bg):
                    if texto_bd and texto_bd != "No aplica":
                        bg.buttons()[1].setChecked(True)
                        entrada.setVisible(True)
                        entrada.setPlainText(texto_bd)
                    else:
                        bg.buttons()[0].setChecked(True)
                        entrada.setVisible(False)
                        entrada.clear()

                cargar_habito(p.antecedentes.habito_fuma, self.in_fuma, self.bg_fuma)
                cargar_habito(p.antecedentes.habito_bebe, self.in_bebe, self.bg_bebe)
                cargar_habito(p.antecedentes.otros_habitos, self.in_otros_h, self.bg_otros_h)
            if es_fem:
                gin = db.query(GinecoObstetrico).filter(GinecoObstetrico.paciente_id == p.id).order_by(GinecoObstetrico.fecha_registro.desc()).first()
                if gin:
                    self.referencias_gin["menarquia"].setText(gin.menarquia or "")
                    self.referencias_gin["gestas"].setText(str(gin.gestas) if gin.gestas is not None else "")
                    self.referencias_gin["abortos"].setText(str(gin.abortos) if gin.abortos is not None else "")
                    self.referencias_gin["embarazo_ectopico"].setText(str(gin.embarazo_ectopico) if gin.embarazo_ectopico is not None else "")
                    self.referencias_gin["partos"].setText(str(gin.partos) if gin.partos is not None else "")
                    self.referencias_gin["cesarea"].setText(str(gin.cesarea) if gin.cesarea is not None else "")
                    self.referencias_gin["menopausia"].setText(gin.menopausia or "")
                    self.referencias_gin["sangramiento"].setText(gin.sangramiento or "")
                    self.referencias_gin["flujo"].setText(gin.flujo or "")
                    self.referencias_gin["diu"].setText(gin.diu or "")
                    self.referencias_gin["aco"].setText(gin.aco or "")
                    if gin.incontinencia:
                        self.bg_incont.buttons()[1].setChecked(True)
                    else:
                        self.bg_incont.buttons()[0].setChecked(True) 
                else:
                    for ent in self.referencias_gin.values(): ent.clear()
                    self.bg_incont.buttons()[0].setChecked(True)
        db.close()
        self.actualizar_diseno_dinamico()

    def limpiar_todo(self):
        self.in_motivo.clear(); self.in_enfermedad.clear(); self.in_impresion_diag.clear()
        self.in_diagnostico.clear(); self.in_estudios_ind.clear()
        self.in_examen_funcional.clear()
        self.in_ant_personales.clear(); self.in_ant_familiares.clear(); self.in_ant_operaciones.clear()
        self.lbl_imc.setText("<b>IMC: --</b>")
        self.group_ant_base.setChecked(False)
        self.group_gineco.setChecked(False) 
        self.tabla_recipe.setRowCount(0)
        self.tabla_examenes.setRowCount(0) 
        
        for le in self.findChildren(QLineEdit): le.clear()
            
        for qte in self.findChildren(QTextEdit):
            if qte not in [self.in_motivo, self.in_enfermedad, self.in_impresion_diag, self.in_diagnostico, 
                           self.in_estudios_ind, self.in_examen_funcional, 
                           self.in_ant_personales, self.in_ant_familiares, self.in_ant_operaciones]:
                qte.clear()
                qte.setVisible(False)
                qte.setFixedHeight(40)
                
        for rb in self.findChildren(QRadioButton):
            if rb.text() in ["No aplica", "No"]: rb.setChecked(True)