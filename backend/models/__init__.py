import importlib
import pkgutil

# Import every model in this folder so SQLAlchemy creates their tables
for _, _name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_name}")
