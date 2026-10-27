from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, date
import bcrypt

Base = declarative_base()

# --- 0. GESTIÓN DE USUARIOS Y SEGURIDAD ---
class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False) # Subimos a 255 por seguridad
    rol = Column(String(50), nullable=False)  # 'principal' (doctor) o 'secundaria'
    secretaria_pass_plain = Column(String(100), nullable=True)
    # Dentro de la clase Usuario en models.py:
    codigo_maestro_plain = Column(String(50), nullable=True) # Para mantener el código siempre visible
    # --- RECUPERACIÓN NIVEL 1: Preguntas de Seguridad ---
    pregunta_seguridad_1 = Column(String(150), nullable=True)
    respuesta_hash_1 = Column(String(255), nullable=True)
    pregunta_seguridad_2 = Column(String(150), nullable=True)
    respuesta_hash_2 = Column(String(255), nullable=True)
    
    
    # --- RECUPERACIÓN NIVEL 2: Código Maestro de Emergencia ---
    codigo_maestro_hash = Column(String(255), nullable=True)

    def set_password(self, password):
        """Encripta la contraseña antes de guardarla"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Verifica si la contraseña ingresada coincide con el hash"""
        # Validamos que password_hash exista antes de chequear
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
# --- 1. CONFIGURACIÓN DEL DOCTOR (MEMBRETE) ---
class PerfilDoctor(Base):
    __tablename__ = "perfil_doctor"
    id = Column(Integer, primary_key=True)
    nombre_clinica = Column(String)
    nombre_doctor = Column(String)
    cedula_doctor = Column(String)
    especialidades = Column(String)
    genero_doctor = Column(String)
    matricula_msds = Column(String)
    rif_clinica = Column(String)
    direccion_clinica = Column(String)
    correo_doctor = Column(String)
    logo_ruta = Column(String) 
    firma_ruta = Column(String) 
    plantilla_consentimiento = Column(Text, nullable=True)

# --- 2. GESTIÓN INTEGRAL DE PACIENTES ---
class Paciente(Base):
    __tablename__ = 'pacientes'
    id = Column(Integer, primary_key=True)
    cedula = Column(String(25), unique=True, nullable=False)
    nombre_completo = Column(String(255), nullable=False)
    fecha_nacimiento = Column(Date)
    genero = Column(String(20)) 
    nacionalidad = Column(String(100))
    pais = Column(String(100))
    estado_civil = Column(String(50))
    profesion = Column(String(200))
    telefono_celular = Column(String(50))
    telefono_casa = Column(String(50))
    direccion = Column(Text)
    seguro = Column(String(150))
    referido = Column(String(150))
    fecha_registro = Column(DateTime, default=datetime.now)

    @hybrid_property
    def edad_actual(self):
        if self.fecha_nacimiento:
            hoy = date.today()
            return hoy.year - self.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return 0

    consultas = relationship("Consulta", back_populates="paciente")
    antecedentes = relationship("Antecedentes", uselist=False, back_populates="paciente")
    gineco = relationship("GinecoObstetrico", back_populates="paciente")
    documentos = relationship("RecipeOrden", back_populates="paciente")
    informes = relationship("InformeMedico", back_populates="paciente")
    notas_operatorias = relationship("NotaOperatoria", back_populates="paciente")
    egresos = relationship("InformeEgreso", back_populates="paciente")
    consentimientos = relationship("ConsentimientoCirugia", back_populates="paciente")
    archivos = relationship("ArchivoPaciente", back_populates="paciente")
    imagenes = relationship("OrdenImagen", back_populates="paciente")
    # Relaciones existentes:
    consultas = relationship("Consulta", back_populates="paciente")
    antecedentes = relationship("Antecedentes", uselist=False, back_populates="paciente")
    # ...
    imagenes = relationship("OrdenImagen", back_populates="paciente")

    # NUEVA RELACIÓN:
    rendimientos = relationship("Rendimiento", back_populates="paciente", cascade="all, delete-orphan")

# --- 3. ARCHIVOS, ANTECEDENTES Y GINECOLOGÍA ---
class ArchivoPaciente(Base):
    __tablename__ = 'archivos_paciente'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    nombre_archivo = Column(String(255))
    ruta_archivo = Column(Text) 
    tipo_archivo = Column(String(50)) 
    fecha_subida = Column(DateTime, default=datetime.now)
    paciente = relationship("Paciente", back_populates="archivos")

class Antecedentes(Base):
    __tablename__ = 'antecedentes'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    personales = Column(Text)
    familiares = Column(Text)
    alergias = Column(Text)
    operaciones_realizadas = Column(Text)
    
    # --- HÁBITOS Y EXAMEN FUNCIONAL INTEGRADOS ---
    habito_fuma = Column(String(50))
    habito_bebe = Column(String(50))
    otros_habitos = Column(Text)
    examen_funcional = Column(Text)
    
    paciente = relationship("Paciente", back_populates="antecedentes")

class GinecoObstetrico(Base):
    __tablename__ = 'gineco_obstetrico'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha_registro = Column(DateTime, default=datetime.now)
    menarquia = Column(String(50))
    gestas = Column(Integer, default=0)
    abortos = Column(Integer, default=0)
    embarazo_ectopico = Column(Integer, default=0)
    partos = Column(Integer, default=0)
    cesarea = Column(Integer, default=0)
    menopausia = Column(String(50))
    sangramiento = Column(Text)
    incontinencia = Column(Boolean, default=False)
    flujo = Column(Text)
    diu = Column(String(100))
    aco = Column(String(100))
    paciente = relationship("Paciente", back_populates="gineco")

# --- 4. CONSULTA Y EXAMEN FÍSICO ---
class Consulta(Base):
    __tablename__ = 'consultas'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha_consulta = Column(DateTime, default=datetime.now)
    edad_paciente = Column(Integer)
    
    # Motivo y Evolución
    motivo_consulta = Column(Text)         # NUEVO
    enfermedad_actual = Column(Text)
    nota_evolutiva = Column(Text)
    impresion_diagnostica = Column(Text)   # NUEVO
    diagnostico = Column(Text)             # NUEVO
    estudios_indicados = Column(Text)      # NUEVO
    examen_funcional = Column(Text)        # NUEVO (Movido de antecedentes para ser dinámico por consulta)
    
    # Biometría
    peso = Column(Float); altura = Column(Float); imc = Column(Float)
    tension_arterial = Column(String(50)); pulso = Column(Integer)

    # Examen Físico General
    piel = Column(Text); ojos = Column(Text); oidos = Column(Text)
    orofaringe = Column(Text); tiroides = Column(Text); axilas = Column(Text)
    supraclaviculares = Column(Text); abdomen = Column(Text); lumbar = Column(Text)
    neurologico = Column(Text)             # NUEVO
    otros_examen_fisico = Column(Text)     # NUEVO
    
    # Examen Físico Femenino/Masculino
    mamas = Column(Text); vulva = Column(Text); vagina = Column(Text)
    cervix = Column(Text); colposcopia = Column(Text); tacto_recto_vaginal = Column(Text) 
    pene_testiculos = Column(Text); prostata = Column(Text)
    
    paciente = relationship("Paciente", back_populates="consultas")

# --- 4.5. CATÁLOGO DE EXÁMENES (NUEVO REWORK) ---
class CategoriaExamen(Base):
    __tablename__ = 'categorias_examenes'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), unique=True, nullable=False)
    examenes = relationship("ExamenCatalogo", back_populates="categoria", cascade="all, delete-orphan")

class ExamenCatalogo(Base):
    __tablename__ = 'catalogo_examenes'
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey('categorias_examenes.id'))
    nombre = Column(String(255), nullable=False)
    categoria = relationship("CategoriaExamen", back_populates="examenes")

# --- 5. DOCUMENTOS DE SALIDA ---
class RecipeOrden(Base):
    __tablename__ = 'recipes_ordenes'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    consulta_id = Column(Integer, ForeignKey('consultas.id'), nullable=True) 
    edad_al_momento = Column(Integer)
    tipo_documento = Column(String(50)) 
    items = Column(Text); instrucciones = Column(Text)
    fecha = Column(DateTime, default=datetime.now)
    paciente = relationship("Paciente", back_populates="documentos")

class InformeMedico(Base):
    __tablename__ = 'informes_medicos'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha = Column(Date, nullable=False)
    edad_al_momento = Column(Integer)
    informe_escrito = Column(Text)
    
    # Configuraciones usadas en este informe
    incluir_antecedentes = Column(Boolean, default=False)
    incluir_referido = Column(Boolean, default=False)  # NUEVO
    incluir_seguro = Column(Boolean, default=False)    # NUEVO
    
    comentario = Column(String(255))
    
    paciente = relationship("Paciente", overlaps="informes")
    
class NotaOperatoria(Base):
    """(Informe Post Operatorio)"""
    __tablename__ = 'notas_operatorias'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha = Column(DateTime, default=datetime.now)
    edad_al_momento = Column(Integer)
    
    diagnostico_preoperatorio = Column(Text)
    cirugia_realizada = Column(Text)
    diagnostico_postoperatorio = Column(Text)
    descripcion_intervencion = Column(Text)
    hallazgos = Column(Text)
    biopsia = Column(Text)
    plan_manejo = Column(Text)
    
    paciente = relationship("Paciente", back_populates="notas_operatorias")

class InformeEgreso(Base):
    __tablename__ = 'informes_egreso'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha = Column(DateTime, default=datetime.now)
    edad_al_momento = Column(Integer)
    
    resumen_egreso = Column(Text)
    evaluacion = Column(Text)
    examen_fisico = Column(Text)
    paraclinicos = Column(Text)
    diagnostico_egreso = Column(Text)
    procedimiento_realizado = Column(Text)
    plan_manejo = Column(Text)
    
    paciente = relationship("Paciente", back_populates="egresos") 

class OrdenImagen(Base):
    __tablename__ = 'orden_imagenes'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    resumen_clinico = Column(Text); estudio_solicitado = Column(Text)
    fecha = Column(DateTime, default=datetime.now)
    paciente = relationship("Paciente", back_populates="imagenes") 

class ConsentimientoCirugia(Base):
    __tablename__ = 'consentimientos_cirugia'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha = Column(Date, default=datetime.now)
    intervencion = Column(Text); diagnostico = Column(Text); riesgos_especificos = Column(Text)
    familiar_nombre = Column(String(255)); familiar_cedula = Column(String(50))
    paciente = relationship("Paciente", back_populates="consentimientos")

# --- 6. AGENDA Y AUDITORÍA ---
class AgendaDiaria(Base):
    __tablename__ = 'agenda_diaria'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    hora_llegada = Column(DateTime, default=datetime.now)
    estado = Column(String(50), default="En espera"); fecha_dia = Column(Date, default=datetime.now)

class CategoriaMedicamento(Base):
    __tablename__ = 'categorias_medicamentos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), unique=True, nullable=False)
    medicamentos = relationship("MedicamentoCatalogo", back_populates="categoria", cascade="all, delete-orphan")

class MedicamentoCatalogo(Base):
    __tablename__ = 'catalogo_medicamentos'
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey('categorias_medicamentos.id'))
    nombre = Column(String(255), nullable=False)
    categoria = relationship("CategoriaMedicamento", back_populates="medicamentos")

class CitaMedica(Base):
    __tablename__ = 'citas_medicas'
    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    fecha = Column(Date, nullable=False)
    motivo = Column(String(255), default="")
    estado = Column(String(50), default="Pendiente") # "Pendiente", "Asistió", "Cancelada"
    confirmacion = Column(String(50), default="Por confirmar") # "Por confirmar", "Confirmado"

    paciente = relationship("Paciente", backref="citas")

class PlantillaInforme(Base):
    __tablename__ = 'plantillas_informe'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    texto = Column(Text, nullable=False)

class LogSistema(Base):
    __tablename__ = 'logs_sistema'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer); accion = Column(Text); timestamp = Column(DateTime, default=datetime.now)

# --- 7. MÓDULO DE RENDIMIENTOS Y HONORARIOS ---
class Rendimiento(Base):
    __tablename__ = 'rendimientos'

    id = Column(Integer, primary_key=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id', ondelete='CASCADE'), nullable=False)
    
    fecha_operacion = Column(Date, nullable=False, default=datetime.now)
    procedimiento = Column(Text, nullable=False)
    clinica = Column(String(255), nullable=True)
    
    pago_directo = Column(Float, nullable=True, default=0.0) # Monto si aplica pago directo
    seguro = Column(String(150), nullable=True)               # Empresa/Nombre de seguro si no es directo
    moneda = Column(String(10), nullable=False, default="USD") # USD ($) o VES (Bs.)
    
    # Cirujano Principal
    cirujano_p_nombre = Column(String(255), nullable=True)
    cirujano_p_cedula = Column(String(50), nullable=True)
    cirujano_p_monto = Column(Float, nullable=True, default=0.0)

    # Cirujano Auxiliar 1
    cirujano_aux1_nombre = Column(String(255), nullable=True)
    cirujano_aux1_cedula = Column(String(50), nullable=True)
    cirujano_aux1_monto = Column(Float, nullable=True, default=0.0)

    # Cirujano Auxiliar 2
    cirujano_aux2_nombre = Column(String(255), nullable=True)
    cirujano_aux2_cedula = Column(String(50), nullable=True)
    cirujano_aux2_monto = Column(Float, nullable=True, default=0.0)

    # Compatibilidad con código previo
    cirujano_p = Column(String(255), nullable=True)
    cirujano_aux1 = Column(String(255), nullable=True)
    cirujano_aux2 = Column(String(255), nullable=True)
    
    pagado = Column(Boolean, default=False, nullable=False)    # Indica si la operación está pagada o pendiente
    fecha_pago = Column(DateTime, nullable=True)               # Fecha y hora exacta en que se marcó como pagado
    
    cancelado = Column(Boolean, default=False, nullable=False) # Si fue cancelada la operación
    fecha_cancelacion = Column(Date, nullable=True)            # Fecha de cancelación
    
    cuanto = Column(Float, nullable=False, default=0.0)        # Monto total asignado / honorario

    # Relación ORM
    paciente = relationship("Paciente", back_populates="rendimientos")

    

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String, nullable=False)        # Ej: Alquiler, Luz, Equipos, Insumos
    categoria = Column(String, nullable=True)       # Ej: Operativo, Servicios, Personal
    monto = Column(Float, nullable=False, default=0.0)
    moneda = Column(String, default="USD")          # USD o VES
    fecha = Column(DateTime, default=datetime.now)  # Fecha del gasto