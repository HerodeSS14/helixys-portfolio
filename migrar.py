# migraciones.py
from sqlalchemy import text
from database import SessionLocal, engine, Base
import models  # Asegura que se carguen los modelos de SQLAlchemy

def ejecutar_migraciones_automaticas():
    """
    Se ejecuta al iniciar la app.
    Crea tablas y agrega columnas faltantes automáticamente sin afectar datos.
    """
    
    
    # 1. Crear tablas si no existen (vía SQLAlchemy)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"⚠️ Aviso al crear tablas base: {e}")

    # 2. Sentencias SQL idempotentes para tablas y columnas específicas (PostgreSQL)
    db = SessionLocal()
    try:
        sql_script = text("""
            -- Crear tabla rendimientos si no existe
            CREATE TABLE IF NOT EXISTS rendimientos (
                id SERIAL PRIMARY KEY,
                paciente_id INT NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
                fecha_operacion DATE NOT NULL DEFAULT CURRENT_DATE,
                procedimiento TEXT NOT NULL,
                clinica VARCHAR(255),
                pago_directo DOUBLE PRECISION DEFAULT 0.0,
                seguro VARCHAR(150),
                cirujano_p VARCHAR(255),
                cirujano_aux1 VARCHAR(255),
                cirujano_aux2 VARCHAR(255),
                pagado BOOLEAN NOT NULL DEFAULT FALSE,
                fecha_pago TIMESTAMP WITHOUT TIME ZONE,
                cancelado BOOLEAN NOT NULL DEFAULT FALSE,
                fecha_cancelacion DATE,
                cuanto DOUBLE PRECISION NOT NULL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_rendimientos_paciente ON rendimientos(paciente_id);
            CREATE INDEX IF NOT EXISTS idx_rendimientos_fecha ON rendimientos(fecha_operacion);
            CREATE INDEX IF NOT EXISTS idx_rendimientos_pagado ON rendimientos(pagado);

            -- Alteraciones / Columnas nuevas para rendimientos
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS moneda VARCHAR(10) DEFAULT 'USD';
            
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_p_nombre VARCHAR(255);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_p_cedula VARCHAR(50);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_p_monto DOUBLE PRECISION DEFAULT 0.0;
            
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux1_nombre VARCHAR(255);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux1_cedula VARCHAR(50);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux1_monto DOUBLE PRECISION DEFAULT 0.0;

            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux2_nombre VARCHAR(255);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux2_cedula VARCHAR(50);
            ALTER TABLE rendimientos ADD COLUMN IF NOT EXISTS cirujano_aux2_monto DOUBLE PRECISION DEFAULT 0.0;
        """)
        
        db.execute(sql_script)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()