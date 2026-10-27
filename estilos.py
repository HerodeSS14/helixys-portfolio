# estilos.py
import os
import winsound
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont

class GestorTemas(QObject):
    tema_cambiado = Signal()

    def __init__(self):
        super().__init__()
        # 🎨 TUS COLORES FAVORITOS BASE
        self.MENTA_MEDICA = "#74C9B9"
        self.MENTA_HOVER  = "#5BB3A3"  
        self.MENTA_FOCUS  = "rgba(116, 201, 185, 0.2)"
        self.CARBONO      = "#1C1C1C"
        self.FUENTES_CAMPOS = QFont("Arial", 10)
        # 🧠 PALETA SEMÁNTICA CON PERSONALIDAD PARA BOTONES
        self.AZUL_INFORME       = "#3498DB"  
        self.AZUL_INFORME_HOVER = "#2980B9"
        
        self.MORADO_ORDEN       = "#9B59B6"  
        self.MORADO_ORDEN_HOVER = "#8E44AD"
        
        self.ROJO_PELIGRO       = "#F43F5E"  
        self.ROJO_PELIGRO_HOVER = "#E11D48"

        self.configurar_modo_claro()

    def reproducir_alerta_notificacion(self):
        # 🔊 REPRODUCCIÓN DE TU PROPIO ARCHIVO DE AUDIO (DEBE SER REQUERIDO EN .WAV)
        # 📌 NOTA: Asegúrate de guardar tu sonido como 'notificacion.wav' junto a este archivo
        ruta_sonido = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notificacion.wav")
        
        try:
            if os.path.exists(ruta_sonido):
                # Ejecuta tu sonido personalizado sin congelar la interfaz (ASYNC)
                winsound.PlaySound(ruta_sonido, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # Sonido de respaldo del sistema si el archivo no existe en la carpeta
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception as e:
            print(f"[AUDIO ERROR] No se pudo reproducir el sonido: {e}")

    def configurar_modo_claro(self):
        self.modo_actual = "claro"
        self.BG_PRINCIPAL  = "#F8FAFC"  
        self.BG_TARJETA    = "#FFFFFF"  
        self.BG_INPUT      = "#FFFFFF"
        self.BG_SCROLLBAR  = "#282b30"
        
        self.TEXTO_MAIN    = "#1C1C1C"  
        self.TEXTO_MUTED   = "#64748B"  
        self.BORDE_SUAVE   = "#CBD5E1"  
        
        self.COLOR_DIVISION_TABLA = "#36393e" 
        self.COLOR_SCROLLBAR      = "#36393e" 
        
        self.BG_GROUP_DISABLED = "#E2E8F0" 
        self.BG_GROUP_ENABLED  = "#FFFFFF"
        
        self.tema_cambiado.emit()

    def configurar_modo_oscuro(self):
        self.modo_actual = "oscuro"
        
        self.BG_PRINCIPAL  = "#282b30"  
        self.BG_TARJETA    = "#36393e"  
        self.BG_INPUT      = "#424549"  
        self.BORDE_SUAVE   = "#4f545c"  
        
        self.TEXTO_MAIN    = "#FFFFFF"  
        self.TEXTO_MUTED   = "#b9bbbe"  
        
        self.COLOR_DIVISION_TABLA = "#93F6E3" 
        self.COLOR_SCROLLBAR      = "#93F6E3" 

        self.BG_GROUP_DISABLED = "#2f3136"
        self.BG_GROUP_ENABLED  = "#424549"
        
        self.tema_cambiado.emit()

    # =========================================================================
    # VISTAS GENERALES CON CONTRASTE Y CONTROLES ADAPTABLES
    # =========================================================================
    @property
    def ESTILO_VENTANA(self):
        estilo_base = f"background-color: {self.BG_PRINCIPAL};"
        
        estilo_tablas_y_scrollbars = f"""
            QTableWidget, QTreeView {{
                gridline-color: {self.COLOR_DIVISION_TABLA};
                border: 1px solid {self.BORDE_SUAVE};
                font-size: 13px;
                alternate-background-color: {'#2f3136' if self.modo_actual == "oscuro" else '#F1F5F9'};
            }}
            
            QHeaderView::section {{
                background-color: #93F6E3;
                color: #1C1C1C;
                font-weight: bold;
                padding: 6px;
                border: 1px solid {self.BORDE_SUAVE};
            }}
            
            QMessageBox, QDialog, QInputDialog {{
                background-color: {self.BG_TARJETA};
            }}
            QMessageBox QLabel, QDialog QLabel, QInputDialog QLabel {{
                color: {self.TEXTO_MAIN};
                font-size: 14px;
            }}
            QMessageBox QPushButton, QDialog QPushButton, QInputDialog QPushButton {{
                background-color: {self.BG_INPUT};
                color: {self.TEXTO_MAIN};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 4px;
                padding: 5px 15px;
                min-width: 70px;
            }}
            QMessageBox QPushButton:hover, QDialog QPushButton:hover, QInputDialog QPushButton:hover {{
                background-color: {self.MENTA_MEDICA};
                color: #1C1C1C;
            }}
            
            QScrollBar:vertical {{
                background: transparent;
                width: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.COLOR_SCROLLBAR};
                min-height: 30px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.MENTA_HOVER if self.modo_actual == "oscuro" else "#475569"};
            }}
            
            QScrollBar:horizontal {{
                background: transparent;
                height: 14px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {self.COLOR_SCROLLBAR};
                min-width: 30px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.MENTA_HOVER if self.modo_actual == "oscuro" else "#475569"};
            }}
            
            QScrollBar::add-line, QScrollBar::sub-line,
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
                border: none;
            }}

            QMenu {{
                background-color: {self.BG_TARJETA};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {self.TEXTO_MAIN};
                padding: 10px 16px;
                margin: 3px 0px;
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.4;
            }}
            QMenu::item:selected {{
                background-color: {self.MENTA_MEDICA};
                color: #1C1C1C;
                font-weight: bold;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self.BORDE_SUAVE};
                margin: 6px 8px;
            }} 
        """
        return estilo_base + estilo_tablas_y_scrollbars

    @property
    def ESTILO_TARJETA(self):
        return f"""
            QFrame {{
                background-color: {self.BG_TARJETA};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 8px;
            }}
            QMessageBox, QDialog, QInputDialog, QWidget {{
                background-color: {self.BG_TARJETA};
                color: {self.TEXTO_MAIN};
            }}
            QMessageBox QLabel, QDialog QLabel, QInputDialog QLabel, QLabel {{
                color: {self.TEXTO_MAIN};
            }}
            QMessageBox QPushButton, QDialog QPushButton, QInputDialog QPushButton {{
                background-color: {self.BG_INPUT};
                color: {self.TEXTO_MAIN};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 4px;
                padding: 6px 18px;
                min-width: 75px;
                font-weight: bold;
            }}
            QMessageBox QPushButton:hover, QDialog QPushButton:hover, QInputDialog QPushButton:hover {{
                background-color: {self.MENTA_MEDICA};
                color: #1C1C1C;
            }}
        """

    @property
    def ESTILO_ENTRY_MODERNO(self):
        return f"""
            QLineEdit, QTextEdit {{
                background-color: {self.BG_INPUT};
                color: {self.TEXTO_MAIN};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {self.MENTA_MEDICA};
                background-color: {self.BG_INPUT};
            }}
        """

    @property
    def ESTILO_LABEL_TITULO(self):
        return f"font-size: 18px; font-weight: bold; color: {self.TEXTO_MAIN}; border: none; background: transparent;"

    @property
    def ESTILO_LABEL_DATO(self):
        return f"font-size: 14px; font-weight: bold; color: {self.TEXTO_MUTED}; border: none; background: transparent;"

    @property
    def ESTILO_BTN_PRIMARIO(self):
        return f"""
            QPushButton {{
                background-color: {self.MENTA_MEDICA};
                color: #1C1C1C;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 10px 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.MENTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #459E8E;
            }}
        """

    @property
    def ESTILO_BTN_INFORME(self):
        return f"""
            QPushButton {{
                background-color: {self.AZUL_INFORME};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 10px 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.AZUL_INFORME_HOVER};
            }}
        """

    @property
    def ESTILO_BTN_RECIPE(self):
        return f"""
            QPushButton {{
                background-color: {self.CARBONO};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 10px 20px;
                border: 1px solid {self.BORDE_SUAVE};
            }}
            QPushButton:hover {{
                background-color: #333333;
                border-color: {self.MENTA_MEDICA};
            }}
        """

    @property
    def ESTILO_BTN_ORDEN(self):
        return f"""
            QPushButton {{
                background-color: {self.MORADO_ORDEN};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
                padding: 10px 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.MORADO_ORDEN_HOVER};
            }}
        """

    @property
    def ESTILO_BTN_SECUNDARIO(self):
        return f"""
            QPushButton {{
                background-color: {self.BG_TARJETA};
                color: {self.TEXTO_MAIN};
                border: 1px solid {self.BORDE_SUAVE};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.BG_PRINCIPAL};
                border-color: {self.MENTA_MEDICA};
            }}
        """

    @property
    def ESTILO_BTN_PELIGRO(self):
        return f"""
            QPushButton {{
                background-color: {self.ROJO_PELIGRO};
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.ROJO_PELIGRO_HOVER};
            }}
        """

tema = GestorTemas()