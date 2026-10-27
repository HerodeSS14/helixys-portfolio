import os
from datetime import datetime, timedelta, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QMessageBox, QDateEdit, QCheckBox, QDoubleSpinBox, QDialog,
    QFrame, QGroupBox, QFileDialog, QSplitter, QComboBox, QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QKeyEvent

from database import SessionLocal
from models import Paciente, Rendimiento
from estilos import tema

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# =============================================================================
# DELEGADO DE PINTADO PARA FORZAR COLORES DE FILA EN QTREEWIDGET (VERDE/AMARILLO)
# =============================================================================
class DelegadoColorArbol(QStyledItemDelegate):
    """ Delegado personalizado para asegurar que el fondo de las filas se pinte con
        su color correspondiente (Verde/Amarillo) superando el estilo QSS de Qt. """
    def paint(self, painter, option, index):
        brush_fondo = index.data(Qt.BackgroundRole)
        # Si tiene color asignado y la fila NO está seleccionada por el usuario
        if brush_fondo and not (option.state & QStyle.State_Selected):
            painter.save()
            painter.fillRect(option.rect, brush_fondo)
            painter.restore()
        super().paint(painter, option, index)


# =============================================================================
# WIDGET PERSONALIZADO PARA ENTRADA ESTILO ATM (DE DERECHA A IZQUIERDA)
# =============================================================================
class SpinBoxMontoATM(QDoubleSpinBox):
    """
    QDoubleSpinBox personalizado que permite la entrada de números
    desplazándose de derecha a izquierda (estilo punto de venta / centavos).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100000000)
        self.setDecimals(2)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setGroupSeparatorShown(True)
        self._buffer_digitos = ""

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
        if self.value() > 0:
            self._buffer_digitos = f"{int(round(self.value() * 100))}"
        else:
            self._buffer_digitos = ""

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._buffer_digitos = ""

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        if Qt.Key_0 <= key <= Qt.Key_9:
            digit = chr(key)
            if self._buffer_digitos == "" and digit == "0":
                return
            
            if len(self._buffer_digitos) < 10:
                self._buffer_digitos += digit
                val = int(self._buffer_digitos) / 100.0
                self.setValue(val)
            return

        elif key == Qt.Key_Backspace:
            if len(self._buffer_digitos) > 0:
                self._buffer_digitos = self._buffer_digitos[:-1]
                val = int(self._buffer_digitos) / 100.0 if self._buffer_digitos else 0.0
                self.setValue(val)
            else:
                self.setValue(0.0)
            return

        super().keyPressEvent(event)


# =============================================================================
# DIÁLOGO DE FORMULARIO DE RENDIMIENTO
# =============================================================================
class DialogoFormularioRendimiento(QDialog):
    """ Ventana Modal Emergente para Buscar Paciente y Registrar/Editar Operación """
    def __init__(self, parent=None, rendimiento_id=None):
        super().__init__(parent)
        self.rendimiento_id = rendimiento_id
        self.paciente_seleccionado_id = None
        
        self.setWindowTitle("Editar Operación / Honorario" if rendimiento_id else "Añadir Nueva Operación / Honorario")
        self.setMinimumSize(980, 720)
        self.init_ui()
        self.aplicar_estilos()
        self.cargar_lista_pacientes()
        
        if self.rendimiento_id:
            self.cargar_datos_existentes()

    def init_ui(self):
        lay_main = QHBoxLayout(self)
        lay_main.setContentsMargins(15, 15, 15, 15)
        lay_main.setSpacing(15)

        splitter = QSplitter(Qt.Horizontal)

        # 1. Panel Izquierdo: Buscador de Paciente
        w_paciente = QWidget()
        lay_pac = QVBoxLayout(w_paciente)
        lay_pac.setContentsMargins(0, 0, 0, 0)

        self.lbl_titulo_pac = QLabel("🔍 Buscar Paciente")
        self.lbl_titulo_pac.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        lay_pac.addWidget(self.lbl_titulo_pac)

        self.in_buscar_paciente = QLineEdit()
        self.in_buscar_paciente.setPlaceholderText("Nombre o Cédula...")
        self.in_buscar_paciente.setMinimumHeight(38)
        self.in_buscar_paciente.textChanged.connect(self.cargar_lista_pacientes)
        lay_pac.addWidget(self.in_buscar_paciente)

        self.tabla_pacientes = QTableWidget(0, 2)
        self.tabla_pacientes.setHorizontalHeaderLabels(["Cédula", "Nombre"])
        self.tabla_pacientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_pacientes.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_pacientes.cellClicked.connect(self.seleccionar_paciente)
        lay_pac.addWidget(self.tabla_pacientes)

        splitter.addWidget(w_paciente)

        # 2. Panel Derecho: Formulario Operación y Honorarios
        w_form = QWidget()
        lay_form = QVBoxLayout(w_form)
        lay_form.setContentsMargins(5, 0, 5, 0)

        self.lbl_titulo_crud = QLabel("⚙️ Detalle de Operación / Honorario")
        self.lbl_titulo_crud.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        lay_form.addWidget(self.lbl_titulo_crud)

        # Tarjeta del paciente seleccionado
        self.card_paciente_info = QFrame()
        self.card_paciente_info.setFrameShape(QFrame.StyledPanel)
        lay_card = QVBoxLayout(self.card_paciente_info)
        self.lbl_paciente_sel = QLabel("<i>Ningún paciente seleccionado</i>")
        self.lbl_paciente_sel.setStyleSheet("font-size: 13px; font-weight: bold;")
        lay_card.addWidget(self.lbl_paciente_sel)
        lay_form.addWidget(self.card_paciente_info)

        # Campos del formulario
        f_layout = QVBoxLayout()

        # Fecha, Clínica y Selección de Moneda
        h_f1 = QHBoxLayout()
        v_fop = QVBoxLayout()
        v_fop.addWidget(QLabel("<b>Fecha Operación:</b>"))
        self.in_fecha_operacion = QDateEdit()
        self.in_fecha_operacion.setCalendarPopup(True)
        self.in_fecha_operacion.setDate(QDate.currentDate())
        self.in_fecha_operacion.setMinimumHeight(35)
        v_fop.addWidget(self.in_fecha_operacion)

        v_cli = QVBoxLayout()
        v_cli.addWidget(QLabel("<b>Clínica / Centro:</b>"))
        self.in_clinica = QLineEdit()
        self.in_clinica.setPlaceholderText("Ej: Clínica San José")
        self.in_clinica.setMinimumHeight(35)
        v_cli.addWidget(self.in_clinica)

        v_mon = QVBoxLayout()
        v_mon.addWidget(QLabel("<b>Moneda:</b>"))
        self.cmb_moneda = QComboBox()
        self.cmb_moneda.addItems(["USD ($)", "VES (Bs.)"])
        self.cmb_moneda.setMinimumHeight(35)
        self.cmb_moneda.currentIndexChanged.connect(self.actualizar_simbolo_moneda)
        v_mon.addWidget(self.cmb_moneda)

        h_f1.addLayout(v_fop, 30)
        h_f1.addLayout(v_cli, 45)
        h_f1.addLayout(v_mon, 25)
        f_layout.addLayout(h_f1)

        # Procedimiento
        f_layout.addWidget(QLabel("<b>Procedimiento Realizado:</b>"))
        self.in_procedimiento = QLineEdit()
        self.in_procedimiento.setPlaceholderText("Ej: Histerectomía Laparoscópica")
        self.in_procedimiento.setMinimumHeight(35)
        f_layout.addWidget(self.in_procedimiento)

        # Modalidad de Pago
        grp_pago = QGroupBox("Modalidad de Pago")
        lay_grp_pago = QVBoxLayout(grp_pago)

        self.chk_pago_directo = QCheckBox("Pago Directo / Particular")
        self.chk_pago_directo.setChecked(True)
        self.chk_pago_directo.toggled.connect(self.toggle_modalidad_pago)
        lay_grp_pago.addWidget(self.chk_pago_directo)

        h_pago_det = QHBoxLayout()
        v_pdirecto = QVBoxLayout()
        v_pdirecto.addWidget(QLabel("Monto Pago Directo:"))
        self.spn_pago_directo = SpinBoxMontoATM()
        self.spn_pago_directo.setPrefix("$ ")
        self.spn_pago_directo.setMinimumHeight(35)
        v_pdirecto.addWidget(self.spn_pago_directo)

        v_seguro = QVBoxLayout()
        v_seguro.addWidget(QLabel("Nombre del Seguro:"))
        self.in_seguro = QLineEdit()
        self.in_seguro.setPlaceholderText("Ej: Mercantil Seguros")
        self.in_seguro.setMinimumHeight(35)
        self.in_seguro.setEnabled(False)
        v_seguro.addWidget(self.in_seguro)

        h_pago_det.addLayout(v_pdirecto, 50)
        h_pago_det.addLayout(v_seguro, 50)
        lay_grp_pago.addLayout(h_pago_det)
        f_layout.addWidget(grp_pago)

        # EQUIPO DE CIRUJANOS DETALLADO CON SPINBOXES ESTILO ATM
        grp_cirujanos = QGroupBox("Equipo Médico y Honorarios por Cirujano")
        lay_grp_cir = QVBoxLayout(grp_cirujanos)

        # 1. Cirujano Principal
        h_cp = QHBoxLayout()
        self.in_cp_nom = QLineEdit(); self.in_cp_nom.setPlaceholderText("Nombre Cirujano Principal")
        self.in_cp_ced = QLineEdit(); self.in_cp_ced.setPlaceholderText("Cédula Principal")
        self.spn_cp_monto = SpinBoxMontoATM(); self.spn_cp_monto.setPrefix("$ ")
        h_cp.addWidget(QLabel("<b>Principal:</b>"))
        h_cp.addWidget(self.in_cp_nom, 40)
        h_cp.addWidget(self.in_cp_ced, 30)
        h_cp.addWidget(self.spn_cp_monto, 30)
        lay_grp_cir.addLayout(h_cp)

        # 2. Cirujano Auxiliar 1
        h_ca1 = QHBoxLayout()
        self.in_ca1_nom = QLineEdit(); self.in_ca1_nom.setPlaceholderText("Nombre Auxiliar 1")
        self.in_ca1_ced = QLineEdit(); self.in_ca1_ced.setPlaceholderText("Cédula Auxiliar 1")
        self.spn_ca1_monto = SpinBoxMontoATM(); self.spn_ca1_monto.setPrefix("$ ")
        h_ca1.addWidget(QLabel("Auxiliar 1:"))
        h_ca1.addWidget(self.in_ca1_nom, 40)
        h_ca1.addWidget(self.in_ca1_ced, 30)
        h_ca1.addWidget(self.spn_ca1_monto, 30)
        lay_grp_cir.addLayout(h_ca1)

        # 3. Cirujano Auxiliar 2
        h_ca2 = QHBoxLayout()
        self.in_ca2_nom = QLineEdit(); self.in_ca2_nom.setPlaceholderText("Nombre Auxiliar 2")
        self.in_ca2_ced = QLineEdit(); self.in_ca2_ced.setPlaceholderText("Cédula Auxiliar 2")
        self.spn_ca2_monto = SpinBoxMontoATM(); self.spn_ca2_monto.setPrefix("$ ")
        h_ca2.addWidget(QLabel("Auxiliar 2:"))
        h_ca2.addWidget(self.in_ca2_nom, 40)
        h_ca2.addWidget(self.in_ca2_ced, 30)
        h_ca2.addWidget(self.spn_ca2_monto, 30)
        lay_grp_cir.addLayout(h_ca2)

        f_layout.addWidget(grp_cirujanos)

        # Monto Total / Cancelado / Estado Pagado
        h_est = QHBoxLayout()

        v_cuanto = QVBoxLayout()
        v_cuanto.addWidget(QLabel("<b>Monto Total Honorarios:</b>"))
        self.spn_cuanto = SpinBoxMontoATM()
        self.spn_cuanto.setPrefix("$ ")
        self.spn_cuanto.setMinimumHeight(35)
        v_cuanto.addWidget(self.spn_cuanto)

        v_canc = QVBoxLayout()
        self.chk_cancelado = QCheckBox("Operación Cancelada / Pagada")
        self.chk_cancelado.setStyleSheet("font-weight: bold; color: #2ecc71;")
        self.chk_cancelado.toggled.connect(self.toggle_cancelado)
        v_canc.addWidget(self.chk_cancelado)
        self.in_fecha_cancelacion = QDateEdit()
        self.in_fecha_cancelacion.setCalendarPopup(True)
        self.in_fecha_cancelacion.setDate(QDate.currentDate())
        self.in_fecha_cancelacion.setMinimumHeight(35)
        self.in_fecha_cancelacion.setEnabled(False)
        v_canc.addWidget(self.in_fecha_cancelacion)

        h_est.addLayout(v_cuanto, 50)
        h_est.addLayout(v_canc, 50)
        f_layout.addLayout(h_est)

        lay_form.addLayout(f_layout)

        # Botones Emergentes
        h_btns = QHBoxLayout()
        self.btn_guardar = QPushButton("💾 GUARDAR")
        self.btn_guardar.setMinimumHeight(40)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self.guardar)

        self.btn_cancelar = QPushButton("❌ CANCELAR")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        h_btns.addWidget(self.btn_guardar)
        h_btns.addWidget(self.btn_cancelar)
        lay_form.addLayout(h_btns)

        splitter.addWidget(w_form)
        splitter.setSizes([280, 700])
        lay_main.addWidget(splitter)

    def actualizar_simbolo_moneda(self):
        simbolo = "Bs. " if self.cmb_moneda.currentText().startswith("VES") else "$ "
        self.spn_pago_directo.setPrefix(simbolo)
        self.spn_cp_monto.setPrefix(simbolo)
        self.spn_ca1_monto.setPrefix(simbolo)
        self.spn_ca2_monto.setPrefix(simbolo)
        self.spn_cuanto.setPrefix(simbolo)

    def aplicar_estilos(self):
        style_inputs = tema.ESTILO_ENTRY_MODERNO
        for widget in [self.in_buscar_paciente, self.in_clinica, self.in_procedimiento, self.in_seguro,
                       self.in_cp_nom, self.in_cp_ced, self.in_ca1_nom, self.in_ca1_ced, 
                       self.in_ca2_nom, self.in_ca2_ced, self.in_fecha_operacion, self.in_fecha_cancelacion,
                       self.spn_pago_directo, self.spn_cp_monto, self.spn_ca1_monto, self.spn_ca2_monto,
                       self.spn_cuanto, self.cmb_moneda]:
            widget.setStyleSheet(style_inputs)

        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_cancelar.setStyleSheet(tema.ESTILO_BTN_PELIGRO)

    def toggle_modalidad_pago(self, checked):
        self.spn_pago_directo.setEnabled(checked)
        self.in_seguro.setEnabled(not checked)
        if checked: self.in_seguro.clear()
        else: self.spn_pago_directo.setValue(0.0)

    def toggle_cancelado(self, checked):
        self.in_fecha_cancelacion.setEnabled(checked)

    def cargar_lista_pacientes(self):
        db = SessionLocal()
        try:
            filtro = self.in_buscar_paciente.text().strip()
            query = db.query(Paciente)
            if filtro:
                query = query.filter((Paciente.nombre_completo.ilike(f"%{filtro}%")) | (Paciente.cedula.ilike(f"%{filtro}%")))
            pacientes = query.all()

            self.tabla_pacientes.setRowCount(len(pacientes))
            for i, p in enumerate(pacientes):
                it_ced = QTableWidgetItem(p.cedula)
                it_nom = QTableWidgetItem(p.nombre_completo)
                it_ced.setData(Qt.UserRole, p.id)
                self.tabla_pacientes.setItem(i, 0, it_ced)
                self.tabla_pacientes.setItem(i, 1, it_nom)
        finally:
            db.close()

    def seleccionar_paciente(self, row, col):
        it_ced = self.tabla_pacientes.item(row, 0)
        if not it_ced: return
        paciente_id = it_ced.data(Qt.UserRole)
        
        db = SessionLocal()
        try:
            p = db.query(Paciente).get(paciente_id)
            if p:
                self.paciente_seleccionado_id = p.id
                self.lbl_paciente_sel.setText(f"👤 <b>{p.nombre_completo}</b> | C.I: {p.cedula}")
                if not self.in_seguro.text() and p.seguro:
                    self.in_seguro.setText(p.seguro)
        finally:
            db.close()

    def cargar_datos_existentes(self):
        db = SessionLocal()
        try:
            r = db.query(Rendimiento).get(self.rendimiento_id)
            if r:
                self.paciente_seleccionado_id = r.paciente_id
                self.lbl_paciente_sel.setText(f"👤 <b>{r.paciente.nombre_completo}</b> | C.I: {r.paciente.cedula}")
                if r.fecha_operacion:
                    self.in_fecha_operacion.setDate(QDate(r.fecha_operacion.year, r.fecha_operacion.month, r.fecha_operacion.day))

                self.in_clinica.setText(r.clinica or "")
                self.in_procedimiento.setText(r.procedimiento or "")

                if getattr(r, 'moneda', None) == "VES":
                    self.cmb_moneda.setCurrentIndex(1)
                else:
                    self.cmb_moneda.setCurrentIndex(0)
                self.actualizar_simbolo_moneda()

                if r.pago_directo and r.pago_directo > 0:
                    self.chk_pago_directo.setChecked(True)
                    self.spn_pago_directo.setValue(r.pago_directo)
                else:
                    self.chk_pago_directo.setChecked(False)
                    self.in_seguro.setText(r.seguro or "")

                # Cirujano Principal
                self.in_cp_nom.setText(getattr(r, 'cirujano_p_nombre', r.cirujano_p or ""))
                self.in_cp_ced.setText(getattr(r, 'cirujano_p_cedula', "") or "")
                self.spn_cp_monto.setValue(getattr(r, 'cirujano_p_monto', 0.0) or 0.0)

                # Cirujano Auxiliar 1
                self.in_ca1_nom.setText(getattr(r, 'cirujano_aux1_nombre', r.cirujano_aux1 or ""))
                self.in_ca1_ced.setText(getattr(r, 'cirujano_aux1_cedula', "") or "")
                self.spn_ca1_monto.setValue(getattr(r, 'cirujano_aux1_monto', 0.0) or 0.0)

                # Cirujano Auxiliar 2
                self.in_ca2_nom.setText(getattr(r, 'cirujano_aux2_nombre', r.cirujano_aux2 or ""))
                self.in_ca2_ced.setText(getattr(r, 'cirujano_aux2_cedula', "") or "")
                self.spn_ca2_monto.setValue(getattr(r, 'cirujano_aux2_monto', 0.0) or 0.0)

                self.spn_cuanto.setValue(r.cuanto or 0.0)
                esta_cancelado = r.cancelado or r.pagado
                self.chk_cancelado.setChecked(esta_cancelado)
                if esta_cancelado and r.fecha_cancelacion:
                    self.in_fecha_cancelacion.setDate(QDate(r.fecha_cancelacion.year, r.fecha_cancelacion.month, r.fecha_cancelacion.day))
        finally:
            db.close()

    def guardar(self):
        if not self.paciente_seleccionado_id:
            QMessageBox.warning(self, "Aviso", "Seleccione un paciente de la lista.", QMessageBox.Ok)
            return

        procedimiento = self.in_procedimiento.text().strip()
        if not procedimiento:
            QMessageBox.warning(self, "Aviso", "Escriba el nombre del procedimiento.", QMessageBox.Ok)
            return

        db = SessionLocal()
        try:
            if self.rendimiento_id:
                rend = db.query(Rendimiento).get(self.rendimiento_id)
            else:
                rend = Rendimiento()
                db.add(rend)

            rend.paciente_id = self.paciente_seleccionado_id
            qdate_op = self.in_fecha_operacion.date()
            rend.fecha_operacion = datetime(qdate_op.year(), qdate_op.month(), qdate_op.day())
            rend.procedimiento = procedimiento
            rend.clinica = self.in_clinica.text().strip()
            rend.moneda = "VES" if self.cmb_moneda.currentIndex() == 1 else "USD"

            if self.chk_pago_directo.isChecked():
                rend.pago_directo = self.spn_pago_directo.value()
                rend.seguro = None
            else:
                rend.pago_directo = 0.0
                rend.seguro = self.in_seguro.text().strip()

            # Guardar datos estructurados de cirujanos
            rend.cirujano_p_nombre = self.in_cp_nom.text().strip()
            rend.cirujano_p_cedula = self.in_cp_ced.text().strip()
            rend.cirujano_p_monto = self.spn_cp_monto.value()

            rend.cirujano_aux1_nombre = self.in_ca1_nom.text().strip()
            rend.cirujano_aux1_cedula = self.in_ca1_ced.text().strip()
            rend.cirujano_aux1_monto = self.spn_ca1_monto.value()

            rend.cirujano_aux2_nombre = self.in_ca2_nom.text().strip()
            rend.cirujano_aux2_cedula = self.in_ca2_ced.text().strip()
            rend.cirujano_aux2_monto = self.spn_ca2_monto.value()

            # Guardar campos retrocompatibles
            rend.cirujano_p = rend.cirujano_p_nombre
            rend.cirujano_aux1 = rend.cirujano_aux1_nombre
            rend.cirujano_aux2 = rend.cirujano_aux2_nombre

            rend.cuanto = self.spn_cuanto.value()

            # Cancelado = Pagado
            esta_cancelado = self.chk_cancelado.isChecked()
            rend.cancelado = esta_cancelado
            rend.pagado = esta_cancelado

            if esta_cancelado:
                qdate_canc = self.in_fecha_cancelacion.date()
                fecha_c = datetime(qdate_canc.year(), qdate_canc.month(), qdate_canc.day())
                rend.fecha_cancelacion = fecha_c
                rend.fecha_pago = fecha_c
            else:
                rend.fecha_cancelacion = None
                rend.fecha_pago = None

            db.commit()
            QMessageBox.information(self, "Éxito", "Operación guardada correctamente.", QMessageBox.Ok)
            self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}", QMessageBox.Ok)
        finally:
            db.close()


# =============================================================================
# PANTALLA PRINCIPAL DE RENDIMIENTOS
# =============================================================================
class PantallaRendimientos(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        # ASIGNAR DELEGADO PERSONALIZADO PARA PERMITIR COLORES EN LAS FILAS DE AMBOS ÁRBOLES
        self.arbol_recientes.setItemDelegate(DelegadoColorArbol(self.arbol_recientes))
        self.arbol_historial.setItemDelegate(DelegadoColorArbol(self.arbol_historial))

        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()
        self.cargar_operaciones_recientes()
        self.cargar_historial_rendimientos()

    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        layout_principal.setSpacing(15)

        self.tabs = QTabWidget()

        # ------------------- TAB 1: OPERACIONES ACTIVAS / RECIENTES -------------------
        self.tab_registro = QWidget()
        lay_tab_reg = QVBoxLayout(self.tab_registro)
        lay_tab_reg.setContentsMargins(10, 10, 10, 10)
        lay_tab_reg.setSpacing(10)

        self.lbl_titulo_tree = QLabel("📋 Operaciones Activas / Recientes")
        self.lbl_titulo_tree.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        lay_tab_reg.addWidget(self.lbl_titulo_tree)

        self.arbol_recientes = QTreeWidget()
        self.arbol_recientes.setHeaderLabels([
            "Fecha Op.", "Fecha Canc./Pago", "Paciente", "Procedimiento", "Clínica", 
            "Cirujano Principal", "Cirujano Aux. 1", "Cirujano Aux. 2", "Monto Honorarios", "Estado"
        ])
        lay_tab_reg.addWidget(self.arbol_recientes)

        # Barra de Botones Inferiores
        h_acciones = QHBoxLayout()

        self.btn_anadir = QPushButton("➕ Añadir Operación")
        self.btn_anadir.setMinimumHeight(40)
        self.btn_anadir.setCursor(Qt.PointingHandCursor)
        self.btn_anadir.clicked.connect(self.abrir_dialogo_anadir)

        self.btn_editar = QPushButton("✏️ Editar Operación")
        self.btn_editar.setMinimumHeight(40)
        self.btn_editar.setCursor(Qt.PointingHandCursor)
        self.btn_editar.clicked.connect(self.abrir_dialogo_editar)

        self.btn_eliminar_pago = QPushButton("🗑️ Eliminar de Activas")
        self.btn_eliminar_pago.setMinimumHeight(40)
        self.btn_eliminar_pago.setCursor(Qt.PointingHandCursor)
        self.btn_eliminar_pago.clicked.connect(self.eliminar_pago_seleccionado)

        h_acciones.addWidget(self.btn_anadir)
        h_acciones.addWidget(self.btn_editar)
        h_acciones.addWidget(self.btn_eliminar_pago)

        lay_tab_reg.addLayout(h_acciones)
        self.tabs.addTab(self.tab_registro, "📝 Operaciones Activas")

        # ------------------- TAB 2: HISTORIAL DE RENDIMIENTOS -------------------
        self.tab_historial = QWidget()
        lay_tab_hist = QVBoxLayout(self.tab_historial)
        lay_tab_hist.setContentsMargins(15, 15, 15, 15)
        lay_tab_hist.setSpacing(15)

        h_top_hist = QHBoxLayout()
        self.lbl_hist_titulo = QLabel("📊 Historial Anual y Mensual de Rendimientos")
        self.lbl_hist_titulo.setStyleSheet(tema.ESTILO_LABEL_TITULO)
        h_top_hist.addWidget(self.lbl_hist_titulo)

        self.btn_exportar_excel = QPushButton("📥 EXPORTAR MES A EXCEL")
        self.btn_exportar_excel.setMinimumHeight(40)
        self.btn_exportar_excel.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_excel.clicked.connect(self.exportar_mes_excel)
        h_top_hist.addWidget(self.btn_exportar_excel)

        lay_tab_hist.addLayout(h_top_hist)

        self.arbol_historial = QTreeWidget()
        self.arbol_historial.setHeaderLabels([
            "Período / Paciente", "Fecha Op.", "Fecha Canc./Pago", "Procedimiento", "Clínica", 
            "Pago Directo / Seguro", "Cirujano Principal", "Cirujano Aux. 1", "Cirujano Aux. 2", "Monto Total", "Estado"
        ])
        lay_tab_hist.addWidget(self.arbol_historial)

        self.tabs.addTab(self.tab_historial, "📊 Historial por Mes / Año")
        layout_principal.addWidget(self.tabs)

    def actualizar_diseno_dinamico(self):
        color_bg_input = tema.BG_INPUT

        self.setStyleSheet(tema.ESTILO_VENTANA)

        # FONDO TRANSPARENTE EN QTreeWidget::item PARA MOSTRAR LOS COLORES VERDE/AMARILLO
        style_tree = f"""
            QTreeWidget {{
                background-color: {color_bg_input};
                color: #000000;
                font-size: 13px;
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 6px;
                show-decoration-selected: 1;
            }}
            QHeaderView::section {{
                background-color: #93F6E3;
                color: #1C1C1C;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 8px;
                border-right: 1px solid #CBD5E1;
                border-bottom: 2px solid #CBD5E1;
                border-top: 1px solid #CBD5E1;
                border-left: 1px solid #CBD5E1;
            }}
            QTreeWidget::item {{
                background: transparent;
                min-height: 44px;
                padding: 6px 12px;
                border-bottom: 1px solid #CBD5E1;
                border-right: 1px solid #CBD5E1;
                color: #000000;
            }}
            QTreeWidget::item:selected {{
                background-color: #3498db !important;
                color: #FFFFFF !important;
            }}
        """
        for tree in [self.arbol_recientes, self.arbol_historial]:
            tree.setStyleSheet(style_tree)
            header = tree.header()
            header.setStretchLastSection(False)
            for col in range(header.count()):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.btn_anadir.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_editar.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_eliminar_pago.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_exportar_excel.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none; } QPushButton:hover { background-color: #219150; }")

    def _ajustar_columnas(self, arbol):
        for i in range(arbol.columnCount()):
            arbol.resizeColumnToContents(i)
            ancho_actual = arbol.columnWidth(i)
            arbol.setColumnWidth(i, ancho_actual + 20)

    # =========================================================================
    # ACCIONES DE BOTONES EN LA VISTA PRINCIPAL
    # =========================================================================
    def abrir_dialogo_anadir(self):
        dlg = DialogoFormularioRendimiento(self)
        if dlg.exec() == QDialog.Accepted:
            self.cargar_operaciones_recientes()
            self.cargar_historial_rendimientos()

    def abrir_dialogo_editar(self):
        item_sel = self.arbol_recientes.currentItem()
        if not item_sel:
            QMessageBox.warning(self, "Aviso", "Seleccione una operación de la lista para editar.", QMessageBox.Ok)
            return

        rend_id = item_sel.data(0, Qt.UserRole)
        if not rend_id: return

        dlg = DialogoFormularioRendimiento(self, rendimiento_id=rend_id)
        if dlg.exec() == QDialog.Accepted:
            self.cargar_operaciones_recientes()
            self.cargar_historial_rendimientos()

    def eliminar_pago_seleccionado(self):
        item_sel = self.arbol_recientes.currentItem()
        if not item_sel:
            QMessageBox.warning(self, "Aviso", "Seleccione una operación de la lista.", QMessageBox.Ok)
            return

        rend_id = item_sel.data(0, Qt.UserRole)
        if not rend_id: return

        box = QMessageBox(
            QMessageBox.Question,
            "Quitar de Operaciones Activas",
            "¿Desea quitar esta operación del listado activo?\n\n(Se conservará intacta en el historial).",
            QMessageBox.Yes | QMessageBox.No,
            self
        )
        box.setStyleSheet(tema.ESTILO_VENTANA)

        if box.exec() == QMessageBox.Yes:
            db = SessionLocal()
            try:
                rend = db.query(Rendimiento).get(rend_id)
                if rend:
                    rend.cancelado = True
                    rend.pagado = True
                    hace_2_dias = datetime.now() - timedelta(days=2)
                    rend.fecha_cancelacion = hace_2_dias
                    rend.fecha_pago = hace_2_dias
                    db.commit()
                    QMessageBox.information(self, "Actualizado", "La operación se quitó de activas y permanece guardada en el historial.", QMessageBox.Ok)
                    self.cargar_operaciones_recientes()
                    self.cargar_historial_rendimientos()
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Error al quitar de activas: {e}", QMessageBox.Ok)
            finally:
                db.close()

    def _formatear_cirujano(self, nom, ced, mnt, prefix):
        """ Formatea la visualización del cirujano mostrando nombre, cédula y honorario al lado """
        if not nom:
            return "---"
        cad = f"{nom}"
        if ced: 
            cad += f" (C.I: {ced})"
        if mnt is not None and mnt > 0: 
            cad += f" - {prefix}{mnt:,.2f}"
        else:
            cad += f" - {prefix}0.00"
        return cad

    # =========================================================================
    # CARGA DE OPERACIONES RECIENTES
    # =========================================================================
    def cargar_operaciones_recientes(self):
        self.arbol_recientes.clear()
        db = SessionLocal()
        try:
            rendimientos = db.query(Rendimiento).all()
            ahora = datetime.now()
            h_24_atras = ahora - timedelta(hours=24)

            c_verde = QColor(212, 237, 218)     # Verde claro (#D4EDDA)
            c_amarillo = QColor(255, 243, 205)  # Amarillo suave (#FFF3CD)
            c_texto_negro = QColor(0, 0, 0)

            for r in rendimientos:
                esta_cancelado = r.cancelado or r.pagado
                fecha_ref = r.fecha_cancelacion or r.fecha_pago

                if fecha_ref and type(fecha_ref) is date:
                    fecha_ref = datetime.combine(fecha_ref, datetime.min.time())

                if esta_cancelado and fecha_ref and fecha_ref < h_24_atras:
                    continue

                pac_nom = r.paciente.nombre_completo if r.paciente else "N/A"
                f_op_str = r.fecha_operacion.strftime("%d/%m/%Y") if r.fecha_operacion else "S/F"
                
                if esta_cancelado and (r.fecha_cancelacion or r.fecha_pago):
                    f_canc_dt = r.fecha_cancelacion or r.fecha_pago
                    f_canc_str = f_canc_dt.strftime("%d/%m/%Y")
                else:
                    f_canc_str = "---"

                prefix = "Bs. " if getattr(r, 'moneda', "USD") == "VES" else "$ "
                monto_str = f"{prefix}{r.cuanto:,.2f}"

                cp_str = self._formatear_cirujano(
                    getattr(r, 'cirujano_p_nombre', r.cirujano_p),
                    getattr(r, 'cirujano_p_cedula', ""),
                    getattr(r, 'cirujano_p_monto', 0.0),
                    prefix
                )
                ca1_str = self._formatear_cirujano(
                    getattr(r, 'cirujano_aux1_nombre', r.cirujano_aux1),
                    getattr(r, 'cirujano_aux1_cedula', ""),
                    getattr(r, 'cirujano_aux1_monto', 0.0),
                    prefix
                )
                ca2_str = self._formatear_cirujano(
                    getattr(r, 'cirujano_aux2_nombre', r.cirujano_aux2),
                    getattr(r, 'cirujano_aux2_cedula', ""),
                    getattr(r, 'cirujano_aux2_monto', 0.0),
                    prefix
                )

                if esta_cancelado:
                    est_str = "CANCELADA"
                    bg_c = c_verde
                else:
                    est_str = "PENDIENTE"
                    bg_c = c_amarillo

                item = QTreeWidgetItem(self.arbol_recientes, [
                    f_op_str, f_canc_str, pac_nom, r.procedimiento, r.clinica or "", cp_str, ca1_str, ca2_str, monto_str, est_str
                ])
                item.setData(0, Qt.UserRole, r.id)

                for col in range(10):
                    item.setBackground(col, QBrush(bg_c))
                    item.setForeground(col, QBrush(c_texto_negro))

            self._ajustar_columnas(self.arbol_recientes)

        finally:
            db.close()

    # =========================================================================
    # CARGA DE HISTORIAL Y TOTALES
    # =========================================================================
    def cargar_historial_rendimientos(self):
        self.arbol_historial.clear()
        db = SessionLocal()
        try:
            rendimientos = db.query(Rendimiento).order_by(Rendimiento.fecha_operacion.desc()).all()

            estructura = {}
            nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

            c_verde = QColor(212, 237, 218)     # Verde claro (#D4EDDA)
            c_amarillo = QColor(255, 243, 205)  # Amarillo suave (#FFF3CD)
            c_texto_negro = QColor(0, 0, 0)

            for r in rendimientos:
                if not r.fecha_operacion: continue
                ano = r.fecha_operacion.year
                mes_num = r.fecha_operacion.month

                if ano not in estructura:
                    estructura[ano] = {}
                if mes_num not in estructura[ano]:
                    estructura[ano][mes_num] = []

                estructura[ano][mes_num].append(r)

            for ano in sorted(estructura.keys(), reverse=True):
                item_ano = QTreeWidgetItem(self.arbol_historial, [f"📅 AÑO {ano}"])
                font_ano = item_ano.font(0)
                font_ano.setBold(True); font_ano.setPointSize(12)
                item_ano.setFont(0, font_ano)
                item_ano.setForeground(0, QBrush(QColor("#3498db")))

                total_ano_pagado_usd = 0.0
                total_ano_pagado_ves = 0.0

                for mes_num in sorted(estructura[ano].keys(), reverse=True):
                    lista_m = estructura[ano][mes_num]
                    nombre_mes = nombres_meses[mes_num - 1]

                    total_mes_usd = sum(r.cuanto for r in lista_m if (r.cancelado or r.pagado) and getattr(r, 'moneda', 'USD') == 'USD')
                    total_mes_ves = sum(r.cuanto for r in lista_m if (r.cancelado or r.pagado) and getattr(r, 'moneda', 'USD') == 'VES')

                    total_ano_pagado_usd += total_mes_usd
                    total_ano_pagado_ves += total_mes_ves

                    tot_mes_str = f"TOTAL CANCELADO: $ {total_mes_usd:,.2f}"
                    if total_mes_ves > 0:
                        tot_mes_str += f" | Bs. {total_mes_ves:,.2f}"

                    item_mes = QTreeWidgetItem(item_ano, [
                        f"🗓️ {nombre_mes} {ano} ({len(lista_m)} op.)", "", "", "", "", "", "", "", "",
                        tot_mes_str, ""
                    ])
                    item_mes.setData(0, Qt.UserRole, {"tipo": "MES", "ano": ano, "mes": mes_num, "nombre_mes": nombre_mes})
                    font_mes = item_mes.font(0)
                    font_mes.setBold(True)
                    item_mes.setFont(0, font_mes)
                    item_mes.setForeground(0, QBrush(QColor("#2ecc71")))

                    for r in lista_m:
                        f_op_str = r.fecha_operacion.strftime("%d/%m/%Y")
                        esta_cancelado = r.cancelado or r.pagado
                        
                        if esta_cancelado and (r.fecha_cancelacion or r.fecha_pago):
                            f_canc_dt = r.fecha_cancelacion or r.fecha_pago
                            f_canc_str = f_canc_dt.strftime("%d/%m/%Y")
                        else:
                            f_canc_str = "---"

                        pac_str = r.paciente.nombre_completo if r.paciente else "N/A"
                        prefix = "Bs. " if getattr(r, 'moneda', "USD") == "VES" else "$ "
                        mod_pago = f"Directo: {prefix}{r.pago_directo:,.2f}" if r.pago_directo > 0 else f"Seguro: {r.seguro or 'N/R'}"

                        cp_str = self._formatear_cirujano(
                            getattr(r, 'cirujano_p_nombre', r.cirujano_p),
                            getattr(r, 'cirujano_p_cedula', ""),
                            getattr(r, 'cirujano_p_monto', 0.0),
                            prefix
                        )
                        ca1_str = self._formatear_cirujano(
                            getattr(r, 'cirujano_aux1_nombre', r.cirujano_aux1),
                            getattr(r, 'cirujano_aux1_cedula', ""),
                            getattr(r, 'cirujano_aux1_monto', 0.0),
                            prefix
                        )
                        ca2_str = self._formatear_cirujano(
                            getattr(r, 'cirujano_aux2_nombre', r.cirujano_aux2),
                            getattr(r, 'cirujano_aux2_cedula', ""),
                            getattr(r, 'cirujano_aux2_monto', 0.0),
                            prefix
                        )

                        if esta_cancelado:
                            est_str = "CANCELADA"
                            bg_c = c_verde
                        else:
                            est_str = "PENDIENTE"
                            bg_c = c_amarillo

                        item_op = QTreeWidgetItem(item_mes, [
                            pac_str, f_op_str, f_canc_str, r.procedimiento, r.clinica or "", mod_pago,
                            cp_str, ca1_str, ca2_str, f"{prefix}{r.cuanto:,.2f}", est_str
                        ])

                        for col in range(11):
                            item_op.setBackground(col, QBrush(bg_c))
                            item_op.setForeground(col, QBrush(c_texto_negro))

                tot_ano_str = f"TOTAL AÑO: $ {total_ano_pagado_usd:,.2f}"
                if total_ano_pagado_ves > 0:
                    tot_ano_str += f" | Bs. {total_ano_pagado_ves:,.2f}"
                item_ano.setText(9, tot_ano_str)
                item_ano.setExpanded(True)

            self._ajustar_columnas(self.arbol_historial)

        finally:
            db.close()

    # =========================================================================
    # EXPORTACIÓN A EXCEL OPTIMIZADA
    # =========================================================================
    def exportar_mes_excel(self):
        if not HAS_OPENPYXL:
            QMessageBox.critical(self, "Librería Faltante", "La librería 'openpyxl' no está instalada.\nEjecute: pip install openpyxl", QMessageBox.Ok)
            return

        item_sel = self.arbol_historial.currentItem()
        if not item_sel:
            QMessageBox.warning(self, "Aviso", "Seleccione un MES en el árbol del historial para exportar.", QMessageBox.Ok)
            return

        data_role = item_sel.data(0, Qt.UserRole)
        if not data_role or data_role.get("tipo") != "MES":
            QMessageBox.warning(self, "Aviso", "Por favor haga clic directamente sobre el encabezado del mes que desea exportar.", QMessageBox.Ok)
            return

        ano = data_role["ano"]
        mes_num = data_role["mes"]
        nombre_mes = data_role["nombre_mes"]

        file_path, _ = QFileDialog.getSaveFileName(self, f"Exportar Rendimientos {nombre_mes} {ano}", f"Rendimientos_{nombre_mes}_{ano}.xlsx", "Archivos Excel (*.xlsx)")
        if not file_path: return

        db = SessionLocal()
        try:
            rendimientos = db.query(Rendimiento).all()
            filtrados = [r for r in rendimientos if r.fecha_operacion and r.fecha_operacion.year == ano and r.fecha_operacion.month == mes_num]

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"{nombre_mes} {ano}"

            font_titulo = Font(name="Arial", size=13, bold=True, color="FFFFFF")
            fill_titulo = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
            
            font_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            fill_header = PatternFill(start_color="374151", end_color="374151", fill_type="solid")
            
            font_total = Font(name="Arial", size=11, bold=True, color="15803D")
            border_thin = Border(left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'), top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1'))

            ws.merge_cells("A1:L1")
            cell_t = ws.cell(row=1, column=1, value=f"REPORTE DE RENDIMIENTOS Y HONORARIOS MÉDICOS - {nombre_mes.upper()} {ano}")
            cell_t.font = font_titulo
            cell_t.fill = fill_titulo
            cell_t.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 35

            headers = ["Fecha Op.", "Fecha Canc./Pago", "Paciente", "Procedimiento", "Clínica", "Modalidad Pago", "Moneda", "Cirujano Principal", "Cirujano Aux. 1", "Cirujano Aux. 2", "Monto Total", "Estado"]
            ws.append([])

            ws.append(headers)
            ws.row_dimensions[3].height = 25
            for col_idx in range(1, 13):
                cell = ws.cell(row=3, column=col_idx)
                cell.font = font_header
                cell.fill = fill_header
                cell.alignment = Alignment(horizontal="center", vertical="center")

            total_pagado_usd = 0.0
            total_pagado_ves = 0.0

            for idx, r in enumerate(filtrados, start=4):
                f_op_str = r.fecha_operacion.strftime("%d/%m/%Y")
                esta_cancelado = r.cancelado or r.pagado

                if esta_cancelado and (r.fecha_cancelacion or r.fecha_pago):
                    f_canc_dt = r.fecha_cancelacion or r.fecha_pago
                    f_canc_str = f_canc_dt.strftime("%d/%m/%Y")
                else:
                    f_canc_str = "---"

                pac_nom = r.paciente.nombre_completo if r.paciente else "N/A"
                moneda_str = getattr(r, 'moneda', 'USD')
                prefix = "Bs. " if moneda_str == "VES" else "$ "
                mod_pago = f"Directo: {prefix}{r.pago_directo:,.2f}" if r.pago_directo > 0 else f"Seguro: {r.seguro or 'N/R'}"
                
                cp_str = self._formatear_cirujano(getattr(r, 'cirujano_p_nombre', r.cirujano_p), getattr(r, 'cirujano_p_cedula', ""), getattr(r, 'cirujano_p_monto', 0.0), prefix)
                ca1_str = self._formatear_cirujano(getattr(r, 'cirujano_aux1_nombre', r.cirujano_aux1), getattr(r, 'cirujano_aux1_cedula', ""), getattr(r, 'cirujano_aux1_monto', 0.0), prefix)
                ca2_str = self._formatear_cirujano(getattr(r, 'cirujano_aux2_nombre', r.cirujano_aux2), getattr(r, 'cirujano_aux2_cedula', ""), getattr(r, 'cirujano_aux2_monto', 0.0), prefix)

                est_str = "CANCELADA" if esta_cancelado else "PENDIENTE"

                if esta_cancelado:
                    if moneda_str == "VES": total_pagado_ves += r.cuanto
                    else: total_pagado_usd += r.cuanto

                row_data = [f_op_str, f_canc_str, pac_nom, r.procedimiento, r.clinica or "", mod_pago, moneda_str, cp_str, ca1_str, ca2_str, r.cuanto, est_str]
                ws.append(row_data)

                cell_monto = ws.cell(row=idx, column=11)
                cell_monto.number_format = '"$"#,##0.00' if moneda_str == "USD" else '"Bs."#,##0.00'

                for c_i in range(1, 13):
                    ws.cell(row=idx, column=c_i).border = border_thin

            row_tot = len(filtrados) + 5
            ws.cell(row=row_tot, column=10, value="TOTAL CANCELADO ($):").font = font_total
            ws.cell(row=row_tot, column=10).alignment = Alignment(horizontal="right")
            
            c_usd = ws.cell(row=row_tot, column=11, value=total_pagado_usd)
            c_usd.font = font_total
            c_usd.number_format = '"$"#,##0.00'

            if total_pagado_ves > 0:
                row_tot_ves = row_tot + 1
                ws.cell(row=row_tot_ves, column=10, value="TOTAL CANCELADO (Bs.):").font = font_total
                ws.cell(row=row_tot_ves, column=10).alignment = Alignment(horizontal="right")
                c_ves = ws.cell(row=row_tot_ves, column=11, value=total_pagado_ves)
                c_ves.font = font_total
                c_ves.number_format = '"Bs."#,##0.00'

            for col in ws.columns:
                col_letter = get_column_letter(col[0].column)
                
                max_len = 0
                for cell in col:
                    if cell.row > 1 and cell.value is not None:
                        val_str = str(cell.value)
                        if isinstance(cell.value, (int, float)):
                            val_str = f"Bs. {cell.value:,.2f}"
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                
                ws.column_dimensions[col_letter].width = max(max_len + 5, 18)

            wb.save(file_path)
            QMessageBox.information(self, "Exportación Exitosa", f"El archivo Excel ha sido generado con éxito en:\n{file_path}", QMessageBox.Ok)

        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo generar el archivo Excel: {e}", QMessageBox.Ok)
        finally:
            db.close()