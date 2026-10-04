import importlib
import pkgutil

# Importa todos los modelos de esta carpeta para que SQLAlchemy cree sus tablas
for _, _nombre, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_nombre}")
