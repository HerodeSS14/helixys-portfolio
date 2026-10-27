import os
import re
from dotenv import load_dotenv
import google.generativeai as genai

# Cargamos el archivo .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)


def obtener_modelos_flash_activos():
    """
    Escanea los servidores de Google en tiempo real y filtra los modelos.
    Establece el umbral mínimo de calidad en la versión 3.1-flash-lite.
    Ignora versiones inferiores (2.0, 2.5) y, si el 3.1 es descontinuado a futuro,
    captura automáticamente el modelo más económico disponible en ese momento.
    """
    if not API_KEY:
        return []
    
    try:
        modelos_filtrados = []
        
        # 🎯 CONFIGURACIÓN DE TU ESTRATEGIA EXCLUSIVA:
        VERSION_MINIMA_PERMITIDA = 3.1
        
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                nombre_limpio = m.name.replace("models/", "")
                
                # Filtro base de estabilidad (ignoramos experimentales, previews e imágenes)
                if "flash" in nombre_limpio and not any(x in nombre_limpio for x in ["-exp", "-preview", "-image"]):
                    
                    # Extraemos el número de versión (ej: 'gemini-3.1-flash-lite' -> 3.1)
                    numeros = re.findall(r"\d+\.\d+|\d+", nombre_limpio)
                    version_modelo = float(numeros[0]) if numeros else 1.5
                    
                    # 🛡️ FILTRO DE UMBRAL MÍNIMO:
                    # Solo dejamos pasar modelos que sean versión 3.1 o superiores (ej: 3.1, 3.5, 4.0, etc.)
                    # Esto descarta de inmediato al 2.0 y al 2.5 para mantener la calidad alta que te gustó.
                    if version_modelo >= VERSION_MINIMA_PERMITIDA:
                        modelos_filtrados.append(nombre_limpio)
        
        # 💰 ORDENAMIENTO ECONÓMICO INTELIGENTE:
        # Una vez que pasaron el filtro de calidad, los ordenamos de MENOR a MAYOR costo.
        # Ponemos los 'lite' primero, y luego los 'flash' estándar ordenados por versión.
        modelos_filtrados.sort(key=lambda x: (0 if "lite" in x else 1, x))
        
        # Salvavidas histórico rígido por si acaso
        if not modelos_filtrados:
            modelos_filtrados = ["gemini-3.1-flash-lite"]
            
        return modelos_filtrados

    except Exception as e:
        print(f"⚠️ [IA] No se pudo mapear la lista dinámica de Google ({e}). Usando respaldo.")
        return ["gemini-3.1-flash-lite"]


def refinar_texto_medico(texto_crudo):
    """
    Toma el texto crudo de Vosk y lo procesa con Gemini usando un sistema 
    de redundancia en cascada autodetectado dinámicamente.
    """
    if not texto_crudo.strip():
        return ""

    # Si no hay API Key, vamos directo al salvavidas local offline
    if not API_KEY:
        return aplicar_fallback_local(texto_crudo, "Sin API Key en .env")

    # OBTENCIÓN DINÁMICA DE MODELOS ACTIVOS Y ECONÓMICOS
    modelos_candidatos = obtener_modelos_flash_activos()
    print(f"📋 [IA] Modelos económicos detectados y activos: {modelos_candidatos}")

    # PROBAR MODELOS EN CASCADA
    for nombre_modelo in modelos_candidatos:
        try:
            print(f"🔮 [IA] Intentando refinamiento con el motor: {nombre_modelo}...")
            model = genai.GenerativeModel(nombre_modelo)
            
            prompt_sistema = (
                "Actúa como un transcriptor médico experto de alta precisión. Tu tarea es corregir, "
                "pulir y estructurar el siguiente texto que fue capturado mediante reconocimiento de voz. "
                "Reglas estrictas:\n"
                "1. Corrige errores de ortografía, puntuación, mayúsculas y coherencia gramatical.\n"
                "2. Optimiza los términos médicos mal pronunciados dando coherencia clínica.\n"
                "3. Mantén estrictamente el significado original, NO inventes síntomas ni diagnósticos.\n"
                "4. Devuelve ÚNICAMENTE el texto limpio, formateado en prosa fluida profesional, comenzando con mayúscula y terminando en punto. No agregues saludos ni notas adicionales."
            )

            prompt_final = f"{prompt_sistema}\n\nTexto a corregir:\n\"{texto_crudo}\""
            respuesta = model.generate_content(prompt_final)
            
            texto_pulido = respuesta.text.strip()
            if texto_pulido:
                version_real = getattr(respuesta, 'model_version', 'Estable (Latest)')
                print(f"✅ [IA] Refinamiento exitoso con: {nombre_modelo} [Versión Real: {version_real}]")
                return texto_pulido

        except Exception as e:
            error_msg = str(e).lower()
            # Si el modelo fue descontinuado (404), dio error de cuota o restricción, saltamos al siguiente activo
            if any(x in error_msg for x in ["not found", "404", "supported", "resource_exhausted", "limit"]):
                print(f"⚠️ [IA] El modelo {nombre_modelo} no respondió adecuadamente. Saltando al siguiente modelo económico...")
                continue
            else:
                # Si es un error crítico de red estructural, vamos al fallback local
                return aplicar_fallback_local(texto_crudo, f"Fallo estructural: {str(e)}")

    # Si recorrió todos los modelos de la lista dinámica y ninguno sirvió
    return aplicar_fallback_local(texto_crudo, "Todos los modelos de Google fallaron o están offline")


def aplicar_fallback_local(texto_crudo, razon):
    """ SALVAVIDAS OFFLINE: Evita que el software se quede trabado si la nube falla """
    print(f"🚨 [IA CONTRAMEDIDA] Activando formateo local de emergencia. Razón: {razon}")
    
    texto_limpio = texto_crudo.strip()
    if not texto_limpio:
        return ""
        
    texto_formateado = texto_limpio[0].upper() + texto_limpio[1:]
    if not texto_formateado.endswith("."):
        texto_formateado += "."
        
    return texto_formateado