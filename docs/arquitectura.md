# Arquitectura de Helixys

## Contexto

Helixys es una aplicación de escritorio de estructura modular. PySide6 presenta las vistas y conecta sus señales con acciones de registro, consulta e impresión. SQLAlchemy define las entidades y las relaciones; PostgreSQL conserva la información entre sesiones.

## Recorrido de una operación

1. `main.py` inicializa el esquema, presenta el inicio de sesión y construye la ventana correspondiente al rol.
2. Una pantalla `ui_*.py` valida los campos y obtiene una sesión mediante `SessionLocal`.
3. Los modelos traducen la operación al esquema relacional. La pantalla confirma o revierte la transacción.
4. La interfaz refresca las tablas o emite una señal para actualizar otra vista.
5. Cuando se solicita un documento, el módulo de impresión utiliza los datos del paciente y del perfil médico para producir el archivo.

## Decisiones que demuestra el proyecto

- **Interfaz de escritorio:** integración con archivos, impresión y dispositivos de audio del equipo.
- **Modelo relacional:** pacientes asociados con consultas, antecedentes, citas y documentos.
- **Módulos conectados por señales:** actualización de listas y navegación entre etapas de atención.
- **Servicios auxiliares:** generación documental y reconocimiento de voz separados de las pantallas principales.
- **Acceso por rol en la interfaz:** el asistente dispone de un conjunto de vistas más reducido que el médico.
- **Configuración externa:** las credenciales de conexión se suministran mediante variables de entorno.

Estas decisiones describen el código existente. La publicación no implica que todos los controles estén listos para un entorno clínico.

## Persistencia y conectividad

`database.py` configura el motor al importarse y trata de conectar con PostgreSQL. Ante un fallo, crea un motor SQLite en memoria para permitir el flujo de búsqueda del servidor. El arranque normal solicita una conexión PostgreSQL válida antes del login; SQLite no es un modo de almacenamiento persistente de la aplicación.

`servicio_mdns.py` permite anunciar y descubrir un servidor en la red local. Las acciones de configuración automática de `automatizacion_servidor.py` pueden modificar PostgreSQL, abrir el puerto 5432 y reiniciar servicios de Windows. La evaluación del portafolio no necesita ejecutar esas acciones.

## Voz

`motor_voz.py` captura audio con PyAudio y lo transcribe localmente con Vosk. Cuando se solicita el procesamiento de texto, `asistente_ia.py` puede usar Gemini si existe una clave configurada, o aplicar un formato local de respaldo. La integración externa y el dictado local tienen requisitos distintos y no deben describirse como un único flujo completamente sin conexión.

## Limitaciones y mejoras pendientes

- La selección de pantallas por rol no equivale a autorización de cada operación en la base de datos.
- Aunque el acceso se verifica con bcrypt, existen campos heredados que guardan contraseñas de asistentes y códigos de recuperación en texto plano.
- La configuración automática de red incluye reglas amplias con `trust`; debe sustituirse por acceso restringido y autenticado antes de evaluar un despliegue compartido.
- Las cuentas iniciales tienen claves conocidas. Deben reemplazarse en cualquier entorno compartido.
- Los importes se representan con `Float`. Una evolución del módulo financiero debería utilizar tipos decimales y reglas de redondeo explícitas.
- Las migraciones usan SQL específico de PostgreSQL y hay errores que se capturan sin informar al usuario. Una siguiente etapa sería formalizar migraciones y diagnósticos.
- La URL de conexión se construye mediante interpolación; conviene migrar a `sqlalchemy.engine.URL.create` para admitir credenciales con caracteres reservados.
- El SDK y la selección de modelos Gemini necesitan una revisión de compatibilidad antes de habilitar el servicio externo.
- Faltan validaciones completas de impresión, red, audio y flujos de usuario sobre PostgreSQL.

## Publicación para portafolio

Se publica una instantánea del código local, incluidos los cambios que ya existían en `main.py` y `migrar.py`, con un historial independiente del repositorio privado. No se trasladan su `.git`, el `.env`, instaladores, documentos, datos clínicos ni modelos binarios. Solo se elimina de `database.py` un comentario que contenía una credencial local.

La alternativa de volver público el repositorio privado se descartó porque su historial conserva credenciales. Una página web adicional queda fuera del alcance elegido para este trabajo.
