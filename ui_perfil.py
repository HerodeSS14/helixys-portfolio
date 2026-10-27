from PySide6.QtWidgets import (QAbstractItemView, QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QFileDialog, QLabel, QHBoxLayout, 
                             QMessageBox, QStackedWidget, QFrame, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QComboBox, QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPixmap
from database import SessionLocal
from models import PerfilDoctor, Paciente, Consulta, AgendaDiaria, Antecedentes, GinecoObstetrico, RecipeOrden, Usuario
from servicios_impresion import MotorImpresion
import os
import shutil
from datetime import datetime
from estilos import tema  # Motor de diseño centralizado
import bcrypt
import secrets
import string

class SeguridadManager:
    @staticmethod
    def cambiar_credenciales(usuario_id, nuevo_user, nueva_pass):
        db = SessionLocal()
        usuario = db.query(Usuario).get(usuario_id)
        if usuario:
            usuario.username = nuevo_user
            # Encriptamos la nueva contraseña
            salt = bcrypt.gensalt()
            usuario.password_hash = bcrypt.hashpw(nueva_pass.encode('utf-8'), salt).decode('utf-8')
            db.commit()
            db.close()
            return True
        return False

    @staticmethod
    def configurar_recuperacion(usuario_id, preg1, resp1, preg2, resp2):
        db = SessionLocal()
        usuario = db.query(Usuario).get(usuario_id)
        if usuario:
            usuario.pregunta_seguridad_1 = preg1
            usuario.pregunta_seguridad_2 = preg2
            
            # Encriptamos las respuestas (en minúsculas y sin espacios para evitar errores de tipeo al recuperar)
            r1_limpia = resp1.strip().lower()
            r2_limpia = resp2.strip().lower()
            
            usuario.respuesta_hash_1 = bcrypt.hashpw(r1_limpia.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            usuario.respuesta_hash_2 = bcrypt.hashpw(r2_limpia.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.commit()
            db.close()
            return True
        return False

    @staticmethod
    def generar_codigo_maestro(usuario_id):
        """Genera un código tipo XXXX-XXXX-XXXX para imprimir y guardar en caja fuerte"""
        caracteres = string.ascii_uppercase + string.digits
        codigo_plano = '-'.join([''.join(secrets.choice(caracteres) for _ in range(4)) for _ in range(3)])
        
        db = SessionLocal()
        usuario = db.query(Usuario).get(usuario_id)
        if usuario:
            usuario.codigo_maestro_hash = bcrypt.hashpw(codigo_plano.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.commit()
            db.close()
            
            # Se devuelve en texto plano SOLO ESTA VEZ para que el doctor lo imprima o anote
            return codigo_plano 
        return None
    
class PantallaConfiguracion(QWidget):
    # SEÑAL: Se emitirá cada vez que un paciente sea borrado de la DB
    paciente_eliminado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(tema.ESTILO_VENTANA)
        layout_principal = QVBoxLayout(self)
        
        # --- CABECERA DE NAVEGACIÓN ---
        self.nav_layout = QHBoxLayout()
        self.btn_nav_perfil = QPushButton("👤 Perfil Médico")
        self.btn_nav_mantenimiento = QPushButton("🛠️ Mantenimiento")
        self.btn_nav_seguridad = QPushButton("🔒 Seguridad")
        
        for b in [self.btn_nav_perfil, self.btn_nav_mantenimiento, self.btn_nav_seguridad]:
            b.setFixedHeight(40)
            self.nav_layout.addWidget(b)
        
        layout_principal.addLayout(self.nav_layout)

        self.stack = QStackedWidget()
        layout_principal.addWidget(self.stack)

        # SECCIONES
        self.widget_perfil = QWidget(); self.setup_perfil()
        self.widget_mantenimiento = QWidget(); self.setup_mantenimiento()
        self.widget_seguridad = QWidget(); self.setup_seguridad()
        
        self.stack.addWidget(self.widget_perfil)
        self.stack.addWidget(self.widget_mantenimiento)
        self.stack.addWidget(self.widget_seguridad)

        # Conexiones de navegación con actualización de estado visual instantáneo
        self.btn_nav_perfil.clicked.connect(lambda: self.cambiar_pestaña(0))
        self.btn_nav_mantenimiento.clicked.connect(self.abrir_mantenimiento)
        self.btn_nav_seguridad.clicked.connect(lambda: self.cambiar_pestaña(2))

        # Conectar reactividad central
        tema.tema_cambiado.connect(self.actualizar_diseno_dinamico)
        self.actualizar_diseno_dinamico()
        self.cargar_datos_actuales()

    def setup_perfil(self):
        # 🚀 CORREGIDO: Creamos un layout principal para el widget del perfil que sostendrá el Scroll
        layout_pestaña = QVBoxLayout(self.widget_perfil)
        layout_pestaña.setContentsMargins(0, 0, 0, 0)

        # Creación del QScrollArea
        self.scroll_perfil = QScrollArea()
        self.scroll_perfil.setWidgetResizable(True)
        
        # Contenedor interno que llevará el formulario real
        self.scroll_content_perfil = QWidget()
        layout = QVBoxLayout(self.scroll_content_perfil)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.logo_path = ""; self.firma_path = ""; self.largo_previo_especialidad = 0
        
        self.lbl_tit_perfil = QLabel("<h2>👤 Datos del Consultorio</h2>")
        layout.addWidget(self.lbl_tit_perfil)
        
        self.form = QFormLayout()
        self.form.setSpacing(10)
        
        self.in_clinica = QLineEdit()
        self.in_doctor = QLineEdit()
        
        # Selector de Género
        self.combo_genero_doc = QComboBox()
        self.combo_genero_doc.addItems(["Femenino", "Masculino"])
        
        self.in_cedula = QLineEdit()
        self.in_especialidad = QLineEdit(placeholderText="Ej: Ginecología - Obstetricia")
        self.in_msds = QLineEdit()
        self.in_rif = QLineEdit()
        self.in_correo = QLineEdit()
        self.in_direccion = QLineEdit()

        # Labels del formulario para tracking de estilos
        self.labels_formulario = []
        campos = [
            ("Clínica:", self.in_clinica),
            ("Doctor(a):", self.in_doctor),
            ("Género del Especialista:", self.combo_genero_doc),
            ("Cédula:", self.in_cedula),
            ("Especialidad:", self.in_especialidad),
            ("MSDS:", self.in_msds),
            ("RIF:", self.in_rif),
            ("Correo:", self.in_correo),
            ("Dirección:", self.in_direccion)
        ]

        for texto_lbl, widget_in in campos:
            lbl = QLabel(texto_lbl)
            self.form.addRow(lbl, widget_in)
            self.labels_formulario.append(lbl)

        for edit in [self.in_clinica, self.in_doctor, self.in_direccion]:
            edit.textChanged.connect(lambda text, e=edit: self.formatear_mayusculas(text, e))
        self.in_especialidad.textChanged.connect(lambda text: self.formatear_especialidad(text, self.in_especialidad))

        # --- ROW DE RECURSOS GRÁFICOS COMPARTIDA ---
        self.lbl_tit_recursos = QLabel("Recursos Gráficos:")
        self.labels_formulario.append(self.lbl_tit_recursos)
        
        container_recursos = QWidget()
        lay_recursos_h = QHBoxLayout(container_recursos)
        lay_recursos_h.setContentsMargins(0, 5, 0, 5)
        lay_recursos_h.setSpacing(20)

        # Bloque Izquierdo: LOGO
        vbox_logo = QVBoxLayout()
        self.btn_logo = QPushButton("📷 Cargar Logo")
        self.btn_logo.setFixedHeight(38)
        self.btn_logo.setMinimumWidth(150)
        self.btn_logo.clicked.connect(self.seleccionar_logo)
        
        self.lbl_preview_logo = QLabel()
        self.lbl_preview_logo.setFixedSize(100, 100)
        self.lbl_preview_logo.setAlignment(Qt.AlignCenter)
        
        vbox_logo.addWidget(self.btn_logo)
        vbox_logo.addWidget(self.lbl_preview_logo, 0, Qt.AlignCenter)
        lay_recursos_h.addLayout(vbox_logo)

        # Bloque Derecho: FIRMA
        vbox_firma = QVBoxLayout()
        self.btn_firma = QPushButton("✍️ Cargar Firma")
        self.btn_firma.setFixedHeight(38)
        self.btn_firma.setMinimumWidth(150)
        self.btn_firma.clicked.connect(self.seleccionar_firma)
        
        self.lbl_preview_firma = QLabel()
        self.lbl_preview_firma.setFixedSize(150, 70)
        self.lbl_preview_firma.setAlignment(Qt.AlignCenter)
        
        vbox_firma.addWidget(self.btn_firma)
        vbox_firma.addWidget(self.lbl_preview_firma, 0, Qt.AlignCenter)
        lay_recursos_h.addLayout(vbox_firma)

        self.form.addRow(self.lbl_tit_recursos, container_recursos)
        layout.addLayout(self.form)

        self.btn_guardar = QPushButton("💾 GUARDAR CAMBIOS PERFIL")
        self.btn_guardar.setFixedHeight(45)
        self.btn_guardar.clicked.connect(lambda: self.guardar_perfil())
        layout.addWidget(self.btn_guardar)
        layout.addStretch()

        # 🚀 Asignamos el contenedor al scroll y el scroll al layout de la pestaña
        self.scroll_perfil.setWidget(self.scroll_content_perfil)
        layout_pestaña.addWidget(self.scroll_perfil)

    def setup_mantenimiento(self):
        layout = QVBoxLayout(self.widget_mantenimiento)
        self.lbl_tit_mant = QLabel("<h2>🛠️ Mantenimiento de Datos</h2>")
        layout.addWidget(self.lbl_tit_mant)

        # 📂 BLOQUE 1: LIMPIEZA DE ARCHIVOS
        self.grupo_archivos = QFrame()
        lay_arc = QVBoxLayout(self.grupo_archivos)
        self.lbl_sub_gestion = QLabel("<b>📂 Gestión de Espacio:</b>")
        lay_arc.addWidget(self.lbl_sub_gestion)
        
        self.btn_limpiar_pdfs = QPushButton("🗑️ VACIAR CARPETA DE RÉCIPES (PDF)")
        self.btn_limpiar_pdfs.setFixedHeight(40)
        self.btn_limpiar_pdfs.clicked.connect(lambda: self.accion_limpiar_pdfs())
        lay_arc.addWidget(self.btn_limpiar_pdfs)
        layout.addWidget(self.grupo_archivos)

        # 👥 BLOQUE 2: ELIMINACIÓN SELECTIVA
        self.grupo_pacientes = QFrame()
        lay_pac = QVBoxLayout(self.grupo_pacientes)
        self.lbl_sub_elim = QLabel("<b>👥 Eliminación Individual de Pacientes:</b>")
        lay_pac.addWidget(self.lbl_sub_elim)
        
        self.in_buscar_mant = QLineEdit(placeholderText="Buscar por nombre o cédula para eliminar...")
        self.in_buscar_mant.textChanged.connect(self.actualizar_arbol_mantenimiento)
        lay_pac.addWidget(self.in_buscar_mant)

        self.tree_pacientes = QTreeWidget()
        self.tree_pacientes.setHeaderLabels(["Cédula", "Nombre Completo"])
        self.tree_pacientes.header().setSectionResizeMode(QHeaderView.Stretch)
        lay_pac.addWidget(self.tree_pacientes)

        self.btn_eliminar_individual = QPushButton("❌ ELIMINAR PACIENTE SELECCIONADO")
        self.btn_eliminar_individual.setFixedHeight(40)
        self.btn_eliminar_individual.clicked.connect(lambda: self.eliminar_paciente_individual())
        lay_pac.addWidget(self.btn_eliminar_individual)
        
        layout.addWidget(self.grupo_pacientes)

    def setup_seguridad(self):
        # Layout principal de la pestaña que sostiene al scroll
        layout_pestaña = QVBoxLayout(self.widget_seguridad)
        layout_pestaña.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_seguridad = QScrollArea()
        self.scroll_seguridad.setWidgetResizable(True)
        
        self.scroll_content_seguridad = QWidget()
        layout = QVBoxLayout(self.scroll_content_seguridad)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        self.lbl_tit_seguridad = QLabel("<h2>🔒 Configuración de Seguridad</h2>")
        self.lbl_info_seguridad = QLabel("Gestione sus credenciales de acceso y opciones de recuperación (Módulo cifrado con Bcrypt).")
        layout.addWidget(self.lbl_tit_seguridad)
        layout.addWidget(self.lbl_info_seguridad)

        # --- BLOQUE 1: CAMBIO DE CREDENCIALES ---
        self.grupo_credenciales = QFrame()
        lay_cred = QFormLayout(self.grupo_credenciales)
        self.lbl_sub_cred = QLabel("<b>🔑 Cambiar Usuario y Contraseña</b>")
        lay_cred.addRow(self.lbl_sub_cred)
        
        self.in_nuevo_usuario = QLineEdit(placeholderText="Nuevo nombre de usuario")
        self.in_nueva_pass = QLineEdit(placeholderText="Nueva contraseña")
        self.in_nueva_pass.setEchoMode(QLineEdit.Password)
        
        lay_cred.addRow("Nuevo Usuario:", self.in_nuevo_usuario)
        lay_cred.addRow("Nueva Contraseña:", self.in_nueva_pass)
        
        self.btn_guardar_cred = QPushButton("Guardar Nuevas Credenciales")
        self.btn_guardar_cred.setFixedHeight(35)
        self.btn_guardar_cred.clicked.connect(self.accion_guardar_credenciales)
        lay_cred.addRow("", self.btn_guardar_cred)
        
        layout.addWidget(self.grupo_credenciales)

        # --- BLOQUE 2: PREGUNTAS DE SEGURIDAD ---
        self.grupo_preguntas = QFrame()
        lay_preg = QFormLayout(self.grupo_preguntas)
        self.lbl_sub_preg = QLabel("<b>🛡️ Configurar Preguntas de Seguridad (Nivel 1)</b>")
        lay_preg.addRow(self.lbl_sub_preg)
        
        self.in_preg1 = QLineEdit(placeholderText="Ej: ¿Cuál fue el nombre de tu primera mascota?")
        self.in_resp1 = QLineEdit(placeholderText="Respuesta 1")
        self.in_preg2 = QLineEdit(placeholderText="Ej: ¿En qué ciudad nació tu madre?")
        self.in_resp2 = QLineEdit(placeholderText="Respuesta 2")
        
        lay_preg.addRow("Pregunta 1:", self.in_preg1)
        lay_preg.addRow("Respuesta 1:", self.in_resp1)
        lay_preg.addRow("Pregunta 2:", self.in_preg2)
        lay_preg.addRow("Respuesta 2:", self.in_resp2)
        
        self.btn_guardar_preg = QPushButton("Guardar Preguntas de Seguridad")
        self.btn_guardar_preg.setFixedHeight(35)
        self.btn_guardar_preg.clicked.connect(self.accion_guardar_preguntas)
        lay_preg.addRow("", self.btn_guardar_preg)
        
        layout.addWidget(self.grupo_preguntas)

        # --- BLOQUE 3: CÓDIGO MAESTRO ---
        self.grupo_codigo = QFrame()
        lay_cod = QVBoxLayout(self.grupo_codigo)
        lay_cod.setSpacing(15)
        
        self.lbl_sub_cod = QLabel("<b>🚨 Código Maestro de Emergencia (Nivel 2)</b>")
        self.lbl_info_cod = QLabel("Genera un código único para recuperar el sistema si olvida todo lo anterior.\nImprímalo o anótelo y guárdelo en un lugar físico seguro.")
        
        lay_visual_codigo = QHBoxLayout()
        lbl_codigo_texto = QLabel("Código Maestro Actual:")
        self.in_codigo_visual = QLineEdit()
        self.in_codigo_visual.setReadOnly(True)
        self.in_codigo_visual.setAlignment(Qt.AlignCenter)
        self.in_codigo_visual.setPlaceholderText("No generado aún")
        
        fuente_codigo = self.in_codigo_visual.font()
        fuente_codigo.setPointSize(16)
        fuente_codigo.setBold(True)
        self.in_codigo_visual.setFont(fuente_codigo)
        
        lay_visual_codigo.addWidget(lbl_codigo_texto)
        lay_visual_codigo.addWidget(self.in_codigo_visual, 1)
        
        self.btn_generar_codigo = QPushButton("Generar Nuevo Código Maestro")
        self.btn_generar_codigo.setFixedHeight(40)
        self.btn_generar_codigo.clicked.connect(self.accion_generar_codigo)
        
        lay_cod.addWidget(self.lbl_sub_cod)
        lay_cod.addWidget(self.lbl_info_cod)
        lay_cod.addLayout(lay_visual_codigo)
        lay_cod.addWidget(self.btn_generar_codigo) # Se mete aquí directo al QFrame
        
        layout.addWidget(self.grupo_codigo)

        # --- BLOQUE 4: GESTIÓN DE SECRETARIA ---
        self.grupo_secretaria = QFrame()
        lay_sec = QVBoxLayout(self.grupo_secretaria)
        lay_sec.setSpacing(12)
        
        self.lbl_sub_sec = QLabel("<b>👩‍💼 Cuenta de Secretaria (Rol Secundario)</b>")
        self.lbl_info_sec = QLabel("Asigne credenciales para su asistente. Si elimina la cuenta, el acceso será revocado.")
        
        lay_sec.addWidget(self.lbl_sub_sec)
        lay_sec.addWidget(self.lbl_info_sec)
        
        form_sec = QFormLayout()
        self.in_sec_usuario = QLineEdit(placeholderText="Usuario de la Secretaria")
        self.in_sec_pass = QLineEdit(placeholderText="Contraseña de la Secretaria")
        form_sec.addRow("Usuario:", self.in_sec_usuario)
        form_sec.addRow("Contraseña:", self.in_sec_pass)
        lay_sec.addLayout(form_sec)
        
        self.btn_guardar_sec = QPushButton("Crear / Actualizar Secretaria")
        self.btn_guardar_sec.setFixedHeight(35)
        self.btn_guardar_sec.clicked.connect(self.accion_guardar_secretaria)
        lay_sec.addWidget(self.btn_guardar_sec)
        
        layout.addWidget(self.grupo_secretaria)

        # --- TABLA DE SECRETARIAS REGISTRADAS ---
        self.lbl_titulo_tabla = QLabel("<b>Asistentes registradas en el sistema:</b>")
        self.tabla_secretarias = QTableWidget(0, 3)
        self.tabla_secretarias.setHorizontalHeaderLabels(["Usuario", "Contraseña", "Acciones"])
        self.tabla_secretarias.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_secretarias.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_secretarias.setMinimumHeight(150)
        
        layout.addWidget(self.lbl_titulo_tabla)
        layout.addWidget(self.tabla_secretarias)

        # El espacio elástico va AL FINAL de todo el contenido, antes de acoplar el scroll
        layout.addStretch()
        
        # Cargas e inicializaciones de datos
        self.cargar_tabla_secretarias()
        self.actualizar_codigo_maestro_visual()
        
        self.scroll_seguridad.setWidget(self.scroll_content_seguridad)
        layout_pestaña.addWidget(self.scroll_seguridad)

    def obtener_id_doctor(self):
        """Helper para obtener el ID del usuario principal (Doctor)"""
        db = SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.rol == "principal").first()
        uid = usuario.id if usuario else None
        db.close()
        return uid
    

    def accion_guardar_credenciales(self):
        usr = self.in_nuevo_usuario.text().strip()
        pwd = self.in_nueva_pass.text().strip()
        if not usr or not pwd:
            box = QMessageBox(QMessageBox.Warning, "Campos Vacíos", "Debe llenar ambos campos para cambiar credenciales.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec(); return
            
        uid = self.obtener_id_doctor()
        if uid and SeguridadManager.cambiar_credenciales(uid, usr, pwd):
            box = QMessageBox(QMessageBox.Information, "Éxito", "Credenciales actualizadas correctamente.\nUse estos datos en su próximo inicio de sesión.", QMessageBox.Ok, self)
            self.in_nuevo_usuario.clear(); self.in_nueva_pass.clear()
        else:
            box = QMessageBox(QMessageBox.Critical, "Error", "No se pudo actualizar las credenciales.", QMessageBox.Ok, self)
        self.actualizar_emergente_parent(box); box.exec()

    def accion_guardar_preguntas(self):
        p1 = self.in_preg1.text().strip(); r1 = self.in_resp1.text().strip()
        p2 = self.in_preg2.text().strip(); r2 = self.in_resp2.text().strip()
        
        if not all([p1, r1, p2, r2]):
            box = QMessageBox(QMessageBox.Warning, "Incompleto", "Debe llenar ambas preguntas y respuestas.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec(); return
            
        uid = self.obtener_id_doctor()
        if uid and SeguridadManager.configurar_recuperacion(uid, p1, r1, p2, r2):
            box = QMessageBox(QMessageBox.Information, "Éxito", "Preguntas de seguridad configuradas e incrustadas con encriptación.", QMessageBox.Ok, self)
            self.in_preg1.clear(); self.in_resp1.clear(); self.in_preg2.clear(); self.in_resp2.clear()
        else:
            box = QMessageBox(QMessageBox.Critical, "Error", "No se pudo guardar la configuración.", QMessageBox.Ok, self)
        self.actualizar_emergente_parent(box); box.exec()

    def accion_generar_codigo(self):
        box_conf = QMessageBox(QMessageBox.Warning, "Atención", "Se generará un nuevo Código Maestro.\nSi tenía uno anterior, dejará de funcionar automáticamente.\n\n¿Desea continuar?", QMessageBox.Yes | QMessageBox.No, self)
        self.actualizar_emergente_parent(box_conf)
        
        if box_conf.exec() == QMessageBox.Yes:
            uid = self.obtener_id_doctor()
            if uid:
                # Generamos un código alfanumérico seguro tipo XXXX-XXXX-XXXX
                caracteres = string.ascii_uppercase + string.digits
                codigo_plano = '-'.join([''.join(secrets.choice(caracteres) for _ in range(4)) for _ in range(3)])
                
                db = SessionLocal()
                usuario = db.query(Usuario).get(uid)
                if usuario:
                    # Guardamos el Hash para las validaciones del Login y el plano para la UI
                    usuario.codigo_maestro_hash = bcrypt.hashpw(codigo_plano.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    usuario.codigo_maestro_plain = codigo_plano
                    db.commit()
                    
                    # Lo mostramos directamente reemplazando el anterior en tiempo real
                    self.in_codigo_visual.setText(codigo_plano)
                    
                    box = QMessageBox(QMessageBox.Information, "CÓDIGO GENERADO", f"Su nuevo Código Maestro ha sido creado y guardado:\n\n{codigo_plano}\n\nSe mantendrá visible permanentemente en este panel.", QMessageBox.Ok, self)
                else:
                    box = QMessageBox(QMessageBox.Critical, "Error", "No se encontró el usuario principal.", QMessageBox.Ok, self)
                db.close()
                self.actualizar_emergente_parent(box); box.exec()
    def cargar_tabla_secretarias(self):
        """Lee la BD y puebla la tabla de secretarias con su información"""
        db = SessionLocal()
        # Buscamos los usuarios que tengan el rol secundaria
        secretarias = db.query(Usuario).filter(Usuario.rol == "secundaria").all()
        db.close()

        self.tabla_secretarias.setRowCount(0) # Limpiamos filas anteriores

        for i, sec in enumerate(secretarias):
            self.tabla_secretarias.insertRow(i)
            
            # Nombre de usuario
            self.tabla_secretarias.setItem(i, 0, QTableWidgetItem(sec.username))
            
            # Contraseña en texto plano visible
            self.tabla_secretarias.setItem(i, 1, QTableWidgetItem(sec.secretaria_pass_plain or "N/A"))
            
            # Botón de eliminar dinámico
            btn_elim = QPushButton("🗑️ Eliminar")
            btn_elim.setStyleSheet("background-color: #F04747; color: white; font-weight: bold; border-radius: 4px; padding: 3px;")
            btn_elim.setCursor(Qt.PointingHandCursor)
            btn_elim.clicked.connect(lambda checked, u=sec.username: self.accion_eliminar_secretaria(u))
            
            # Centramos el botón dentro de la celda
            btn_widget = QWidget()
            btn_lay = QHBoxLayout(btn_widget)
            btn_lay.setContentsMargins(5, 2, 5, 2)
            btn_lay.addWidget(btn_elim)
            btn_lay.setAlignment(Qt.AlignCenter)
            
            self.tabla_secretarias.setCellWidget(i, 2, btn_widget)
            
    def accion_guardar_secretaria(self):
        usr = self.in_sec_usuario.text().strip()
        pwd = self.in_sec_pass.text().strip()
        
        if not usr or not pwd:
            box = QMessageBox(QMessageBox.Warning, "Campos Vacíos", "Ingrese un usuario y contraseña para la secretaria.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec(); return
            
        db = SessionLocal()
        try:
            # Buscamos si ya existe una asistente con ese nombre
            sec = db.query(Usuario).filter(Usuario.username == usr, Usuario.rol == "secundaria").first()
            salt = bcrypt.gensalt()
            hash_pwd = bcrypt.hashpw(pwd.encode('utf-8'), salt).decode('utf-8')
            
            if sec:
                sec.password_hash = hash_pwd
                sec.secretaria_pass_plain = pwd  # Guardamos texto plano para la tabla
                msg = f"Contraseña de '{usr}' actualizada con éxito."
            else:
                nueva_sec = Usuario(username=usr, password_hash=hash_pwd, rol="secundaria", secretaria_pass_plain=pwd)
                db.add(nueva_sec)
                msg = f"Cuenta de asistente '{usr}' creada con éxito."
                
            db.commit()
            box = QMessageBox(QMessageBox.Information, "Éxito", msg, QMessageBox.Ok, self)
            self.in_sec_usuario.clear()
            self.in_sec_pass.clear()
            
            # Refrescamos la tabla automáticamente
            self.cargar_tabla_secretarias()
            
        except Exception as e:
            db.rollback()
            box = QMessageBox(QMessageBox.Critical, "Error", f"Error en el proceso: {e}", QMessageBox.Ok, self)
        finally:
            db.close()
            
            
        self.actualizar_emergente_parent(box); box.exec()

    def actualizar_codigo_maestro_visual(self):
        """Busca si el doctor ya tiene un código maestro guardado y lo muestra en el cuadro de texto"""
        db = SessionLocal()
        doctor = db.query(Usuario).filter(Usuario.rol == "principal").first()
        db.close()
        
        if doctor and doctor.codigo_maestro_plain:
            self.in_codigo_visual.setText(doctor.codigo_maestro_plain)
        else:
            self.in_codigo_visual.clear()

    def accion_eliminar_secretaria(self, username_a_eliminar):
        box_conf = QMessageBox(QMessageBox.Critical, "Revocar Acceso", f"¿Está seguro de eliminar de forma permanente el acceso de '{username_a_eliminar}'?", QMessageBox.Yes | QMessageBox.No, self)
        self.actualizar_emergente_parent(box_conf)
        
        if box_conf.exec() == QMessageBox.Yes:
            db = SessionLocal()
            try:
                sec = db.query(Usuario).filter(Usuario.username == username_a_eliminar, Usuario.rol == "secundaria").first()
                if sec:
                    db.delete(sec)
                    db.commit()
                    box = QMessageBox(QMessageBox.Information, "Acceso Revocado", f"La cuenta de asistente '{username_a_eliminar}' ha sido eliminada.", QMessageBox.Ok, self)
                    
                    # Refrescamos la tabla automáticamente para que desaparezca de la pantalla
                    self.cargar_tabla_secretarias()
                else:
                    box = QMessageBox(QMessageBox.Warning, "Aviso", "No se encontró el usuario en el sistema.", QMessageBox.Ok, self)
            except Exception as e:
                db.rollback()
                box = QMessageBox(QMessageBox.Critical, "Error", f"Error al eliminar: {e}", QMessageBox.Ok, self)
            finally:
                db.close()
                
            self.actualizar_emergente_parent(box); box.exec()

    def cambiar_pestaña(self, indice):
        self.stack.setCurrentIndex(indice)
        self.actualizar_estilo_navegacion()

    def abrir_mantenimiento(self):
        self.cambiar_pestaña(1)
        self.actualizar_arbol_mantenimiento()

    def actualizar_emergente_parent(self, box):
        box.setWindowFlags(box.windowFlags() | Qt.Dialog)
        box.setStyleSheet(tema.ESTILO_VENTANA)

    def actualizar_diseno_dinamico(self):
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_paginas = "#36393e" if tema.modo_actual == "oscuro" else tema.BG_TARJETA
        color_fondo_entry = "#424549" if tema.modo_actual == "oscuro" else "#FFFFFF"
        border_entry = f"1px solid {tema.BORDE_SUAVE}" if tema.modo_actual == "oscuro" else "1px solid #CCCCCC"

        # 1. Fondos de los contenedores del Stack
        self.widget_perfil.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.widget_mantenimiento.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.widget_seguridad.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        # 🚀 NUEVO BLINDAJE PARA EL SCROLLBAR DEL PERFIL: Elimina bordes y acopla el fondo
        self.scroll_perfil.setStyleSheet(f"QScrollArea {{ border: none; background-color: {color_fondo_paginas}; }}")
        self.scroll_content_perfil.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        self.scroll_seguridad.setStyleSheet(f"QScrollArea {{ border: none; background-color: {color_fondo_paginas}; }}")
        self.scroll_content_seguridad.setStyleSheet(f"background-color: {color_fondo_paginas}; border: none;")
        # Títulos Principales h2
        for tit in [self.lbl_tit_perfil, self.lbl_tit_mant, self.lbl_tit_seguridad]:
            tit.setStyleSheet(f"color: {color_txt}; background: transparent;")
        
        self.lbl_info_seguridad.setStyleSheet(f"color: {color_txt}; background: transparent; font-size: 14px;")

        # Labels de texto estático del Formulario de Perfil
        for lbl in self.labels_formulario + [self.btn_logo, self.btn_firma]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent;")
        # Agregar los dos nuevos Labels de preview al refresco dinámico
        
        for lbl in self.labels_formulario + [self.lbl_preview_logo, self.lbl_preview_firma]:
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 14px; background: transparent; border: none;")
        # 2. 🚀 BLINDAJE DE ENTRADAS CONTRA FOCUS BLANCO
        style_inputs = f"""
            QLineEdit {{
                border: {border_entry}; 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                font-size: 14px; 
                padding: 8px;
                border-radius: 5px;
            }}
            QLineEdit:focus {{
                border: 1px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
            }}
        """
        for in_widget in [self.in_clinica, self.in_doctor, self.in_cedula, self.in_especialidad, self.in_msds, self.in_rif, self.in_correo, self.in_direccion, self.in_buscar_mant, 
                          self.in_nuevo_usuario, self.in_nueva_pass, self.in_preg1, self.in_resp1, self.in_preg2, self.in_resp2, self.in_sec_usuario, self.in_sec_pass]: # NUEVOS AL FINAL
            in_widget.setStyleSheet(style_inputs)

        # 3. Selector Desplegable QComboBox adaptivo
        self.combo_genero_doc.setStyleSheet(f"""
            QComboBox {{
                border: {border_entry};
                background-color: {color_fondo_entry};
                color: {color_txt};
                padding: 6px 12px;
                border-radius: 5px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: {tema.BORDE_SUAVE};
                border-left-style: solid;
            }}
            QComboBox QAbstractItemView {{
                background-color: {color_fondo_entry};
                color: {color_txt};
                selection-background-color: {tema.MENTA_MEDICA};
                selection-color: #1C1C1C;
                border: 1px solid {tema.BORDE_SUAVE};
            }}
        """)

        # 4. Marcos/Bloques de la sección de mantenimiento
        style_marcos = f"""
            QFrame {{
                background-color: {tema.BG_TARJETA if tema.modo_actual == 'oscuro' else '#FFFFFF'};
                border: 1px solid {tema.BORDE_SUAVE};
                border-radius: 8px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """
        self.grupo_archivos.setStyleSheet(style_marcos)
        self.grupo_pacientes.setStyleSheet(style_marcos)
        # --- AQUÍ VAN LOS NUEVOS MARCOS ---
        self.grupo_credenciales.setStyleSheet(style_marcos)
        self.grupo_preguntas.setStyleSheet(style_marcos)
        self.grupo_codigo.setStyleSheet(style_marcos)
        self.grupo_secretaria.setStyleSheet(style_marcos)

        # --- AQUÍ VAN LOS NUEVOS LABELS ---
        for lbl in [self.lbl_sub_gestion, self.lbl_sub_elim, self.lbl_sub_cred, self.lbl_sub_preg, self.lbl_sub_cod, self.lbl_sub_sec]: # NUEVO EN LA LISTA
            lbl.setStyleSheet(f"color: {color_txt}; font-size: 14px; font-weight: bold; background: transparent;")
        self.lbl_info_cod.setStyleSheet(f"color: {color_txt}; background: transparent; font-size: 13px;")
        self.lbl_info_sec.setStyleSheet(f"color: {color_txt}; background: transparent; font-size: 13px;") # NUEVO

        # 5. Listado de Mantenimiento QTreeWidget
        self.tree_pacientes.setStyleSheet(f"""
            QTreeWidget {{ 
                background-color: {color_fondo_entry}; 
                color: {color_txt}; 
                border: 1px solid {tema.BORDE_SUAVE}; 
                border-radius: 6px; 
                padding: 5px; 
                font-size: 14px; 
            }}
            QHeaderView::section {{ 
                background-color: #93F6E3; 
                color: #1C1C1C; 
                font-weight: bold; 
                padding: 6px; 
                border: 1px solid {tema.BORDE_SUAVE}; 
            }}
            QTreeView::item {{ color: {color_txt}; padding: 4px; }}
            QTreeView::item:hover {{ background-color: {tema.MENTA_FOCUS}; color: {color_txt}; }}
            QTreeView::item:selected {{ background-color: {tema.MENTA_MEDICA}; color: #1C1C1C; font-weight: bold; }}
        """)

        # 6. Estilos de los Botones Operacionales
        self.btn_logo.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_firma.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_guardar.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_limpiar_pdfs.setStyleSheet(tema.ESTILO_BTN_SECUNDARIO)
        self.btn_eliminar_individual.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_guardar_cred.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_guardar_preg.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.btn_generar_codigo.setStyleSheet(tema.ESTILO_BTN_PELIGRO)
        self.btn_guardar_sec.setStyleSheet(tema.ESTILO_BTN_PRIMARIO)
        self.in_codigo_visual.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {tema.MENTA_MEDICA};
                background-color: {color_fondo_entry};
                color: {tema.MENTA_MEDICA};
                padding: 6px;
                border-radius: 6px;
            }}
        """)
        

        self.actualizar_estilo_navegacion()

    def actualizar_estilo_navegacion(self):
        # Transforma los botones superiores en una barra de pestañas reactiva
        idx_activo = self.stack.currentIndex()
        botones = [self.btn_nav_perfil, self.btn_nav_mantenimiento, self.btn_nav_seguridad]
        
        color_letras_normal = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        color_fondo_normal = "#424549" if tema.modo_actual == "oscuro" else tema.BG_INPUT

        for i, btn in enumerate(botones):
            if i == idx_activo:
                # Pestaña seleccionada (Menta vibrante con letras oscuras de alto contraste)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tema.MENTA_MEDICA};
                        color: #1C1C1C;
                        font-weight: bold;
                        font-size: 14px;
                        border: 1px solid {tema.MENTA_MEDICA};
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                        border-bottom-left-radius: 0px;
                        border-bottom-right-radius: 0px;
                    }}
                """)
            else:
                # Pestaña inactiva integrada al lienzo posterior
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color_fondo_normal};
                        color: {color_letras_normal};
                        font-weight: bold;
                        font-size: 14px;
                        border: 1px solid {tema.BORDE_SUAVE};
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background-color: {tema.MENTA_FOCUS};
                        color: {color_letras_normal};
                    }}
                """)

    def actualizar_arbol_mantenimiento(self):
        self.tree_pacientes.clear()
        filtro = self.in_buscar_mant.text().strip()
        db = SessionLocal()
        query = db.query(Paciente)
        if filtro:
            query = query.filter((Paciente.nombre_completo.ilike(f"%{filtro}%")) | (Paciente.cedula.ilike(f"%{filtro}%")))
        
        pacientes = query.all()
        color_txt = "#FFFFFF" if tema.modo_actual == "oscuro" else tema.TEXTO_MAIN
        
        for p in pacientes:
            item = QTreeWidgetItem([p.cedula, p.nombre_completo])
            item.setData(0, Qt.UserRole, p.id)
            item.setForeground(0, QBrush(QColor(color_txt)))
            item.setForeground(1, QBrush(QColor(color_txt)))
            self.tree_pacientes.addTopLevelItem(item)
        db.close()

    def eliminar_paciente_individual(self):
        seleccion = self.tree_pacientes.currentItem()
        if not seleccion:
            box = QMessageBox(QMessageBox.Warning, "Aviso", "Seleccione un paciente de la lista.", QMessageBox.Ok, self)
            self.actualizar_emergente_parent(box); box.exec(); return

        paciente_id = seleccion.data(0, Qt.UserRole)
        nombre = seleccion.text(1)

        box_conf = QMessageBox(QMessageBox.Critical, "Eliminar Registro", 
                               f"¿Está seguro de eliminar de forma permanente a {nombre}?\n\nEsta acción eliminará consultas, récipes, antecedentes y es completamente irreversible.",
                               QMessageBox.Yes | QMessageBox.No, self)
        self.actualizar_emergente_parent(box_conf)
        
        if box_conf.exec() == QMessageBox.Yes:
            db = SessionLocal()
            try:
                # Borrado regulado en cascada
                db.query(AgendaDiaria).filter_by(paciente_id=paciente_id).delete()
                db.query(RecipeOrden).filter_by(paciente_id=paciente_id).delete()
                db.query(Consulta).filter_by(paciente_id=paciente_id).delete()
                db.query(GinecoObstetrico).filter_by(paciente_id=paciente_id).delete()
                db.query(Antecedentes).filter_by(paciente_id=paciente_id).delete()
                
                p = db.query(Paciente).get(paciente_id)
                if p:
                    db.delete(p)
                db.commit()
                
                box_ok = QMessageBox(QMessageBox.Information, "Éxito", f"El expediente de {nombre} ha sido borrado del sistema médico.", QMessageBox.Ok, self)
                self.actualizar_emergente_parent(box_ok); box_ok.exec()
                
                self.actualizar_arbol_mantenimiento()
                self.paciente_eliminado.emit() 
                
            except Exception as e:
                db.rollback()
                box_err = QMessageBox(QMessageBox.Critical, "Error", f"Fallo al eliminar: {str(e)}", QMessageBox.Ok, self)
                self.actualizar_emergente_parent(box_err); box_err.exec()
            finally:
                db.close()

    def accion_limpiar_pdfs(self):
        box = QMessageBox(QMessageBox.Warning, "Mantenimiento Crítico", "¿Desea limpiar el historial de archivos PDF generados? Esto liberará espacio en el disco pero no borrará las consultas médicas.", QMessageBox.Yes | QMessageBox.No, self)
        self.actualizar_emergente_parent(box)
        if box.exec() == QMessageBox.Yes:
            if MotorImpresion.limpiar_carpeta_pdf():
                box_ok = QMessageBox(QMessageBox.Information, "Éxito", "Carpeta de reportes digitales liberada correctamente.", QMessageBox.Ok, self)
                self.actualizar_emergente_parent(box_ok); box_ok.exec()

    def formatear_mayusculas(self, text, edit_widget):
        pos = edit_widget.cursorPosition()
        edit_widget.blockSignals(True)
        edit_widget.setText(text.title())
        edit_widget.setCursorPosition(pos)
        edit_widget.blockSignals(False)

    def formatear_especialidad(self, text, edit_widget):
        if len(text) < self.largo_previo_especialidad:
            self.largo_previo_especialidad = len(text); return 
        self.largo_previo_especialidad = len(text)
        if not text: return
        pos = edit_widget.cursorPosition(); edit_widget.blockSignals(True)
        if text.endswith(" ") and len(text) > 1 and text[-2] not in [" ", "-"]:
            text = text[:-1] + " - "; pos += 2
        edit_widget.setText(text.title()); edit_widget.setCursorPosition(pos); edit_widget.blockSignals(False)
        self.largo_previo_especialidad = len(edit_widget.text())

    def seleccionar_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Logo de la Clínica", "", "Imágenes (*.png *.jpg *.jpeg)")
        if path: 
            self.logo_path = path
            self.mostrar_miniatura_logo(path)

    def seleccionar_firma(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Firma Digitalizada", "", "Imágenes (*.png *.jpg *.jpeg)")
        if path: 
            self.firma_path = path
            self.mostrar_miniatura_firma(path)
    def mostrar_miniatura_logo(self, path):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            # Escala la imagen al tamaño del cuadro manteniendo proporciones limpias
            pix_scaled = pix.scaled(self.lbl_preview_logo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_preview_logo.setPixmap(pix_scaled)
        else:
            self.lbl_preview_logo.setText("[Sin Logo]")
            self.lbl_preview_logo.setStyleSheet(f"color: {'#888888' if tema.modo_actual == 'oscuro' else '#7f8c8d'}; font-style: italic;")

    def mostrar_miniatura_firma(self, path):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            pix_scaled = pix.scaled(self.lbl_preview_firma.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_preview_firma.setPixmap(pix_scaled)
        else:
            self.lbl_preview_firma.setText("[Sin Firma]")
            self.lbl_preview_firma.setStyleSheet(f"color: {'#888888' if tema.modo_actual == 'oscuro' else '#7f8c8d'}; font-style: italic;")

    def cargar_datos_actuales(self):
        db = SessionLocal(); p = db.query(PerfilDoctor).first()
        if p:
            self.in_clinica.setText(p.nombre_clinica or "")
            self.in_doctor.setText(p.nombre_doctor or "")
            
            if hasattr(p, 'genero_doctor') and p.genero_doctor:
                self.combo_genero_doc.setCurrentText(p.genero_doctor)
                
            self.in_cedula.setText(p.cedula_doctor or "")
            self.in_especialidad.setText(p.especialidades or "")
            self.in_msds.setText(p.matricula_msds or "")
            self.in_rif.setText(p.rif_clinica or "")
            self.in_correo.setText(p.correo_doctor or "")
            self.in_direccion.setText(p.direccion_clinica or "")
            
            # Cargar miniaturas guardadas en la base de datos
            if p.logo_ruta: 
                self.logo_path = p.logo_ruta
                self.mostrar_miniatura_logo(p.logo_ruta)
            else:
                self.mostrar_miniatura_logo(None)
                
            if p.firma_ruta: 
                self.firma_path = p.firma_ruta
                self.mostrar_miniatura_firma(p.firma_ruta)
            else:
                self.mostrar_miniatura_firma(None)
        else:
            self.mostrar_miniatura_logo(None)
            self.mostrar_miniatura_firma(None)
        db.close()

    def procesar_archivo_local(self, ruta_nueva, ruta_actual_db, prefijo):
        if not ruta_nueva or ruta_nueva == ruta_actual_db:
            return ruta_actual_db

        try:
            carpeta = "recursos_sistema"
            os.makedirs(carpeta, exist_ok=True)

            ext = os.path.splitext(ruta_nueva)[1]
            nombre_it = f"{prefijo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            ruta_destino = os.path.join(carpeta, nombre_it)

            shutil.copy2(ruta_nueva, ruta_destino)

            if ruta_actual_db and os.path.exists(ruta_actual_db):
                if os.path.abspath(ruta_actual_db) != os.path.abspath(ruta_destino):
                    try:
                        os.remove(ruta_actual_db)
                    except Exception as e:
                        print(f"No se pudo eliminar el recurso antiguo: {e}")

            return ruta_destino
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            return ruta_nueva

    def guardar_perfil(self):
        db = SessionLocal()
        p = db.query(PerfilDoctor).first()
        
        if not p: 
            p = PerfilDoctor()
            db.add(p)

        if hasattr(self, 'logo_path') and self.logo_path:
            p.logo_ruta = self.procesar_archivo_local(self.logo_path, p.logo_ruta, "logo")
        
        if hasattr(self, 'firma_path') and self.firma_path:
            p.firma_ruta = self.procesar_archivo_local(self.firma_path, p.firma_ruta, "firma")

        p.nombre_clinica = self.in_clinica.text()
        p.nombre_doctor = self.in_doctor.text()
        p.genero_doctor = self.combo_genero_doc.currentText()
        p.cedula_doctor = self.in_cedula.text()
        p.especialidades = self.in_especialidad.text()
        p.matricula_msds = self.in_msds.text()
        p.rif_clinica = self.in_rif.text()
        p.correo_doctor = self.in_correo.text()
        p.direccion_clinica = self.in_direccion.text()

        db.commit()
        db.close()
        
        self.logo_path = None
        self.firma_path = None
        
        box = QMessageBox(QMessageBox.Information, "Éxito", "Perfil médico y recursos gráficos actualizados con éxito.", QMessageBox.Ok, self)
        self.actualizar_emergente_parent(box); box.exec()