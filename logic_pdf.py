import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from datetime import datetime
from database import SessionLocal
from models import PerfilDoctor, Paciente

class GeneradorPrescripcion:
    def __init__(self):
        self.ancho, self.alto = letter # 8.5 x 11 pulgadas
        
    def crear_recipe(self, paciente_id, items_recipe, nombre_archivo="recipe.pdf"):
        # 1. Obtener datos de la DB
        db = SessionLocal()
        doc = db.query(PerfilDoctor).first()
        paciente = db.query(Paciente).get(paciente_id)
        db.close()

        if not doc:
            print("Error: No hay perfil de doctor configurado.")
            return

        c = canvas.Canvas(nombre_archivo, pagesize=letter)
        
        # --- CABECERA (DISEÑO PROFESIONAL) ---
        # Logo (si existe)
        if doc.logo_doctor and os.path.exists(doc.logo_doctor):
            logo = ImageReader(doc.logo_doctor)
            c.drawImage(logo, 0.5*inch, 9.8*inch, width=1.2*inch, height=1*inch, mask='auto')

        # Datos de la Clínica y Doctor (Derecha)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(7.8*inch, 10.5*inch, doc.nombre_clinica.upper())
        
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(7.8*inch, 10.3*inch, f"Dra. {doc.nombre_doctor}")
        
        c.setFont("Helvetica", 10)
        c.drawRightString(7.8*inch, 10.15*inch, doc.especialidades)
        c.drawRightString(7.8*inch, 10.0*inch, f"C.I: {doc.cedula_doctor} | MSDS: {doc.matricula_msds}")
        
        c.setLineWidth(1)
        c.line(0.5*inch, 9.7*inch, 8.0*inch, 9.7*inch) # Línea divisoria

        # --- DATOS DEL PACIENTE ---
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.5*inch, 9.4*inch, f"PACIENTE: {paciente.nombre_completo}")
        c.drawRightString(8.0*inch, 9.4*inch, f"FECHA: {datetime.now().strftime('%d/%m/%Y')}")
        
        c.setFont("Helvetica", 10)
        c.drawString(0.5*inch, 9.2*inch, f"CÉDULA: {paciente.cedula}  |  EDAD: {paciente.edad_actual} años")
        
        c.line(0.5*inch, 9.1*inch, 8.0*inch, 9.1*inch)

        # --- CUERPO DEL RÉCIPE (Rp:) ---
        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.5*inch, 8.7*inch, "Rp:")
        
        # Aquí escribimos los medicamentos
        c.setFont("Courier", 11) # Fuente tipo máquina de escribir para evitar errores de lectura
        y_pos = 8.4*inch
        for item in items_recipe:
            # Dividimos por líneas si el texto es muy largo
            c.drawString(0.7*inch, y_pos, f"• {item}")
            y_pos -= 0.3*inch
            if y_pos < 4*inch: # Salto de seguridad
                break

        # --- FIRMA Y SELLO ---
        if doc.firma_digital and os.path.exists(doc.firma_digital):
            firma = ImageReader(doc.firma_digital)
            c.drawImage(firma, 3.2*inch, 1.5*inch, width=2*inch, height=0.8*inch, mask='auto')
        
        c.setFont("Helvetica", 9)
        c.drawCentredString(self.ancho/2, 1.2*inch, "_______________________________________")
        c.drawCentredString(self.ancho/2, 1.0*inch, f"Dra. {doc.nombre_doctor}")
        c.drawCentredString(self.ancho/2, 0.85*inch, f"C.I: {doc.cedula_doctor} | Rif: J-12345678-9")

        # --- PIE DE PÁGINA (DIRECCIÓN) ---
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(self.ancho/2, 0.4*inch, f"Dirección: {doc.direccion_clinica} | Correo: {doc.correo_doctor}")

        c.save()
        print(f"PDF Generado: {nombre_archivo}")
        return nombre_archivo