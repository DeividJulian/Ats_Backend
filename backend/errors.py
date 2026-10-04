"""Spanish messages for validation and HTTP errors that the frameworks generate in English."""

# Pydantic error type -> Spanish message (the placeholders come from the error's "ctx")
VALIDATION_MESSAGES = {
    "missing": "es obligatorio",
    "string_too_short": "debe tener al menos {min_length} caracteres",
    "string_too_long": "debe tener como máximo {max_length} caracteres",
    "too_short": "debe tener al menos {min_length} elementos",
    "too_long": "admite como máximo {max_length} elementos",
    "greater_than": "debe ser mayor que {gt}",
    "greater_than_equal": "debe ser mayor o igual a {ge}",
    "less_than": "debe ser menor que {lt}",
    "less_than_equal": "debe ser menor o igual a {le}",
    "int_parsing": "debe ser un número entero",
    "int_type": "debe ser un número entero",
    "int_from_float": "debe ser un número entero",
    "float_parsing": "debe ser un número",
    "float_type": "debe ser un número",
    "bool_parsing": "debe ser verdadero o falso",
    "bool_type": "debe ser verdadero o falso",
    "string_type": "debe ser un texto",
    "list_type": "debe ser una lista",
    "dict_type": "debe ser un objeto JSON",
    "model_attributes_type": "debe ser un objeto JSON",
    "literal_error": "debe ser uno de estos valores: {expected}",
    "json_invalid": "el cuerpo no es un JSON válido",
}

HTTP_MESSAGES = {
    "Not Found": "Recurso no encontrado",
    "Method Not Allowed": "Método no permitido",
}


def validation_message(error: dict) -> str:
    error_type = error.get("type", "")
    if error_type == "value_error" and "email" in error.get("msg", ""):
        return "no es un correo electrónico válido"
    template = VALIDATION_MESSAGES.get(error_type)
    if template is None:
        return error.get("msg", "valor inválido")
    context = {k: str(v).replace(" or ", " o ") for k, v in (error.get("ctx") or {}).items()}
    try:
        return template.format(**context)
    except KeyError:
        return error.get("msg", "valor inválido")


def http_message(detail) -> str:
    return HTTP_MESSAGES.get(detail, detail) if isinstance(detail, str) else detail
