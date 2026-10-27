from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox, QFrame, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, 
                             QTabWidget, QInputDialog, QTreeWidget, QTreeWidgetItem, 
                             QListWidgetItem, QApplication, QMenu)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QBrush, QColor, QAction
from database import SessionLocal
from models import (Paciente, PerfilDoctor, ArchivoPaciente, RecipeOrden,
                    ExamenCatalogo, CategoriaExamen, 
                    MedicamentoCatalogo, CategoriaMedicamento)
from servicios_impresion import MotorImpresion
import os
import re
import shutil
from datetime import datetime
from estilos import tema  # Importación del motor de diseño centralizado

# =================================================================
# 1. PANTALLA DE RECETA RÁPIDA
# =================================================================
class PantallaRecetaRapida(QWidget):
    volver_historial = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.ruta_base = "archivos_clinica"
        
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)

        # 1. Cabecera
        self.frame_paciente = QFrame()
        lay_h = QHBoxLayout(self.frame_paciente)
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_cedula = QLabel("<b>CÉDULA:</b> --")
        lay_h.addWidget(self.lbl_paciente); lay_h.addWidget(self.lbl_cedula)
        layout_principal.addWidget(self.frame_paciente)

        # 2. Tabs
        self.tabs = QTabWidget()
        
        # --- PESTAÑA A: GENERAR RÉCIPE ---
        self.tab_generar = QWidget()
        lay_gen = QHBoxLayout(self.tab_generar)
        
        # Panel Izquierdo: Buscador con Árbol
        panel_izq = QVBoxLayout()
        self.lbl_tit_buscar = QLabel("<b>🔍 Buscar Medicamento:</b>")
        panel_izq.addWidget(self.lbl_tit_buscar)
        self.in_buscador = QLineEdit()
        self.in_buscador.setPlaceholderText("Escriba para filtrar...")
        self.in_buscador.textChanged.connect(self.filtrar_catalogo)
        panel_izq.addWidget(self.in_buscador)
        
        self.arbol_busqueda = QTreeWidget()
        self.arbol_busqueda.setHeaderHidden(True)
        self.arbol_busqueda.itemDoubleClicked.connect(self.agregar_al_recipe)
        panel_izq.addWidget(self.arbol_busqueda)
        lay_gen.addLayout(panel_izq, 30)

        # Panel Derecho: Récipe Actual
        panel_der = QVBoxLayout()
        self.lbl_tit_en_recipe = QLabel("<b>📋 Medicamentos en este Récipe:</b>")
        panel_der.addWidget(self.lbl_tit_en_recipe)
        
        self.tabla_recipe = QTableWidget(0, 3)
        self.tabla_recipe.setHorizontalHeaderLabels(["Medicamento", "Indicaciones", "Acción"])
        self.tabla_recipe.setColumnWidth(0, 180) 
        self.tabla_recipe.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_recipe.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_recipe.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        panel_der.addWidget(self.tabla_recipe)
        
        # Botón con Menú Desplegable (PDF / Word)
        self.btn_generar_doc = QPushButton("🖨️ GENERAR RÉCIPE ▾")
        self.btn_generar_doc.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
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
        
        lay_btn_footer = QHBoxLayout()
        lay_btn_footer.setSpacing(10)
        self.btn_volver = QPushButton("Volver al Historial")
        self.btn_volver.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_volver.setFixedHeight(45)
        self.btn_volver.clicked.connect(self.volver_historial.emit)
        
        lay_btn_footer.addWidget(self.btn_volver)
        lay_btn_footer.addWidget(self.btn_generar_doc)
        panel_der.addLayout(lay_btn_footer)
        
        lay_gen.addLayout(panel_der, 70)
        self.tabs.addTab(self.tab_generar, "📝 Generar Récipe")

        # --- PESTAÑA B: ADMINISTRAR CATÁLOGO DE MEDICAMENTOS ---
        self.tab_admin = QWidget()
        lay_admin = QHBoxLayout(self.tab_admin)
        
        col_cat = QVBoxLayout()
        self.lbl_tit_cats = QLabel("<b>📁 Categorías de Medicamentos:</b>")
        col_cat.addWidget(self.lbl_tit_cats)
        self.lista_categorias = QListWidget()
        self.lista_categorias.currentRowChanged.connect(self.cargar_medicamentos_categoria)
        col_cat.addWidget(self.lista_categorias)
        
        lay_btn_cat = QHBoxLayout()
        lay_btn_cat.setSpacing(6)
        self.btn_add_cat = QPushButton("➕"); self.btn_add_cat.clicked.connect(self.admin_agregar_categoria)
        self.btn_edit_cat = QPushButton("✏️"); self.btn_edit_cat.clicked.connect(self.admin_editar_categoria)
        self.btn_del_cat = QPushButton("🗑️"); self.btn_del_cat.clicked.connect(self.admin_borrar_categoria)
        for b in [self.btn_add_cat, self.btn_edit_cat, self.btn_del_cat]:
            b.setFixedSize(100, 50) 
        lay_btn_cat.addWidget(self.btn_add_cat); lay_btn_cat.addWidget(self.btn_edit_cat); lay_btn_cat.addWidget(self.btn_del_cat)
        lay_btn_cat.addStretch()
        col_cat.addLayout(lay_btn_cat)
        lay_admin.addLayout(col_cat)

        col_med = QVBoxLayout()
        self.lbl_tit_meds_cat = QLabel("<b>💊 Medicamentos en Categoría:</b>")
        col_med.addWidget(self.lbl_tit_meds_cat)
        self.lista_medicamentos_cat = QListWidget()
        col_med.addWidget(self.lista_medicamentos_cat)
        
        lay_btn_med = QHBoxLayout()
        lay_btn_med.setSpacing(6)
        self.btn_add_med = QPushButton("➕"); self.btn_add_med.clicked.connect(self.admin_agregar_medicamento)
        self.btn_edit_med = QPushButton("✏️"); self.btn_edit_med.clicked.connect(self.admin_editar_medicamento)
        self.btn_del_med = QPushButton("🗑️"); self.btn_del_med.clicked.connect(self.admin_borrar_medicamento)
        for b in [self.btn_add_med, self.btn_edit_med, self.btn_del_med]:
            b.setFixedSize(100, 50) 
        lay_btn_med.addWidget(self.btn_add_med); lay_btn_med.addWidget(self.btn_edit_med); lay_btn_med.addWidget(self.btn_del_med)
        lay_btn_med.addStretch()
        col_med.addLayout(lay_btn_med)
        lay_admin.addLayout(col_med)

        self.tabs.addTab(self.tab_admin, "⚙️ Administrar Catálogo")
        layout_principal.addWidget(self.tabs)

        # Conexión dinámica
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def obtener_texto_dialogo_oscuro(self, titulo, etiqueta, texto_previo=""):
        app = QApplication.instance()
        manejador = getattr(app, "manejador_voz", None)
        
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

        if manejador:
            manejador.desbloquear_voz()

        return texto, ok

    def ajustar_emergente_parent(self, box):
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_tabla = "#424549" if tema.modo_actual == "oscuro" else tema.BG_INPUT

        # 1. Cabecera superior adaptada
        border_head = "#4f545c" if tema.modo_actual == "oscuro" else "#f1c40f"
        bg_head = tema.BG_TARJETA if tema.modo_actual == "oscuro" else "#fef9e7"
        self.frame_paciente.setStyleSheet(f"background-color: {bg_head}; border-radius: 10px; border: 1px solid {border_head};")
        self.lbl_paciente.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")
        self.lbl_cedula.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")

        # 2. Re-estilizar Pestañas
        self.tab_generar.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.tab_admin.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {tema.BORDE_SUAVE}; background-color: {color_fondo_paginas}; }}
            QTabBar::tab {{
                background-color: {color_fondo_tabla}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE};
                padding: 10px 20px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; }}
        """)

        # 3. Inputs y Buscadores
        self.in_buscador.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 6px; font-size: 14px;")

        # 4. Árboles de búsqueda, Tablas y Listas Administrables
        self.arbol_busqueda.setStyleSheet(f"""
            QTreeWidget {{ background-color: {color_fondo_tabla}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 5px; font-size: 14px; }}
            QTreeView::item {{ color: {color_txt}; }}
            QTreeView::item:hover {{ background-color: {tema.MENTA_FOCUS}; }}
            QTreeView::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; }}
        """)
        
        self.tabla_recipe.setStyleSheet(f"""
            QTableWidget {{ background-color: {color_fondo_tabla}; color: {color_txt}; gridline-color: {tema.COLOR_DIVISION_TABLA}; border: 1px solid {tema.BORDE_SUAVE}; font-size: 13px; }}
            QHeaderView::section {{ background-color: #93F6E3; color: #1C1C1C; font-weight: bold; padding: 6px; border: 1px solid {tema.BORDE_SUAVE}; }}
        """)

        for lista in [self.lista_categorias, self.lista_medicamentos_cat]:
            lista.setStyleSheet(f"""
                QListWidget {{ 
                    background-color: {color_fondo_tabla}; 
                    color: {color_txt}; 
                    border: 1px solid {tema.BORDE_SUAVE}; 
                    border-radius: 6px; 
                    padding: 5px; 
                    font-size: 15px; 
                }}
                QListWidget::item {{ 
                    color: {color_txt}; 
                }}
                QListWidget::item:hover {{ 
                    background-color: {tema.MENTA_FOCUS}; 
                    color: {color_txt}; 
                }}
                QListWidget::item:selected {{ 
                    background-color: {tema.MENTA_MEDICA}; 
                    color: #1C1C1C; 
                    font-weight: bold; 
                }}
            """)

        # 5. Etiquetas de Título
        for lbl in [self.lbl_tit_buscar, self.lbl_tit_en_recipe, self.lbl_tit_cats, self.lbl_tit_meds_cat]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 13px; background: transparent;")

        # 6. Mini botones de administración
        for btn in [self.btn_add_cat, self.btn_edit_cat, self.btn_add_med, self.btn_edit_med]:
            btn.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_del_cat.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_del_med.setStyleSheet(tema.ESTILO_BTN_PELIGRO)

        self.btn_generar_doc.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)

        self.actualizar_estilo_celdas_internas()

    def actualizar_estilo_celdas_internas(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        for row in range(self.tabla_recipe.rowCount()):
            item_med = self.tabla_recipe.item(row, 0)
            if item_med:
                item_med.setForeground(QColor(color_txt))
            
            in_ind = self.tabla_recipe.cellWidget(row, 1)
            if in_ind:
                in_ind.setStyleSheet(f"""
                    QTextEdit {{
                        border: {border_entry}; 
                        background-color: {color_fondo_entry}; 
                        color: {color_txt}; 
                        font-size: 14px; 
                        padding: 4px;
                        border-radius: 4px;
                    }}
                    QTextEdit:focus {{
                        border: 1px solid {tema.MENTA_MEDICA}; 
                        background-color: {color_fondo_entry}; 
                        color: {color_txt}; 
                    }}
                """)
            
            btn_del = self.tabla_recipe.cellWidget(row, 2)
            if btn_del:
                btn_del.setStyleSheet(f"""
                    QPushButton {{ background-color: transparent; border: none; font-size: 15px; }}
                    QPushButton:hover {{ background-color: {tema.ROJO_PELIGRO}; border-radius: 4px; }}
                """)

    # --- LÓGICA DE ADMINISTRACIÓN (CATÁLOGO MEDICAMENTOS) ---
    def actualizar_todo_el_catalogo(self):
        db = SessionLocal()
        self.lista_categorias.clear()
        self.arbol_busqueda.clear()
        
        categorias = db.query(CategoriaMedicamento).order_by(CategoriaMedicamento.nombre).all()
        color_folder = QColor("#93F6E3") if tema.modo_actual == "oscuro" else QColor("#2c3e50")
        color_letras = QColor("#FFFFFF") if tema.modo_actual == "oscuro" else QColor(tema.TEXTO_MAIN)
        
        for c in categorias: 
            item_c = QListWidgetItem(c.nombre)
            item_c.setForeground(color_letras)
            self.lista_categorias.addItem(item_c)
            
            cat_item = QTreeWidgetItem(self.arbol_busqueda, [f"📁 {c.nombre}"])
            cat_item.setData(0, Qt.UserRole, "CATEGORIA")
            cat_item.setForeground(0, QBrush(color_folder))
            font = cat_item.font(0); font.setBold(True); cat_item.setFont(0, font)
            
            for med in sorted(c.medicamentos, key=lambda x: x.nombre):
                med_item = QTreeWidgetItem(cat_item, [f"💊 {med.nombre}"])
                med_item.setData(0, Qt.UserRole, "MEDICAMENTO")
                med_item.setData(0, Qt.UserRole + 1, med.nombre)
                med_item.setForeground(0, QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
        db.close()

    def cargar_medicamentos_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        db = SessionLocal()
        cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
        self.lista_medicamentos_cat.clear()
        
        color_letras = QColor("#FFFFFF") if tema.modo_actual == "oscuro" else QColor(tema.TEXTO_MAIN)
        
        if cat:
            for med in cat.medicamentos: 
                item_med = QListWidgetItem(med.nombre)
                item_med.setForeground(color_letras) 
                self.lista_medicamentos_cat.addItem(item_med)
        db.close()

    def restaurar_categoria(self, nombre_cat):
        items = self.lista_categorias.findItems(nombre_cat, Qt.MatchExactly)
        if items: self.lista_categorias.setCurrentItem(items[0])

    def admin_agregar_categoria(self):
        texto, ok = self.obtener_texto_dialogo_oscuro("Nueva Categoría", "Nombre de la categoría:")
        if ok and texto.strip():
            db = SessionLocal()
            db.add(CategoriaMedicamento(nombre=texto.strip()))
            db.commit(); db.close(); self.actualizar_todo_el_catalogo()

    def admin_editar_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        texto, ok = self.obtener_texto_dialogo_oscuro("Editar", "Nuevo nombre:", item.text())
        if ok and texto.strip():
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
            if cat: cat.nombre = texto.strip(); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()

    def admin_borrar_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        box = QMessageBox(QMessageBox.Question, "Confirmar", f"¿Borrar '{item.text()}' y sus medicamentos?", QMessageBox.Yes | QMessageBox.No, self)
        self.ajustar_emergente_parent(box)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == item.text()).first()
            if cat: db.delete(cat); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()

    def admin_agregar_medicamento(self):
        item_cat = self.lista_categorias.currentItem()
        if not item_cat: 
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione una categoría.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec(); return
        cat_nombre = item_cat.text()
        texto, ok = self.obtener_texto_dialogo_oscuro("Nuevo Medicamento", f"Medicamento para {cat_nombre}:")
        if ok and texto.strip():
            db = SessionLocal()
            cat = db.query(CategoriaMedicamento).filter(CategoriaMedicamento.nombre == cat_nombre).first()
            db.add(MedicamentoCatalogo(nombre=texto.strip(), categoria_id=cat.id if hasattr(cat, 'categoria_id') else cat.id))
            db.commit(); db.close(); self.actualizar_todo_el_catalogo()
            self.restaurar_categoria(cat_nombre)

    def admin_editar_medicamento(self):
        item_med = self.lista_medicamentos_cat.currentItem()
        item_cat = self.lista_categorias.currentItem()
        if not item_med or not item_cat: return
        cat_nombre = item_cat.text()
        texto, ok = self.obtener_texto_dialogo_oscuro("Editar Medicamento", "Nuevo nombre:", item_med.text())
        if ok and texto.strip():
            db = SessionLocal()
            med = db.query(MedicamentoCatalogo).filter(MedicamentoCatalogo.nombre == item_med.text()).first()
            if med: med.nombre = texto.strip(); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()
            self.restaurar_categoria(cat_nombre)

    def admin_borrar_medicamento(self):
        item_med = self.lista_medicamentos_cat.currentItem()
        item_cat = self.lista_categorias.currentItem()
        if not item_med or not item_cat: return
        cat_nombre = item_cat.text()
        db = SessionLocal()
        med = db.query(MedicamentoCatalogo).filter(MedicamentoCatalogo.nombre == item_med.text()).first()
        if med: db.delete(med); db.commit()
        db.close(); self.actualizar_todo_el_catalogo()
        self.restaurar_categoria(cat_nombre)

    def filtrar_catalogo(self, texto):
        texto = texto.lower()
        for i in range(self.arbol_busqueda.topLevelItemCount()):
            cat_item = self.arbol_busqueda.topLevelItem(i)
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
        
        item_nombre = QTableWidgetItem(nombre_med)
        item_nombre.setForeground(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN))
        self.tabla_recipe.setItem(row, 0, item_nombre)
        
        in_ind = QTextEdit()
        in_ind.setPlaceholderText("Indicaciones (Dosis, frecuencia...)")
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        in_ind.setStyleSheet(f"""
            QTextEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 4px;
                border-radius: 4px;
            }}
            QTextEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry};
                color: {color_txt}; 
            }}
        """)
        in_ind.setFixedHeight(40)
        
        def adaptar_altura():
            doc_height = int(in_ind.document().size().height())
            in_ind.setFixedHeight(max(40, doc_height + 10))
            self.tabla_recipe.resizeRowsToContents()
            
        in_ind.textChanged.connect(adaptar_altura)
        self.tabla_recipe.setCellWidget(row, 1, in_ind)
        
        btn_del = QPushButton("❌")
        btn_del.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; font-size: 14px; }} QPushButton:hover {{ background-color: {tema.ROJO_PELIGRO}; border-radius: 4px; }}")
        btn_del.clicked.connect(lambda: self.tabla_recipe.removeRow(self.tabla_recipe.indexAt(btn_del.pos()).row()))
        self.tabla_recipe.setCellWidget(row, 2, btn_del)

    def cargar_datos(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_cedula.setText(f"<b>CÉDULA:</b> {p.cedula}")
            self.tabla_recipe.setRowCount(0); self.actualizar_todo_el_catalogo()
        db.close()

    def procesar_documento(self, formato="pdf"):
        if not self.paciente_id or self.tabla_recipe.rowCount() == 0: return
        lista, it, ins = [], [], []
        for i in range(self.tabla_recipe.rowCount()):
            med = self.tabla_recipe.item(i, 0).text()
            ind = self.tabla_recipe.cellWidget(i, 1).toPlainText()
            lista.append((med, ind))
            it.append(med); ins.append(ind)
            
        db = SessionLocal()
        p = db.query(Paciente).get(self.paciente_id)
        doctor = db.query(PerfilDoctor).first()
        
        ext = ".docx" if formato.lower() == "docx" else ".pdf"
        tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

        ruta_generada = MotorImpresion.generar_pdf_recipe(doctor, p, lista, formato=formato)
        nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
        ruta_dest = os.path.join(self.ruta_base, f"{nombre_limpio}_{p.cedula}")
        os.makedirs(ruta_dest, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_file = f"RECIPE_{nombre_limpio}_{timestamp}{ext}"
        ruta_final = os.path.join(ruta_dest, nombre_file)
        shutil.move(ruta_generada, ruta_final)
        
        db.add(ArchivoPaciente(paciente_id=self.paciente_id, nombre_archivo=nombre_file, ruta_archivo=ruta_final, tipo_archivo=tipo_reg))
        db.add(RecipeOrden(paciente_id=self.paciente_id, consulta_id=None, tipo_documento="RÉCIPE MÉDICO RÁPIDO", items="\n".join(it), instrucciones="\n".join(ins)))
        db.commit(); db.close()
        
        MotorImpresion.abrir_documento_generado(ruta_final)
        self.volver_historial.emit()


# =================================================================
# 2. PANTALLA DE ORDEN DE EXAMEN
# =================================================================
class PantallaOrdenRapida(QWidget):
    volver_historial = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paciente_id = None
        self.ruta_base = "archivos_clinica"
        
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)

        self.frame_paciente = QFrame()
        lay_h = QHBoxLayout(self.frame_paciente)
        self.lbl_paciente = QLabel("<b>PACIENTE:</b> --")
        self.lbl_cedula = QLabel("<b>CÉDULA:</b> --")
        self.lbl_seguro = QLabel("<b>SEGURO:</b> --")
        lay_h.addWidget(self.lbl_paciente); lay_h.addWidget(self.lbl_cedula); lay_h.addWidget(self.lbl_seguro)
        layout_principal.addWidget(self.frame_paciente)

        self.tabs = QTabWidget()
        
        # --- PESTAÑA A: GENERAR ORDEN ---
        self.tab_generar = QWidget()
        lay_gen = QHBoxLayout(self.tab_generar)
        
        panel_izq = QVBoxLayout()
        self.lbl_tit_buscar_ex = QLabel("<b>🔍 Buscar Examen:</b>")
        panel_izq.addWidget(self.lbl_tit_buscar_ex)
        self.in_buscador = QLineEdit()
        self.in_buscador.setPlaceholderText("Escriba para filtrar...")
        self.in_buscador.textChanged.connect(self.filtrar_catalogo)
        panel_izq.addWidget(self.in_buscador)
        
        self.arbol_busqueda = QTreeWidget()
        self.arbol_busqueda.setHeaderHidden(True)
        self.arbol_busqueda.itemDoubleClicked.connect(self.agregar_a_orden)
        panel_izq.addWidget(self.arbol_busqueda)
        lay_gen.addLayout(panel_izq, 30)

        panel_der = QVBoxLayout()
        self.lbl_tit_en_orden = QLabel("<b>📋 Exámenes en esta Orden:</b>")
        panel_der.addWidget(self.lbl_tit_en_orden)
        
        self.tabla_orden = QTableWidget(0, 3)
        self.tabla_orden.setHorizontalHeaderLabels(["Examen", "Observación", "Acción"])
        self.tabla_orden.setColumnWidth(0, 180) 
        self.tabla_orden.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_orden.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tabla_orden.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        panel_der.addWidget(self.tabla_orden)
        
        # Botón con Menú Desplegable (PDF / Word)
        self.btn_generar_doc = QPushButton("🖨️ GENERAR ORDEN ▾")
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
        
        lay_btn_footer = QHBoxLayout()
        lay_btn_footer.setSpacing(10)
        self.btn_volver = QPushButton("Volver al Historial")
        self.btn_volver.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_volver.setFixedHeight(45)
        self.btn_volver.clicked.connect(self.volver_historial.emit)
        
        lay_btn_footer.addWidget(self.btn_volver)
        lay_btn_footer.addWidget(self.btn_generar_doc)
        panel_der.addLayout(lay_btn_footer)
        
        lay_gen.addLayout(panel_der, 70)
        self.tabs.addTab(self.tab_generar, "📝 Generar Orden")

        # --- PESTAÑA B: ADMINISTRAR CATÁLOGO DE EXÁMENES ---
        self.tab_admin = QWidget()
        lay_admin = QHBoxLayout(self.tab_admin)
        
        col_cat = QVBoxLayout()
        self.lbl_tit_cats_ex = QLabel("<b>📁 Categorías:</b>")
        col_cat.addWidget(self.lbl_tit_cats_ex)
        self.lista_categorias = QListWidget()
        self.lista_categorias.currentRowChanged.connect(self.cargar_examenes_categoria)
        col_cat.addWidget(self.lista_categorias)
        
        lay_btn_cat = QHBoxLayout()
        lay_btn_cat.setSpacing(6)
        self.btn_add_cat = QPushButton("➕"); self.btn_add_cat.clicked.connect(self.admin_agregar_categoria)
        self.btn_edit_cat = QPushButton("✏️"); self.btn_edit_cat.clicked.connect(self.admin_editar_categoria)
        self.btn_del_cat = QPushButton("🗑️"); self.btn_del_cat.clicked.connect(self.admin_borrar_categoria)
        for b in [self.btn_add_cat, self.btn_edit_cat, self.btn_del_cat]:
            b.setFixedSize(100, 50) 
        lay_btn_cat.addWidget(self.btn_add_cat); lay_btn_cat.addWidget(self.btn_edit_cat); lay_btn_cat.addWidget(self.btn_del_cat)
        lay_btn_cat.addStretch()
        col_cat.addLayout(lay_btn_cat)
        lay_admin.addLayout(col_cat)

        col_ex = QVBoxLayout()
        self.lbl_tit_exs_cat = QLabel("<b>🔬 Exámenes en Categoría:</b>")
        col_ex.addWidget(self.lbl_tit_exs_cat)
        self.lista_examenes_cat = QListWidget()
        col_ex.addWidget(self.lista_examenes_cat)
        
        lay_btn_ex = QHBoxLayout()
        lay_btn_ex.setSpacing(6)
        self.btn_add_ex = QPushButton("➕"); self.btn_add_ex.clicked.connect(self.admin_agregar_examen)
        self.btn_edit_ex = QPushButton("✏️"); self.btn_edit_ex.clicked.connect(self.admin_editar_examen)
        self.btn_del_ex = QPushButton("🗑️"); self.btn_del_ex.clicked.connect(self.admin_borrar_examen)
        for b in [self.btn_add_ex, self.btn_edit_ex, self.btn_del_ex]:
            b.setFixedSize(100, 50) 
        lay_btn_ex.addWidget(self.btn_add_ex); lay_btn_ex.addWidget(self.btn_edit_ex); lay_btn_ex.addWidget(self.btn_del_ex)
        lay_btn_ex.addStretch()
        col_ex.addLayout(lay_btn_ex)
        lay_admin.addLayout(col_ex)

        self.tabs.addTab(self.tab_admin, "⚙️ Administrar Catálogo")
        layout_principal.addWidget(self.tabs)

        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()

    def obtener_texto_dialogo_oscuro(self, titulo, etiqueta, texto_previo=""):
        app = QApplication.instance()
        manejador = getattr(app, "manejador_voz", None)
        
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

        if manejador:
            manejador.desbloquear_voz()

        return texto, ok

    def ajustar_emergente_parent(self, box):
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_tabla = "#424549" if tema.modo_actual == "oscuro" else tema.BG_INPUT

        # 1. Cabecera superior adaptada
        border_head = "#4f545c" if tema.modo_actual == "oscuro" else "#a3e4d7"
        bg_head = tema.BG_TARJETA if tema.modo_actual == "oscuro" else "#e8f8f5"
        self.frame_paciente.setStyleSheet(f"background-color: {bg_head}; border-radius: 10px; border: 1px solid {border_head};")
        self.lbl_paciente.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")
        self.lbl_cedula.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")
        self.lbl_seguro.setStyleSheet(f"color: {color_txt}; font-size: 15px; border: none; background: transparent;")

        # 2. Re-estilizar Pestañas
        self.tab_generar.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.tab_admin.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {tema.BORDE_SUAVE}; background-color: {color_fondo_paginas}; }}
            QTabBar::tab {{
                background-color: {color_fondo_tabla}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE};
                padding: 10px 20px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; }}
        """)

        # 3. Inputs y Buscadores
        self.in_buscador.setStyleSheet(f"background-color: {tema.BG_INPUT}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 6px; font-size: 14px;")

        # 4. Árboles, Tablas y Listas Administrables
        self.arbol_busqueda.setStyleSheet(f"""
            QTreeWidget {{ background-color: {color_fondo_tabla}; color: {color_txt}; border: 1px solid {tema.BORDE_SUAVE}; border-radius: 6px; padding: 5px; font-size: 14px; }}
            QTreeView::item {{ color: {color_txt}; }}
            QTreeView::item:hover {{ background-color: {tema.MENTA_FOCUS}; }}
            QTreeView::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; }}
        """)
        
        self.tabla_orden.setStyleSheet(f"""
            QTableWidget {{ background-color: {color_fondo_tabla}; color: {color_txt}; gridline-color: {tema.COLOR_DIVISION_TABLA}; border: 1px solid {tema.BORDE_SUAVE}; font-size: 13px; }}
            QHeaderView::section {{ background-color: #93F6E3; color: #1C1C1C; font-weight: bold; padding: 6px; border: 1px solid {tema.BORDE_SUAVE}; }}
        """)

        for lista in [self.lista_categorias, self.lista_examenes_cat]:
            lista.setStyleSheet(f"""
                QListWidget {{ 
                    background-color: {color_fondo_tabla}; 
                    color: {color_txt}; 
                    border: 1px solid {tema.BORDE_SUAVE}; 
                    border-radius: 6px; 
                    padding: 5px; 
                    font-size: 15px; 
                }}
                QListWidget::item {{ color: {color_txt}; }}
                QListWidget::item:hover {{ background-color: {tema.MENTA_FOCUS}; color: {color_txt}; }}
                QListWidget::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; }}
            """)

        # 5. Etiquetas informativas
        for lbl in [self.lbl_tit_buscar_ex, self.lbl_tit_en_orden, self.lbl_tit_cats_ex, self.lbl_tit_exs_cat]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 13px; background: transparent;")

        # 6. Forzar Hover del Botón de Órdenes Verde Esmeralda
        bg_green_hover = "#117a65" if tema.modo_actual == "oscuro" else "#148f77"
        self.btn_generar_doc.setStyleSheet(f"""
            QPushButton {{ background-color: #16a085; color: white; font-weight: bold; border-radius: 6px; font-size: 14px; border: none; }}
            QPushButton:hover {{ background-color: {bg_green_hover}; border: 1px solid {tema.MENTA_MEDICA}; }}
        """)

        # 7. Botones de comandos de catálogo
        for btn in [self.btn_add_cat, self.btn_edit_cat, self.btn_add_ex, self.btn_edit_ex]:
            btn.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_del_cat.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_del_ex.setStyleSheet(tema.ESTILO_BTN_PELIGRO)

        self.actualizar_estilo_celdas_internas()

    def actualizar_estilo_celdas_internas(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        for row in range(self.tabla_orden.rowCount()):
            item_ex = self.tabla_orden.item(row, 0)
            if item_ex:
                item_ex.setForeground(QColor(color_txt))
            
            in_obs = self.tabla_orden.cellWidget(row, 1)
            if in_obs:
                in_obs.setStyleSheet(f"""
                    QTextEdit {{
                        border: {border_entry}; 
                        background-color: {color_fondo_entry}; 
                        color: {color_txt}; 
                        font-size: 14px; 
                        padding: 4px;
                        border-radius: 4px;
                    }}
                    QTextEdit:focus {{
                        border: 1px solid {tema.MENTA_MEDICA};
                        background-color: {color_fondo_entry};
                        color: {color_txt}; 
                    }}
                """)
            
            btn_del = self.tabla_orden.cellWidget(row, 2)
            if btn_del:
                btn_del.setStyleSheet(f"""
                    QPushButton {{ background-color: transparent; border: none; font-size: 15px; }}
                    QPushButton:hover {{ background-color: {tema.ROJO_PELIGRO}; border-radius: 4px; }}
                """)

    # --- LÓGICA DE ADMINISTRACIÓN (CATÁLOGO EXÁMENES) ---
    def actualizar_todo_el_catalogo(self):
        db = SessionLocal()
        self.lista_categorias.clear()
        self.arbol_busqueda.clear()
        
        categorias = db.query(CategoriaExamen).order_by(CategoriaExamen.nombre).all()
        color_folder = QColor("#93F6E3") if tema.modo_actual == "oscuro" else QColor("#2c3e50")
        color_letras = QColor("#FFFFFF") if tema.modo_actual == "oscuro" else QColor(tema.TEXTO_MAIN)

        for c in categorias: 
            item_c = QListWidgetItem(c.nombre)
            item_c.setForeground(color_letras)
            self.lista_categorias.addItem(item_c)
            
            cat_item = QTreeWidgetItem(self.arbol_busqueda, [f"📁 {c.nombre}"])
            cat_item.setData(0, Qt.UserRole, "CATEGORIA")
            cat_item.setForeground(0, QBrush(color_folder))
            font = cat_item.font(0); font.setBold(True); cat_item.setFont(0, font)
            
            for ex in sorted(c.examenes, key=lambda x: x.nombre):
                ex_item = QTreeWidgetItem(cat_item, [f"🔬 {ex.nombre}"])
                ex_item.setData(0, Qt.UserRole, "EXAMEN")
                ex_item.setData(0, Qt.UserRole + 1, ex.nombre)
                ex_item.setForeground(0, QBrush(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN)))
        db.close()

    def cargar_examenes_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        db = SessionLocal()
        cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
        self.lista_examenes_cat.clear()
        
        color_letras = QColor("#FFFFFF") if tema.modo_actual == "oscuro" else QColor(tema.TEXTO_MAIN)
        
        if cat:
            for ex in cat.examenes: 
                item_ex = QListWidgetItem(ex.nombre)
                item_ex.setForeground(color_letras) 
                self.lista_examenes_cat.addItem(item_ex)
        db.close()

    def restaurar_categoria(self, nombre_cat):
        items = self.lista_categorias.findItems(nombre_cat, Qt.MatchExactly)
        if items: self.lista_categorias.setCurrentItem(items[0])

    def admin_agregar_categoria(self):
        texto, ok = self.obtener_texto_dialogo_oscuro("Nueva Categoría", "Nombre de la categoría:")
        if ok and texto.strip():
            db = SessionLocal()
            db.add(CategoriaExamen(nombre=texto.strip()))
            db.commit(); db.close(); self.actualizar_todo_el_catalogo()

    def admin_editar_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        texto, ok = self.obtener_texto_dialogo_oscuro("Editar", "Nuevo nombre:", item.text())
        if ok and texto.strip():
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
            if cat: cat.nombre = texto.strip(); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()

    def admin_borrar_categoria(self):
        item = self.lista_categorias.currentItem()
        if not item: return
        box = QMessageBox(QMessageBox.Question, "Confirmar", f"¿Borrar '{item.text()}' y todos sus exámenes?", QMessageBox.Yes | QMessageBox.No, self)
        self.ajustar_emergente_parent(box)
        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == item.text()).first()
            if cat: db.delete(cat); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()

    def admin_agregar_examen(self):
        item_cat = self.lista_categorias.currentItem()
        if not item_cat: 
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione una categoría primero.", QMessageBox.Ok, self)
            self.ajustar_emergente_parent(box); box.exec(); return
        cat_nombre = item_cat.text()
        texto, ok = self.obtener_texto_dialogo_oscuro("Nuevo Examen", f"Examen para {cat_nombre}:")
        if ok and texto.strip():
            db = SessionLocal()
            cat = db.query(CategoriaExamen).filter(CategoriaExamen.nombre == cat_nombre).first()
            db.add(ExamenCatalogo(nombre=texto.strip(), categoria_id=cat.id if hasattr(cat, 'categoria_id') else cat.id))
            db.commit(); db.close(); self.actualizar_todo_el_catalogo()
            self.restaurar_categoria(cat_nombre)

    def admin_editar_examen(self):
        item_ex = self.lista_examenes_cat.currentItem()
        item_cat = self.lista_categorias.currentItem()
        if not item_ex or not item_cat: return
        cat_nombre = item_cat.text()
        texto, ok = self.obtener_texto_dialogo_oscuro("Editar Examen", "Nuevo nombre:", item_ex.text())
        if ok and texto.strip():
            db = SessionLocal()
            ex = db.query(ExamenCatalogo).filter(ExamenCatalogo.nombre == item_ex.text()).first()
            if ex: ex.nombre = texto.strip(); db.commit()
            db.close(); self.actualizar_todo_el_catalogo()
            self.restaurar_categoria(cat_nombre)

    def admin_borrar_examen(self):
        item_ex = self.lista_examenes_cat.currentItem()
        item_cat = self.lista_categorias.currentItem()
        if not item_ex or not item_cat: return
        cat_nombre = item_cat.text()
        db = SessionLocal()
        ex = db.query(ExamenCatalogo).filter(ExamenCatalogo.nombre == item_ex.text()).first()
        if ex: db.delete(ex); db.commit()
        db.close(); self.actualizar_todo_el_catalogo()
        self.restaurar_categoria(cat_nombre)

    def filtrar_catalogo(self, texto):
        texto = texto.lower()
        for i in range(self.arbol_busqueda.topLevelItemCount()):
            cat_item = self.arbol_busqueda.topLevelItem(i)
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

    def agregar_a_orden(self, item, column):
        if item.data(0, Qt.UserRole) != "EXAMEN":
            item.setExpanded(not item.isExpanded())
            return
            
        nombre_examen = item.data(0, Qt.UserRole + 1)
        row = self.tabla_orden.rowCount()
        self.tabla_orden.insertRow(row)
        
        item_nombre = QTableWidgetItem(nombre_examen)
        item_nombre.setForeground(QColor("#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN))
        self.tabla_orden.setItem(row, 0, item_nombre)
        
        in_obs = QTextEdit()
        in_obs.setPlaceholderText("Observación...")
        
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"
        
        in_obs.setStyleSheet(f"""
            QTextEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 4px;
                border-radius: 4px;
            }}
            QTextEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry};
                color: {color_txt}; 
            }}
        """)
        in_obs.setFixedHeight(40)
        
        def adaptar_altura():
            doc_height = int(in_obs.document().size().height())
            in_obs.setFixedHeight(max(40, doc_height + 10))
            self.tabla_orden.resizeRowsToContents()
            
        in_obs.textChanged.connect(adaptar_altura)
        self.tabla_orden.setCellWidget(row, 1, in_obs)
        
        btn_del = QPushButton("❌")
        btn_del.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; font-size: 14px; }} QPushButton:hover {{ background-color: {tema.ROJO_PELIGRO}; border-radius: 4px; }}")
        btn_del.clicked.connect(lambda: self.tabla_orden.removeRow(self.tabla_orden.indexAt(btn_del.pos()).row()))
        self.tabla_orden.setCellWidget(row, 2, btn_del)

    def cargar_datos_paciente(self, paciente_id):
        self.paciente_id = paciente_id
        db = SessionLocal()
        p = db.query(Paciente).get(paciente_id)
        if p:
            self.lbl_paciente.setText(f"<b>PACIENTE:</b> {p.nombre_completo}")
            self.lbl_cedula.setText(f"<b>CÉDULA:</b> {p.cedula}")
            seg = p.seguro if p.seguro and p.seguro.strip().lower() != "no aplica" else "Ninguno"
            self.lbl_seguro.setText(f"<b>SEGURO:</b> {seg.upper()}")
            self.tabla_orden.setRowCount(0); self.actualizar_todo_el_catalogo()
        db.close()

    def procesar_documento(self, formato="pdf"):
        if not self.paciente_id or self.tabla_orden.rowCount() == 0: return
        lista = []
        for i in range(self.tabla_orden.rowCount()):
            lista.append((self.tabla_orden.item(i, 0).text(), self.tabla_orden.cellWidget(i, 1).toPlainText()))
        
        db = SessionLocal()
        p = db.query(Paciente).get(self.paciente_id)
        doctor = db.query(PerfilDoctor).first()
        
        ext = ".docx" if formato.lower() == "docx" else ".pdf"
        tipo_reg = "DOCX" if formato.lower() == "docx" else "PDF"

        ruta_generada = MotorImpresion.generar_pdf_ordenes(doctor, p, lista, formato=formato)
        nombre_limpio = re.sub(r'[^\w\s-]', '', p.nombre_completo).strip().replace(' ', '_')
        ruta_dest = os.path.join(self.ruta_base, f"{nombre_limpio}_{p.cedula}")
        os.makedirs(ruta_dest, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_file = f"ORDENEXAMEN_{nombre_limpio}_{timestamp}{ext}"
        ruta_final = os.path.join(ruta_dest, nombre_file)
        shutil.move(ruta_generada, ruta_final)
        
        db.add(ArchivoPaciente(paciente_id=self.paciente_id, nombre_archivo=nombre_file, ruta_archivo=ruta_final, tipo_archivo=tipo_reg))
        db.commit(); db.close()
        
        MotorImpresion.abrir_documento_generado(ruta_final)
        self.volver_historial.emit()