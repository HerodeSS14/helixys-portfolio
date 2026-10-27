import sys
import json
import ctypes
from PySide6.QtGui import QDesktopServices, QBrush, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QStackedWidget, QFrame, QLabel, QDialog, QMessageBox
)
from ui_dashboard import Dashboard
from ui_pacientes import FichaIdentificacion
from ui_facturacion import PantallaFactura
from ui_consultas import PantallaConsulta
from ui_historial import PantallaHistorial
from ui_perfil import PantallaConfiguracion
from ui_informes import PantallaInforme
from ui_documentos_rapidos import PantallaRecetaRapida, PantallaOrdenRapida
from ui_consentimientos import PantallaConsentimiento
from ui_informe_egreso import PantallaInformeEgreso
from ui_post_operatorio import PantallaPostOperatorio 
from ui_red_local import TabConectividadRed
from ui_rendimientos import PantallaRendimientos
from ui_gastos import PantallaGastos  # <--- MÓDULO DE GASTOS IMPORTADO
from ui_login import PantallaLogin 
from migrar import ejecutar_migraciones_automaticas
from motor_voz import ManejadorVozUniversal

# Modificamos los imports de database para usar las funciones dinámicas de control
import database
from database import engine, Base, SessionLocal

from models import Base, Usuario 
import bcrypt
from estilos import tema  # Importación del motor de diseño centralizado


def inicializar_usuarios():
    """Crea los usuarios por defecto si la base de datos está vacía"""
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            
            # Cuenta del Doctor
            hash_doc = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.add(Usuario(username="doctor", password_hash=hash_doc, rol="principal"))
            
            # Cuenta de la Secretaria / Asistente
            hash_sec = bcrypt.hashpw("12345".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.add(Usuario(username="secretaria", password_hash=hash_sec, rol="secundaria"))
            
            db.commit()
            
    except Exception as e:
        print(f"❌ Error al inicializar usuarios base: {e}")
    finally:
        db.close()

class VentanaPrincipal(QMainWindow):
    def __init__(self, rol_usuario="principal"):
        super().__init__()
        self.rol_usuario = rol_usuario
        self.setWindowTitle("Helixys")
        self.setMinimumSize(1250, 850)
        self.setWindowIcon(QIcon("icono.ico"))
        
        # Seteo de estilo base para la ventana principal
        self.setStyleSheet(tema.ESTILO_VENTANA)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setStyleSheet("background: transparent;") 
        main_layout = QHBoxLayout(main_widget)
        
        # --- MENÚ LATERAL ---
        self.menu = QFrame()
        self.menu.setFixedWidth(230)
        self.menu.setStyleSheet("background-color: #202225; border: none;") # Fondo lateral oscuro
        menu_layout = QVBoxLayout(self.menu)
        menu_layout.setContentsMargins(15, 20, 15, 20)
        menu_layout.setSpacing(12)

        # TÍTULO DEL MENÚ LATERAL
        lbl_menu = QLabel("🏥 MENÚ")
        lbl_menu.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 18px; margin-bottom: 15px; margin-left: 5px; background: transparent;")
        menu_layout.addWidget(lbl_menu)

        # CREACIÓN DE BOTONES CLÍNICOS PRINCIPALES
        self.btn_dash = QPushButton("   🏠 Inicio")
        self.btn_reg = QPushButton("   📝 Registro")
        self.btn_hist = QPushButton("   🗄️ Historial / Archivos")
        self.btn_rendimientos = QPushButton("   📈 Rendimientos")
        self.btn_gastos = QPushButton("   💸 Gastos Mensuales")  # <--- BOTÓN DE GASTOS

        self.botones_clinicos = [
            self.btn_dash, self.btn_reg, self.btn_hist, 
            self.btn_rendimientos, self.btn_gastos
        ]

        # Estilo premium visible y redondeado para los botones del menú
        for b in self.botones_clinicos:
            b.setStyleSheet("""
                QPushButton {
                    color: #ffffff; 
                    background-color: #2f3136;
                    padding: 12px; 
                    text-align: left; 
                    border: 1px solid #4f545c; 
                    border-radius: 8px;
                    font-weight: bold; 
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #74C9B9;
                    color: #1C1C1C;
                    border-color: #74C9B9;
                }
            """)
            menu_layout.addWidget(b)
        
        # Empuja los botones clínicos hacia arriba y deja el bloque técnico abajo
        menu_layout.addStretch()

        # 1) BOTÓN DE MODO OSCURO (Al final del stretch)
        self.btn_modo_oscuro = QPushButton("🌙 Modo Oscuro")
        self.btn_modo_oscuro.setStyleSheet("""
            QPushButton {
                color: #ffffff; 
                padding: 12px; 
                text-align: center; 
                border: none; 
                border-radius: 6px;
                font-weight: bold; 
                font-size: 13px; 
                background-color: #424549;
            }
            QPushButton:hover { background-color: #4f545c; }
        """)
        self.btn_modo_oscuro.clicked.connect(self.alternar_tema)
        menu_layout.addWidget(self.btn_modo_oscuro)

        # 2) BOTÓN DE SINCRONIZAR RED
        self.btn_red_local = QPushButton("        🌐 Sincronizar Red") 
        self.btn_red_local.setStyleSheet("""
            QPushButton {
                color: #ffffff; 
                background-color: #2f3136;
                padding: 12px; 
                text-align: left; 
                border: 1px solid #4f545c; 
                border-radius: 8px;
                font-weight: bold; 
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #74C9B9;
                color: #1C1C1C;
                border-color: #74C9B9;
            }
        """)
        menu_layout.addWidget(self.btn_red_local)

        # 3) BOTÓN DE CONFIGURACIÓN
        self.btn_conf = QPushButton("⚙️ Configuración")
        self.btn_conf.setStyleSheet("""
            QPushButton {
                color: #ffffff; 
                padding: 12px; 
                text-align: center; 
                border: none; 
                border-radius: 6px;
                font-weight: bold; 
                font-size: 13px; 
                background-color: #2f3136;
                border: 1px solid #4f545c;
            }
            QPushButton:hover { background-color: #e67e22; color: white; border-color: #e67e22; }
        """)
        menu_layout.addWidget(self.btn_conf)

        # =================================================================
        # --- INSTANCIAS DE LAS PANTALLAS CON FILTRO DE ROLES ---
        # =================================================================
        
        # 1. Instancias de las pantallas clínicas universales
        self.view_dashboard = Dashboard()
        self.view_registro = FichaIdentificacion()
        self.view_red_local = TabConectividadRed() 
        self.view_consulta = PantallaConsulta()
        self.view_historial = PantallaHistorial()
        self.pantalla_informes = PantallaInforme() 
        self.pantalla_consentimiento = PantallaConsentimiento()
        self.pantalla_receta_rapida = PantallaRecetaRapida() 
        self.pantalla_orden_rapida = PantallaOrdenRapida()   
        self.pantalla_egreso = PantallaInformeEgreso()
        self.pantalla_postop = PantallaPostOperatorio()
        self.pantalla_facturas = PantallaFactura()

        # 2. Control de acceso restringido para el rol de Secretaria/Asistente
        if self.rol_usuario == "secundaria":
            
            self.btn_conf.hide()
            self.btn_rendimientos.hide()
            self.btn_gastos.hide()
            
            self.view_config = None
            self.pantalla_rendimientos = None
            self.pantalla_gastos = None
        else:
            self.view_config = PantallaConfiguracion() 
            self.pantalla_rendimientos = PantallaRendimientos()
            self.pantalla_gastos = PantallaGastos()


        # =================================================================
        # --- EL PUENTE (CONEXIÓN DE SEÑALES PROTEGIDA) ---
        # =================================================================
        self.view_registro.paciente_registrado.connect(self.view_dashboard.cargar_espera)
        self.view_registro.paciente_registrado.connect(self.view_dashboard.cargar_citas)
        self.view_registro.paciente_registrado.connect(self.view_registro.actualizar_tabla)
        self.view_registro.paciente_registrado.connect(self.view_historial.actualizar_lista)
        
        # Conexiones de flujo clínico general
        self.view_historial.solicitar_consulta.connect(self.abrir_consulta)
        self.view_historial.solicitar_informe.connect(self.abrir_redaccion_informe)
        self.view_historial.solicitar_consentimiento.connect(self.abrir_consentimiento)
        self.view_historial.solicitar_receta_rapida.connect(self.abrir_receta_rapida) 
        self.view_historial.solicitar_orden_rapida.connect(self.abrir_orden_rapida)   
        self.view_historial.solicitar_factura.connect(self.abrir_modulo_facturacion)
        self.view_consulta.solicitar_informe.connect(self.abrir_redaccion_informe)
        self.view_dashboard.solicitar_informe_signal.connect(self.abrir_redaccion_informe)
        self.pantalla_consentimiento.solicitar_historial.connect(self.abrir_historial) 
        self.pantalla_receta_rapida.volver_historial.connect(self.abrir_historial) 
        self.pantalla_orden_rapida.volver_historial.connect(self.abrir_historial)  
        self.view_dashboard.iniciar_consulta_signal.connect(self.abrir_consulta)
        self.view_dashboard.solicitar_factura_signal.connect(self.abrir_modulo_facturacion)
        self.view_historial.solicitar_egreso.connect(self.abrir_egreso)
        self.pantalla_egreso.volver_historial.connect(self.abrir_historial)
        self.view_historial.solicitar_post_op.connect(self.abrir_postop)
        self.pantalla_postop.volver_historial.connect(self.abrir_historial)
        
        if self.view_config:
            self.view_config.paciente_eliminado.connect(self.view_registro.actualizar_tabla)
            self.view_config.paciente_eliminado.connect(self.view_historial.actualizar_lista)


        # =================================================================
        # --- CONTENEDOR DE PANTALLAS (STACK INTEGRAL DINÁMICO) ---
        # =================================================================
        self.stack = QStackedWidget()
        
        self.stack.addWidget(self.view_dashboard)          # Índice 0
        self.stack.addWidget(self.view_registro)           # Índice 1
        self.stack.addWidget(self.view_consulta)           # Índice 2
        self.stack.addWidget(self.view_historial)          # Índice 3
        
        # Índice 4 (Configuración)
        if self.view_config:
            self.stack.addWidget(self.view_config)
        else:
            self.stack.addWidget(QWidget())                # Marcador de posición
            
        self.stack.addWidget(self.pantalla_informes)       # Índice 5 
        self.stack.addWidget(self.pantalla_consentimiento) # Índice 6 
        self.stack.addWidget(self.pantalla_receta_rapida)  # Índice 7
        self.stack.addWidget(self.pantalla_orden_rapida)   # Índice 8
        self.stack.addWidget(self.pantalla_egreso)         # Índice 9
        self.stack.addWidget(self.pantalla_postop)         # Índice 10
        self.stack.addWidget(self.pantalla_facturas)       # Índice 11
        self.stack.addWidget(self.view_red_local)          # Índice 12
        
        # Índice 13 (Rendimientos)
        if self.pantalla_rendimientos:
            self.stack.addWidget(self.pantalla_rendimientos)
        else:
            self.stack.addWidget(QWidget())                # Marcador de posición
            
        # Índice 14 (Gastos)
        if self.pantalla_gastos:
            self.stack.addWidget(self.pantalla_gastos)
        else:
            self.stack.addWidget(QWidget())                # Marcador de posición

        main_layout.addWidget(self.menu)
        main_layout.addWidget(self.stack)

        # --- NAVEGACIÓN MENÚ LATERAL ---
        self.btn_dash.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_reg.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_hist.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        self.btn_red_local.clicked.connect(lambda: self.stack.setCurrentIndex(12)) 
        
        if self.rol_usuario != "secundaria":
            self.btn_conf.clicked.connect(lambda: self.stack.setCurrentIndex(4))
            self.btn_rendimientos.clicked.connect(lambda: self.stack.setCurrentIndex(13))
            self.btn_gastos.clicked.connect(lambda: self.stack.setCurrentIndex(14))

    # LÓGICA DE MUTACIÓN DE COLORES DINÁMICOS EN TIEMPO REAL
    def alternar_tema(self):
        if tema.modo_actual == "claro":
            tema.configurar_modo_oscuro()
            self.btn_modo_oscuro.setText("☀️ Modo Claro")
            self.btn_modo_oscuro.setStyleSheet("""
                QPushButton { color: white; padding: 12px; text-align: center; border: none; border-radius: 6px; font-weight: bold; font-size: 13px; background-color: #7289da; }
                QPushButton:hover { background-color: #5b73c7; }
            """)
        else:
            tema.configurar_modo_claro()
            self.btn_modo_oscuro.setText("🌙 Modo Oscuro")
            self.btn_modo_oscuro.setStyleSheet("""
                QPushButton { color: white; padding: 12px; text-align: center; border: none; border-radius: 6px; font-weight: bold; font-size: 13px; background-color: #424549; }
                QPushButton:hover { background-color: #4f545c; }
            """)
        
        self.setStyleSheet(tema.ESTILO_VENTANA)
        
        # Re-aplicar de manera forzada las hojas de estilo corregidas sobre las pantallas activas
        estilo_recalc = f"""
            QWidget {{ background: transparent; color: {tema.TEXTO_MAIN}; }}
            QFrame {{ background-color: {tema.BG_TARJETA}; border: 1px solid {tema.BORDE_SUAVE}; }}
            QLineEdit, QTextEdit, QTableWidget {{ background-color: {tema.BG_INPUT}; color: {tema.TEXTO_MAIN}; border: 1px solid {tema.BORDE_SUAVE}; }}
            QLabel {{ color: {tema.TEXTO_MAIN}; border: none; background: transparent; }}
            QGroupBox {{ color: {tema.TEXTO_MAIN}; }}
        """
        
        self.stack.setStyleSheet(estilo_recalc)
        
        self.view_registro.actualizar_tabla()
        if self.view_historial:
            self.view_historial.actualizar_tabla_archivos()

    # --- FUNCIONES DE REDIRECCIÓN ---
    def abrir_consulta(self, paciente_id):
        if self.view_consulta:
            self.view_consulta.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(2)

    def abrir_redaccion_informe(self, paciente_id):
        if self.pantalla_informes:
            self.pantalla_informes.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(5) 

    def abrir_consentimiento(self, paciente_id):
        if self.pantalla_consentimiento:
            self.pantalla_consentimiento.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(6)
        
    def abrir_receta_rapida(self, paciente_id):
        if self.pantalla_receta_rapida:
            self.pantalla_receta_rapida.cargar_datos(paciente_id)
            self.stack.setCurrentIndex(7)
        
    def abrir_orden_rapida(self, paciente_id):
        if self.pantalla_orden_rapida:
            self.pantalla_orden_rapida.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(8)

    def abrir_historial(self):
        if self.view_historial:
            self.view_historial.actualizar_tabla_archivos()
            self.stack.setCurrentIndex(3)

    def abrir_egreso(self, paciente_id):
        if self.pantalla_egreso:
            self.pantalla_egreso.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(9)

    def abrir_postop(self, paciente_id):
        if self.pantalla_postop:
            self.pantalla_postop.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(10)

    def abrir_modulo_facturacion(self, paciente_id):
        if self.pantalla_facturas:
            self.pantalla_facturas.cargar_datos_paciente(paciente_id)
            self.stack.setCurrentIndex(11)


# =====================================================================
# INTERCEPCIÓN EN CALIENTE DE LA CONEXIÓN ANTES DEL LOGIN
# =====================================================================
def orquestar_enlace_red_local():
    """ 
    Fuerza el escaneo si database.py levantó RAM por falta de PostgreSQL central.
    Envuelve la ventana ui_red_local en un Diálogo modal cerrado.
    """
    if database.es_conexion_valida():
        try:
            Base.metadata.create_all(bind=database.engine)
        except Exception as e:
            print(f"Error mapeando base de datos guardada: {e}")
        return True

    QMessageBox.information(
        None,
        "Configuración de Red Requerida",
        "No se detectó el servidor central de historias médicas PostgreSQL.\n\n"
        "Se abrirá de forma automática el módulo para escanear y enlazar la base de datos."
    )

    dialogo = QDialog()
    dialogo.setWindowTitle("Buscador de Servidor Central Médico")
    dialogo.setMinimumSize(700, 500)
    lay_diag = QVBoxLayout(dialogo)

    componente_red = TabConectividadRed()
    lay_diag.addWidget(componente_red)

    def verificar_y_cerrar():
        if database.es_conexion_valida():
            dialogo.accept()

    btn_confirmar = QPushButton("Finalizar y Volver al Login")
    btn_confirmar.setStyleSheet("background-color: #74C9B9; color: #1C1C1C; font-weight: bold; padding: 10px; border-radius: 5px;")
    btn_confirmar.clicked.connect(verificar_y_cerrar)
    lay_diag.addWidget(btn_confirmar)

    if dialogo.exec() != QDialog.Accepted or not database.es_conexion_valida():
        QMessageBox.critical(
            None,
            "Error de Inicio",
            "El sistema no puede iniciar sesión sin estar conectado a la base de datos central PostgreSQL.\nLa aplicación se cerrará."
        )
        return False

    try:
        Base.metadata.create_all(bind=database.engine)
        try:
            with open(database.RUTA_CONFIG_RED, "w", encoding="utf-8") as f:
                json.dump({"ip_servidor": database.host}, f, indent=4)
            
        except Exception as json_err:
            print(f"No se pudo escribir archivo config_red.json: {json_err}")
            
        return True
    except Exception as e:
        QMessageBox.critical(None, "Error de Mapeo", f"No se pudo estructurar el esquema en el servidor central:\n{e}")
        return False


if __name__ == "__main__":
    
    try:
        myappid = 'HelixysCorp.MedicalSystem.Main.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    except Exception as e:
        print(f"⚠️ No se pudo registrar el AppUserModelID: {e}")

    ejecutar_migraciones_automaticas()
    app = QApplication(sys.argv)
    
    # 1. Ejecutamos la intercepción inteligente de red local
    if not orquestar_enlace_red_local():
        sys.exit(0)
        
    # 2. Una vez enlazados al PostgreSQL remoto, creamos las cuentas base si está vacío
    inicializar_usuarios()
    
    # 3. Flujo de renderizado de la aplicación y autenticación
    login = PantallaLogin()
    login.setWindowIcon(QIcon("icono.ico")) 
    
    window = None

    def al_login_exitoso(rol_obtenido):
        global window
        login.close()  # Cerramos la ventana de login
        
        # Instanciamos la VentanaPrincipal con el rol asignado
        window = VentanaPrincipal(rol_usuario=rol_obtenido) 
        window.show()
        
        # 🟢 CONEXIÓN DEL MOTOR DE VOZ
        manejador_voz = ManejadorVozUniversal(app, window.stack)
        app.manejador_voz = manejador_voz
        app.installEventFilter(manejador_voz)

    login.login_exitoso.connect(al_login_exitoso)
    login.show()
    
    sys.exit(app.exec())