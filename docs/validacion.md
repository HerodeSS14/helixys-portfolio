# Validación de la muestra

Revisión local realizada el **27 de octubre de 2026**, en Windows con Python 3.12.7.

## Comprobaciones ejecutadas

- Cuatro pruebas de humo aprobadas: relación paciente-consulta, verificación de contraseña con bcrypt, construcción de la ventana del médico y construcción de la ventana del asistente sin las vistas administrativas.
- Construcción de las tablas del modelo sobre SQLite en memoria y carga de tres pacientes ficticios.
- Renderizado e inspección visual de las capturas de inicio, registro de pacientes y rendimientos, a partir de las vistas de la aplicación.
- Revisión de sintaxis de los archivos Python y de enlaces locales de la documentación.
- Revisión de la selección de archivos y búsqueda de las credenciales locales e históricas conocidas antes de publicar.

## Aislamiento

`tests/test_smoke.py` sustituye el módulo de conexión por una base SQLite temporal antes de importar las pantallas. No importa el `database.py` operativo, no carga el `.env`, no ejecuta migraciones de PostgreSQL y no activa búsqueda de red, micrófono ni servicios externos. Los archivos temporales se crean dentro de una carpeta `.test-*` y se eliminan al terminar.

Las capturas se generan con el mismo aislamiento y fuentes Segoe UI cargadas desde Windows. Son vistas reales renderizadas con datos de prueba; no acreditan una sesión conectada a PostgreSQL.

## Límites de la verificación

No se ha probado una instalación limpia de todas las dependencias ni el flujo completo contra un servidor PostgreSQL. Tampoco se han verificado de extremo a extremo impresión, exportaciones, recuperación de cuentas, micrófono, modelos de Vosk, Gemini, descubrimiento de servidores, configuración de firewall ni instaladores.

El workflow de GitHub Actions incluye la instalación de dependencias y las cuatro pruebas en Windows. Su resultado remoto debe consultarse en la pestaña Actions del repositorio; la ejecución local no demuestra que el workflow remoto haya terminado correctamente.
