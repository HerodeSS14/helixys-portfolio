from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect,
                               QDialog, QStackedWidget, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap
import bcrypt
import os
import json
from database import SessionLocal
import database # Importación completa para acceder al host y rutas
from models import Usuario

# =====================================================================
# FUNCIONES DE AYUDA PARA RECUPERACIÓN
# =====================================================================
def buscar_usuario_principal():
    """Busca al doctor (usuario principal) directamente si se olvidó el usuario"""
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.rol == "principal").first()
    nombre_usuario = usuario.username if usuario else None
    db.close()
    return nombre_usuario

def obtener_preguntas_usuario(username):
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    preguntas = None
    if usuario and usuario.pregunta_seguridad_1 and usuario.pregunta_seguridad_2:
        preguntas = (usuario.pregunta_seguridad_1, usuario.pregunta_seguridad_2)
    db.close()
    return preguntas

def validar_respuesta_seguridad(username, numero_pregunta, respuesta_intento):
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    db.close()
    if not usuario: return False
    
    respuesta_limpia = respuesta_intento.strip().lower().encode('utf-8')
    if numero_pregunta == 1 and usuario.respuesta_hash_1:
        return bcrypt.checkpw(respuesta_limpia, usuario.respuesta_hash_1.encode('utf-8'))
    elif numero_pregunta == 2 and usuario.respuesta_hash_2:
        return bcrypt.checkpw(respuesta_limpia, usuario.respuesta_hash_2.encode('utf-8'))
    return False

def validar_codigo_maestro(username, codigo_intento):
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    db.close()
    if not usuario or not usuario.codigo_maestro_hash: return False
    return bcrypt.checkpw(codigo_intento.strip().encode('utf-8'), usuario.codigo_maestro_hash.encode('utf-8'))

def restablecer_cuenta_completa(username_actual, nuevo_username, nueva_pass):
    """Permite reiniciar tanto el usuario como la contraseña de forma segura"""
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.username == username_actual).first()
    exito = False
    if usuario:
        try:
            usuario.username = nuevo_username.strip()
            usuario.password_hash = bcrypt.hashpw(nueva_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.commit()
            exito = True
        except Exception:
            db.rollback()
            exito = False
    db.close()
    return exito


# =====================================================================
# DIÁLOGO DE RECUPERACIÓN DE CUENTA (ASISTENTE MEJORADO)
# =====================================================================
class DialogoRecuperacion(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asistente de Recuperación de Acceso")
        self.setFixedSize(420, 380)
        self.usuario_objetivo = None

        self.setStyleSheet("""
            QDialog { background-color: #2F3136; color: #FFFFFF; font-family: 'Segoe UI'; }
            QLabel { color: #FFFFFF; font-size: 13px; }
            QLineEdit { background-color: #202225; border: 1px solid #4F545C; border-radius: 5px; padding: 8px; color: #FFFFFF; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #74C9B9; }
            QPushButton { background-color: #7289DA; color: white; border: none; border-radius: 5px; padding: 10px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #5B73C7; }
            QPushButton#btn_peligro { background-color: #F04747; }
            QPushButton#btn_peligro:hover { background-color: #D83C3C; }
            QPushButton#btn_enlace { background: transparent; color: #74C9B9; text-decoration: underline; padding: 2px; text-align: left; }
            QPushButton#btn_enlace:hover { color: #93F6E3; }
        """)

        layout = QVBoxLayout(self)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # PAGINA 0: Pedir Usuario
        self.page_user = QWidget()
        lay_user = QVBoxLayout(self.page_user)
        lay_user.setSpacing(12)
        lay_user.addWidget(QLabel("<b>Paso 1: Identificación de la Cuenta</b>\nIngrese su nombre de usuario para comenzar."))
        
        self.in_user_rec = QLineEdit(placeholderText="Nombre de usuario")
        lay_user.addWidget(self.in_user_rec)
        
        self.btn_olvido_usuario = QPushButton("¿Olvidó su nombre de usuario? Recuperar usando sus preguntas o código")
        self.btn_olvido_usuario.setObjectName("btn_enlace")
        self.btn_olvido_usuario.setCursor(Qt.PointingHandCursor)
        self.btn_olvido_usuario.clicked.connect(self.recuperar_usuario_anonimo)
        lay_user.addWidget(self.btn_olvido_usuario)
        
        btn_buscar_user = QPushButton("Siguiente")
        btn_buscar_user.clicked.connect(self.buscar_usuario)
        lay_user.addStretch()
        lay_user.addWidget(btn_buscar_user)

        # PAGINA 1: Elegir Método (Preguntas o Código Maestro)
        self.page_metodo = QWidget()
        lay_metodo = QVBoxLayout(self.page_metodo)
        lay_metodo.setSpacing(15)
        lay_metodo.addWidget(QLabel("<b>Paso 2: Selección de Método</b>\nElija cómo desea validar su identidad:"))
        
        self.btn_metodo_preg = QPushButton("Verificar por Preguntas de Seguridad")
        self.btn_metodo_cod = QPushButton("Verificar por Código Maestro de Emergencia")
        
        self.btn_metodo_preg.clicked.connect(self.preparar_preguntas)
        self.btn_metodo_cod.clicked.connect(self.preparar_pantalla_codigo)
        
        lay_metodo.addWidget(self.btn_metodo_preg)
        lay_metodo.addWidget(self.btn_metodo_cod)
        lay_metodo.addStretch()

        # PAGINA 2: Preguntas de Seguridad
        self.page_preg = QWidget()
        lay_preg = QVBoxLayout(self.page_preg)
        lay_preg.setSpacing(8)
        self.lbl_preg1 = QLabel("")
        self.in_resp1_rec = QLineEdit(placeholderText="Respuesta 1")
        self.lbl_preg2 = QLabel("")
        self.in_resp2_rec = QLineEdit(placeholderText="Respuesta 2")
        btn_verificar_preg = QPushButton("Validar Respuestas")
        btn_verificar_preg.clicked.connect(self.verificar_preguntas)
        lay_preg.addWidget(self.lbl_preg1)
        lay_preg.addWidget(self.in_resp1_rec)
        lay_preg.addWidget(self.lbl_preg2)
        lay_preg.addWidget(self.in_resp2_rec)
        lay_preg.addStretch()
        lay_preg.addWidget(btn_verificar_preg)

        # PAGINA 3: Código Maestro (Único campo reutilizable con formateador blindado)
        self.page_cod = QWidget()
        lay_cod = QVBoxLayout(self.page_cod)
        lay_cod.setSpacing(10)
        lay_cod.addWidget(QLabel("<b>Validación de Emergencia Nivel 2</b>\nIngrese su Código Maestro:"))
        
        self.in_cod_rec = QLineEdit(placeholderText="XXXX-XXXX-XXXX")
        self.in_cod_rec.textChanged.connect(self.formatear_codigo_maestro_entry)
        
        btn_verificar_cod = QPushButton("Verificar Código de Seguridad")
        btn_verificar_cod.clicked.connect(self.verificar_codigo)
        lay_cod.addWidget(self.in_cod_rec)
        lay_cod.addStretch()
        lay_cod.addWidget(btn_verificar_cod)

        # PAGINA 4: Reiniciar Datos de la Cuenta (Usuario y Password Simultáneos)
        self.page_nueva = QWidget()
        lay_nueva = QVBoxLayout(self.page_nueva)
        lay_nueva.setSpacing(10)
        lay_nueva.addWidget(QLabel("<b>Paso 3: Reinicio de Credenciales</b>\nEstablezca los nuevos accesos para ingresar al sistema:"))
        
        self.in_nuevo_user_rec = QLineEdit(placeholderText="Nuevo Nombre de Usuario")
        self.in_nueva_pass = QLineEdit(placeholderText="Nueva Contraseña")
        self.in_nueva_pass.setEchoMode(QLineEdit.Password)
        
        btn_guardar_nueva = QPushButton("Guardar Cambios y Acceder")
        btn_guardar_nueva.setObjectName("btn_peligro")
        btn_guardar_nueva.clicked.connect(self.guardar_reinicio_cuenta)
        
        lay_nueva.addWidget(QLabel("Nombre de Usuario:"))
        lay_nueva.addWidget(self.in_nuevo_user_rec)
        lay_nueva.addWidget(QLabel("Contraseña Nueva:"))
        lay_nueva.addWidget(self.in_nueva_pass)
        lay_nueva.addStretch()
        lay_nueva.addWidget(btn_guardar_nueva)

        self.stack.addWidget(self.page_user)   # 0
        self.stack.addWidget(self.page_metodo) # 1
        self.stack.addWidget(self.page_preg)   # 2
        self.stack.addWidget(self.page_cod)    # 3
        self.stack.addWidget(self.page_nueva)  # 4

    def formatear_codigo_maestro_entry(self, texto):
        """Asegura el formateo estricto a Mayúsculas y Guiones cada 4 caracteres en cualquier flujo"""
        self.in_cod_rec.blockSignals(True)
        limpio = texto.replace("-", "").upper()
        limpio = "".join(c for c in limpio if c.isalnum())[:12]
        bloques = [limpio[i:i+4] for i in range(0, len(limpio), 4)]
        resultado = "-".join(bloques)
        self.in_cod_rec.setText(resultado)
        self.in_cod_rec.blockSignals(False)

    def buscar_usuario(self):
        usuario = self.in_user_rec.text().strip()
        if not usuario:
            QMessageBox.warning(self, "Aviso", "Por favor introduzca un usuario.")
            return
        self.usuario_objetivo = usuario
        self.in_nuevo_user_rec.setText(usuario)
        self.stack.setCurrentIndex(1)

    def recuperar_usuario_anonimo(self):
        usr_doctor = buscar_usuario_principal()
        if not usr_doctor:
            QMessageBox.critical(self, "Error Fatal", "No se detectó un usuario principal registrado en el sistema.")
            return
        self.usuario_objetivo = usr_doctor
        self.in_nuevo_user_rec.setText(usr_doctor)
        self.stack.setCurrentIndex(1)

    def preparar_pantalla_codigo(self):
        """Limpia el campo y redirige con seguridad para forzar el formateador activo"""
        self.in_cod_rec.clear()
        self.stack.setCurrentIndex(3)

    def preparar_preguntas(self):
        preguntas = obtener_preguntas_usuario(self.usuario_objetivo)
        if not preguntas:
            QMessageBox.warning(self, "Error de Configuración", "Esta cuenta no cuenta con preguntas de seguridad parametrizadas.")
            return
        self.lbl_preg1.setText(f"<b>Pregunta 1:</b> {preguntas[0]}")
        self.lbl_preg2.setText(f"<b>Pregunta 2:</b> {preguntas[1]}")
        self.stack.setCurrentIndex(2)

    def verificar_preguntas(self):
        r1 = self.in_resp1_rec.text()
        r2 = self.in_resp2_rec.text()
        if validar_respuesta_seguridad(self.usuario_objetivo, 1, r1) and validar_respuesta_seguridad(self.usuario_objetivo, 2, r2):
            self.stack.setCurrentIndex(4)
        else:
            QMessageBox.critical(self, "Error de Validación", "Las respuestas introducidas no coinciden.")

    def verificar_codigo(self):
        cod = self.in_cod_rec.text().strip()
        if validar_codigo_maestro(self.usuario_objetivo, cod):
            self.stack.setCurrentIndex(4)
        else:
            QMessageBox.critical(self, "Error de Validación", "Código Maestro de Emergencia incorrecto.")

    def guardar_reinicio_cuenta(self):
        nuevo_user = self.in_nuevo_user_rec.text().strip()
        nueva_pass = self.in_nueva_pass.text().strip()
        
        if not nuevo_user or not nueva_pass:
            QMessageBox.warning(self, "Campos Vacíos", "Debe completar el nuevo usuario y la nueva contraseña.")
            return
            
        if len(nueva_pass) < 4:
            QMessageBox.warning(self, "Seguridad Débil", "La contraseña debe poseer al menos 4 caracteres.")
            return
            
        if restablecer_cuenta_completa(self.usuario_objetivo, nuevo_user, nueva_pass):
            QMessageBox.information(self, "Reinicio Exitoso", "Los datos de su cuenta se actualizaron de forma transparente.\nInicie sesión con sus nuevas credenciales.")
            self.accept()
        else:
            QMessageBox.critical(self, "Fallo Técnico", "El nombre de usuario podría estar en uso por otro rol. Intente con otro.")


# =====================================================================
# PANTALLA PRINCIPAL DE LOGIN
# =====================================================================
class PantallaLogin(QWidget):
    login_exitoso = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Helixys - Acceso al Sistema")
        self.setFixedSize(450, 580)
        self.setWindowIcon(QIcon("icono.ico"))
        
        self.setStyleSheet("""
            QWidget { background-color: #202225; font-family: 'Segoe UI', Arial, sans-serif; }
            QLabel { color: #FFFFFF; }
            QLineEdit { background-color: #2F3136; border: 2px solid #4F545C; border-radius: 8px; padding: 10px; color: #FFFFFF; font-size: 14px; }
            QLineEdit:focus { border: 2px solid #74C9B9; }
            
            /* Bloque de estilo estricto para el Botón de Acceso (Evita transparencias por herencia) */
            QPushButton#btn_acceder_sistema { 
                background-color: #74C9B9; 
                color: #1C1C1C; 
                border: 2px solid #7289DA; 
                border-radius: 8px; 
                padding: 12px; 
                font-weight: bold; 
                font-size: 15px; 
            }
            QPushButton#btn_acceder_sistema:hover { 
                background-color: #93F6E3; 
                border: 2px solid #74C9B9;
                color: #1C1C1C;
            }
            QPushButton#btn_acceder_sistema:pressed { 
                background-color: #59A89A; 
                border: 2px solid #4E63AA;
                color: #FFFFFF;
            }
            
            QPushButton#btn_recuperar { background: transparent; color: #74C9B9; font-size: 12px; padding: 5px; font-weight: normal; border: none; }
            QPushButton#btn_recuperar:hover { color: #FFFFFF; text-decoration: underline; background: transparent; }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setAlignment(Qt.AlignCenter)

        tarjeta = QFrame()
        tarjeta.setStyleSheet("""
            .QFrame {
                background-color: #2F3136; 
                border-radius: 15px;
            }
        """)
        tarjeta.setFixedSize(380, 520)
        
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(20)
        sombra.setColor(QColor(0, 0, 0, 150))
        sombra.setOffset(0, 5)
        tarjeta.setGraphicsEffect(sombra)

        layout_tarjeta = QVBoxLayout(tarjeta)
        layout_tarjeta.setContentsMargins(30, 25, 30, 30)
        layout_tarjeta.setSpacing(15)

        # --- SECCIÓN INTEGRACIÓN DE LOGOTIPO SUPERIOR ---
        self.lbl_logo_clinica = QLabel()
        self.lbl_logo_clinica.setAlignment(Qt.AlignCenter)
        self.lbl_logo_clinica.setStyleSheet("background: transparent; border: none;")
        
        ruta_logo = "logo_2.png"
        if os.path.exists(ruta_logo):
            pix_logo = QPixmap(ruta_logo)
            pix_scaled = pix_logo.scaled(500, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_logo_clinica.setPixmap(pix_scaled)
        else:
            self.lbl_logo_clinica.setText("➕")
            self.lbl_logo_clinica.setStyleSheet("color: #74C9B9; font-size: 32px; background: transparent;")

        
        
        lbl_sub = QLabel("Inicie sesión para acceder al sistema")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: #B9BBBE; font-size: 13px; background: transparent;")

        self.in_usuario = QLineEdit()
        self.in_usuario.setPlaceholderText("Nombre de Usuario")
        
        self.in_password = QLineEdit()
        self.in_password.setPlaceholderText("Contraseña")
        self.in_password.setEchoMode(QLineEdit.Password)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #F04747; font-size: 12px; font-weight: bold; background: transparent;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.hide()

        btn_acceder = QPushButton("Acceder al Sistema")
        btn_acceder.setObjectName("btn_acceder_sistema")
        btn_acceder.setCursor(Qt.PointingHandCursor)
        btn_acceder.clicked.connect(self.verificar_credenciales)
        self.in_password.returnPressed.connect(self.verificar_credenciales)

        btn_recuperar = QPushButton("¿Olvidó su contraseña o usuario?")
        btn_recuperar.setObjectName("btn_recuperar")
        btn_recuperar.setCursor(Qt.PointingHandCursor)
        btn_recuperar.clicked.connect(self.abrir_recuperacion)

        # MODIFICACIÓN AGREGADA: Botón sutil de engranaje para reconfigurar el servidor local de red
        btn_config_red = QPushButton("⚙️ Configurar Servidor de Red")
        btn_config_red.setObjectName("btn_recuperar") # Comparte el estilo discreto menta sin bordes
        btn_config_red.setCursor(Qt.PointingHandCursor)
        btn_config_red.clicked.connect(self.forzar_reconfiguracion_red_manual)

        # Ensamblaje en orden jerárquico estricto
        layout_tarjeta.addWidget(self.lbl_logo_clinica)
        
        layout_tarjeta.addWidget(lbl_sub)
        layout_tarjeta.addSpacing(5)
        layout_tarjeta.addWidget(self.in_usuario)
        layout_tarjeta.addWidget(self.in_password)
        layout_tarjeta.addWidget(self.lbl_error)
        layout_tarjeta.addStretch()
        layout_tarjeta.addWidget(btn_acceder)
        layout_tarjeta.addWidget(btn_recuperar, 0, Qt.AlignCenter)
        layout_tarjeta.addWidget(btn_config_red, 0, Qt.AlignCenter) # Inyección en la base de la tarjeta

        layout_principal.addWidget(tarjeta)

    def verificar_credenciales(self):
        usuario_txt = self.in_usuario.text().strip()
        password_txt = self.in_password.text().strip()

        if not usuario_txt or not password_txt:
            self.mostrar_error("Por favor, complete ambos campos.")
            return

        db = SessionLocal()
        try:
            usuario = db.query(Usuario).filter(Usuario.username == usuario_txt).first()
            if usuario and usuario.check_password(password_txt):
                self.login_exitoso.emit(usuario.rol)
            else:
                self.mostrar_error("Usuario o contraseña incorrectos.")
        except Exception as e:
            self.mostrar_error(f"Error de BD: {e}")
        finally:
            db.close()

    def mostrar_error(self, mensaje):
        self.lbl_error.setText(mensaje)
        self.lbl_error.show()

    def abrir_recuperacion(self):
        dialogo = DialogoRecuperacion(self)
        dialogo.exec()

    # =====================================================================
    # MODIFICACIÓN AGREGADA: CORRECCIÓN EN CALIENTE MANUAL DESDE LOGIN
    # =====================================================================
    def forzar_reconfiguracion_red_manual(self):
        """ Abre el escáner a petición del usuario para cambiar de servidor PostgreSQL """
        from ui_red_local import TabConectividadRed
        import database
        
        escaner_dialog = QDialog(self)
        escaner_dialog.setWindowTitle("Configuración Manual de Servidor Central")
        escaner_dialog.setMinimumSize(700, 500)
        lay_diag = QVBoxLayout(escaner_dialog)

        componente_red = TabConectividadRed()
        lay_diag.addWidget(componente_red)

        def verificar_y_cerrar():
            if database.es_conexion_valida():
                escaner_dialog.accept()

        btn_confirmar = QPushButton("Finalizar y Volver al Login")
        btn_confirmar.setStyleSheet("background-color: #74C9B9; color: #1C1C1C; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_confirmar.clicked.connect(verificar_y_cerrar)
        lay_diag.addWidget(btn_confirmar)

        if escaner_dialog.exec() == QDialog.Accepted:
            # Si se logró la conexión en caliente con éxito, persistimos los datos
            try:
                with open(database.RUTA_CONFIG_RED, "w", encoding="utf-8") as f:
                    json.dump({"ip_servidor": database.host}, f, indent=4)
                database.inicializar_base_de_datos()
                QMessageBox.information(self, "Servidor Enlazado", f"El sistema se ha conectado exitosamente al servidor: {database.host}")
            except Exception as e:
                print(f"Error al guardar config_red.json: {e}")