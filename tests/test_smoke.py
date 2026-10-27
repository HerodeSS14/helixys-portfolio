"""Pruebas aisladas: no importan database.py ni leen credenciales locales."""

import os
import shutil
import sys
import tempfile
import types
import unittest
from datetime import date, datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import AgendaDiaria, Base, Consulta, Paciente, PerfilDoctor, Rendimiento, Usuario


def prepare_sandbox():
    """Sustituye solo el módulo de conexión para probar las vistas sin servicios."""
    sandbox = tempfile.TemporaryDirectory(prefix=".test-", dir=ROOT)
    previous_cwd = Path.cwd()
    os.chdir(sandbox.name)
    for asset in ("logo_2.png", "icono.ico", "notificacion.wav"):
        shutil.copy2(ROOT / asset, asset)
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    database = types.ModuleType("database")
    database.Base = Base
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine)
    database.host = "localhost"
    database.RUTA_CONFIG_RED = str(Path(sandbox.name) / "config_red.json")
    database.es_conexion_valida = lambda: False
    sys.modules["database"] = database
    return sandbox, previous_cwd, database


def seed_demo(session_factory):
    """Datos inventados; los identificadores DEMO no corresponden a pacientes."""
    with session_factory() as session:
        session.add(PerfilDoctor(
            nombre_clinica="Consultorio de demostración",
            nombre_doctor="Profesional de ejemplo",
            especialidades="Medicina general · DEMO",
            genero_doctor="Masculino",
        ))
        for index in range(1, 4):
            patient = Paciente(
                cedula=f"DEMO-{index:03d}",
                nombre_completo=f"Paciente de demostración {index:02d}",
                fecha_nacimiento=date(1990 + index, 5, 10),
                genero="Femenino" if index % 2 else "Masculino",
                nacionalidad="Demostración",
            )
            session.add(patient)
            session.flush()
            session.add(AgendaDiaria(
                paciente_id=patient.id, fecha_dia=date.today(),
                hora_llegada=datetime.now().replace(hour=8 + index, minute=0),
                estado="En consulta" if index == 1 else "En espera",
            ))
            session.add(Rendimiento(
                paciente_id=patient.id, fecha_operacion=date.today(),
                procedimiento="Procedimiento de demostración",
                clinica="Centro de ejemplo", moneda="USD",
                pago_directo=100.0 * index, cuanto=100.0 * index,
                cirujano_p_nombre="Profesional de ejemplo",
                cirujano_p_monto=60.0 * index, pagado=index == 1,
            ))
        session.commit()


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox, cls.previous_cwd, cls.database = prepare_sandbox()
        cls.app = QApplication.instance() or QApplication([])
        seed_demo(cls.database.SessionLocal)
        from main import VentanaPrincipal
        cls.window_class = VentanaPrincipal

    @classmethod
    def tearDownClass(cls):
        cls.database.engine.dispose()
        os.chdir(cls.previous_cwd)
        cls.sandbox.cleanup()

    def test_patient_consultation_relationship(self):
        with self.database.SessionLocal() as session:
            patient = session.query(Paciente).filter_by(cedula="DEMO-001").one()
            consultation = Consulta(paciente=patient, motivo_consulta="Ejemplo ficticio")
            session.add(consultation)
            session.commit()
            self.assertEqual(consultation.paciente_id, patient.id)
            self.assertIn(consultation, patient.consultas)
            self.assertGreater(patient.edad_actual, 0)

    def test_password_hash_rejects_wrong_password(self):
        user = Usuario(username="usuario_prueba", rol="principal")
        user.set_password("Solo-para-prueba-2026")
        self.assertNotEqual(user.password_hash, "Solo-para-prueba-2026")
        self.assertTrue(user.check_password("Solo-para-prueba-2026"))
        self.assertFalse(user.check_password("incorrecta"))

    def test_doctor_window_loads_modules_and_patients(self):
        window = self.window_class(rol_usuario="principal")
        try:
            self.assertEqual(window.stack.count(), 15)
            self.assertIsNotNone(window.view_config)
            self.assertIsNotNone(window.pantalla_rendimientos)
            self.assertEqual(window.view_dashboard.tabla_espera.rowCount(), 3)
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_assistant_window_omits_admin_views(self):
        window = self.window_class(rol_usuario="secundaria")
        try:
            self.assertIsNone(window.view_config)
            self.assertIsNone(window.pantalla_rendimientos)
            self.assertIsNone(window.pantalla_gastos)
            self.assertTrue(window.btn_conf.isHidden())
            self.assertTrue(window.btn_gastos.isHidden())
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
