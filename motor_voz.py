import sys
import os
import json
import pyaudio
from PySide6.QtCore import QThread, Signal, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QMessageBox, QLabel
from PySide6.QtGui import QTextCursor, QKeyEvent
from vosk import Model, KaldiRecognizer

RUTA_MODELO = "model"

class HiloAudioVosk(QThread):
    transcripcion_parcial = Signal(str)
    transcripcion_final = Signal(str)
    error_senal = Signal(str)

    def __init__(self):
        super().__init__()
        self.activo = False
        self.p = None
        self.stream = None
        
        if not os.path.exists(RUTA_MODELO):
            self.model = None
        else:
            self.model = Model(RUTA_MODELO)

    def run(self):
        if not self.model:
            self.error_senal.emit("No se encontró la carpeta 'model' de Vosk en la raíz del proyecto.")
            return

        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            self.stream.start_stream()
        except Exception as e:
            self.error_senal.emit(f"Error al abrir el micrófono: {str(e)}")
            return

        rec = KaldiRecognizer(self.model, 16000)
        self.activo = True

        while self.activo:
            try:
                data = self.stream.read(2000, exception_on_overflow=False)
                if len(data) == 0:
                    continue
                
                if rec.AcceptWaveform(data):
                    resultado = json.loads(rec.Result())
                    texto = resultado.get("text", "").strip()
                    if texto:
                        self.transcripcion_final.emit(texto + " ")
                        rec.Reset()
                else:
                    parcial = json.loads(rec.PartialResult())
                    texto_parcial = parcial.get("partial", "").strip()
                    if texto_parcial:
                        self.transcripcion_parcial.emit(texto_parcial)
            except Exception as e:
                print(f"Error en lectura de buffer: {e}")
                break

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p:
                self.p.terminate()
        except Exception as e:
            print(f"Error al cerrar audio: {e}")

    def detener(self):
        self.activo = False


class ManejadorVozUniversal(QObject):
    def __init__(self, app_instancia, stacked_widget=None):
        super().__init__()
        self.app = app_instancia
        self.stack = stacked_widget 
        self.hilo_audio = None
        self.grabando = False
        self.widget_objetivo = None
        self.cartel_aviso = None
        self.longitud_parcial_previa = 0 
        self.tecla_presionada = False
        self.bloqueado = False  # 🔒 BANDERA DE BLOQUEO PARA DIÁLOGOS Y VENTANAS FLOTANTES

    def bloquear_voz(self):
        """
        Bloquea la entrada por voz y apaga dictados activos.
        Se ejecuta antes de desplegar QInputDialogs o Modales.
        """
        self.bloqueado = True
        self.tecla_presionada = False
        if self.grabando:
            self.detener_dictado()
        else:
            if self.cartel_aviso:
                self.cartel_aviso.close()

    def desbloquear_voz(self):
        """
        Restablece la escucha de voz tras cerrar los diálogos modales.
        """
        self.bloqueado = False
        self.tecla_presionada = False

    def forzar_detencion(self):
        """
        Alias de seguridad para detener de emergencia la transcripción.
        """
        self.bloquear_voz()

    def eventFilter(self, obj, event):
        # 🔒 SI LA VOZ ESTÁ BLOQUEADA, SE IGNORA TODO EVENTO DE TECLADO/FOCO
        if self.bloqueado:
            return super().eventFilter(obj, event)

        # Capturamos el cambio de foco antes de que Qt mueva el cursor internamente
        if self.grabando and event.type() == event.Type.FocusIn:
            if isinstance(obj, (QLineEdit, QTextEdit)) and obj != self.widget_objetivo:
                
                # Limpiamos el texto predictivo parcial del campo viejo
                self.eliminar_parcial_previo()
                
                if self.widget_objetivo:
                    campo_viejo = self.widget_objetivo
                    campo_viejo.setToolTip("")
                    self.formatear_campo_especifico(campo_viejo)
                
                self.widget_objetivo = obj
                self.longitud_parcial_previa = 0
                self.mostrar_aviso_flotante("➡️ Voz desviada a este campo")
                self.widget_objetivo.setToolTip("🎤 Escuchando... Haga clic en otra casilla o presione ALT para apagar")
                return False 

        # 🎯 BOTÓN ÚNICO UNIVERSAL: Tecla ALT (Izquierda)
        if event.type() == event.Type.KeyPress and event.key() == Qt.Key_Alt:
            if not event.isAutoRepeat() and not self.tecla_presionada:
                self.tecla_presionada = True
                
                if not self.grabando:
                    focus_widget = self.app.focusWidget()
                    if isinstance(focus_widget, (QLineEdit, QTextEdit)):
                        self.widget_objetivo = focus_widget
                        self.iniciar_dictado()
                else:
                    self.detener_dictado()
            return True

        if event.type() == event.Type.KeyRelease and event.key() == Qt.Key_Alt:
            if not event.isAutoRepeat():
                self.tecla_presionada = False
            return True

        return super().eventFilter(obj, event)

    def iniciar_dictado(self):
        if self.grabando or self.bloqueado:
            return
        self.grabando = True
        self.longitud_parcial_previa = 0
        self.mostrar_aviso_flotante("🎤 Transcripción activada...")
        if self.widget_objetivo:
            self.widget_objetivo.setToolTip("🎤 Escuchando... Haga clic en cualquier casilla | ALT para apagar")
        
        self.hilo_audio = HiloAudioVosk()
        self.hilo_audio.transcripcion_parcial.connect(self.inectar_texto_parcial)
        self.hilo_audio.transcripcion_final.connect(self.consolidar_texto_final)
        self.hilo_audio.error_senal.connect(self.mostrar_error)
        self.hilo_audio.start()

    def detener_dictado(self):
        if not self.grabando:
            return
        self.grabando = False
        self.mostrar_aviso_flotante("🛑 Transcripción desactivada")
        if self.hilo_audio:
            self.hilo_audio.detener()
            self.hilo_audio.wait()
        if self.widget_objetivo:
            self.widget_objetivo.setToolTip("")
            self.formatear_campo_especifico(self.widget_objetivo)
        self.widget_objetivo = None

    def formatear_campo_especifico(self, widget):
        if not widget:
            return
            
        import asistente_ia

        # 📋 FILTRO ESTRICTO POR NOMBRE DE CLASE (Tus archivos reales)
        PANTALLAS_CON_IA = ["PantallaConsulta", "PantallaInforme", "PantallaInformeEgreso", "PantallaPostOperatorio"]
        
        # Buscamos la pantalla contenedora real de este widget subiendo en el árbol de Qt
        parent_widget = widget.parent()
        nombre_clase_pantalla = ""
        
        while parent_widget is not None:
            nombre_clase_pantalla = parent_widget.__class__.__name__
            if nombre_clase_pantalla in PANTALLAS_CON_IA or nombre_clase_pantalla == "VentanaPrincipal":
                break
            parent_widget = parent_widget.parent()

        # Extraemos el texto del widget de forma segura
        texto_sucio = widget.text().strip() if isinstance(widget, QLineEdit) else widget.toPlainText().strip()
        if not texto_sucio:
            return

        # 🧠 EVALUACIÓN INCONDICIONAL POR CLASE DE LA PANTALLA ACTIVA
        if nombre_clase_pantalla in PANTALLAS_CON_IA:
            # SI PERTENECE A LAS 4 COMPONENTES -> Ejecuta Gemini de forma obligatoria
            self.mostrar_aviso_flotante("🔮 IA Puliendo texto...")
            texto_pulido = asistente_ia.refinar_texto_medico(texto_sucio)
        else:
            # EN CUALQUIER OTRA -> Formateo local inmediato de emergencia (Sin gastar cuota)
            print(f"⚡ [Voz] Filtrado local para la pantalla: {nombre_clase_pantalla}")
            texto_pulido = asistente_ia.aplicar_fallback_local(texto_sucio, "Fuera de rango clínico")

        # Inyectamos el resultado bloqueando el widget exacto que dejamos atrás
        if isinstance(widget, QLineEdit):
            widget.setText(texto_pulido)
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(texto_pulido)

    def inectar_texto_parcial(self, texto_parcial):
        if not self.widget_objetivo or self.bloqueado: return
        self.eliminar_parcial_previo()
        
        if isinstance(self.widget_objetivo, QLineEdit):
            self.widget_objetivo.insert(texto_parcial)
        elif isinstance(self.widget_objetivo, QTextEdit):
            self.widget_objetivo.insertPlainText(texto_parcial)
        self.longitud_parcial_previa = len(texto_parcial)

    def consolidar_texto_final(self, texto_bloque):
        if not self.widget_objetivo or not texto_bloque or self.bloqueado: return
        self.eliminar_parcial_previo()
        
        if isinstance(self.widget_objetivo, QLineEdit):
            self.widget_objetivo.insert(texto_bloque)
        elif isinstance(self.widget_objetivo, QTextEdit):
            self.widget_objetivo.insertPlainText(texto_bloque)
        self.longitud_parcial_previa = 0

    def eliminar_parcial_previo(self):
        if self.longitud_parcial_previa == 0 or not self.widget_objetivo: return
        
        if isinstance(self.widget_objetivo, QLineEdit):
            for _ in range(self.longitud_parcial_previa):
                self.widget_objetivo.backspace()
        elif isinstance(self.widget_objetivo, QTextEdit):
            cursor = self.widget_objetivo.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, self.longitud_parcial_previa)
            cursor.removeSelectedText()
            self.widget_objetivo.setTextCursor(cursor)
        self.longitud_parcial_previa = 0

    def mostrar_aviso_flotante(self, texto):
        if self.cartel_aviso: self.cartel_aviso.close()
        ventana_activa = self.app.activeWindow()
        if not ventana_activa: return
        self.cartel_aviso = QLabel(texto, ventana_activa)
        bg_color = "#1E293B"
        txt_color = "#34D399" if "activada" in texto else ("#60A5FA" if "desviada" in texto or "🔮" in texto else "#F87171")
        self.cartel_aviso.setStyleSheet(f"QLabel {{ background-color: {bg_color}; color: {txt_color}; font-weight: bold; font-size: 13px; padding: 10px 18px; border: 1px solid #475569; border-radius: 20px; }}")
        self.cartel_aviso.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cartel_aviso.adjustSize()
        x = (ventana_activa.width() - self.cartel_aviso.width()) // 2
        y = ventana_activa.height() - self.cartel_aviso.height() - 50
        self.cartel_aviso.move(x, y)
        self.cartel_aviso.show()
        QTimer.singleShot(1500, self.cartel_aviso.close)

    def mostrar_error(self, mensaje):
        self.grabando = False
        if self.cartel_aviso: self.cartel_aviso.close()
        box = QMessageBox(QMessageBox.Critical, "Error de Voz", mensaje, QMessageBox.Ok)
        box.exec()