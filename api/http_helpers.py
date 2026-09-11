import functools
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import azure.functions as func
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from database import engine
from errors import AppError


def encode(value):
    if isinstance(value, (UUID, date, datetime, Decimal)):
        return str(value) if not isinstance(value, (date, datetime)) else value.isoformat()
    raise TypeError(type(value).__name__)


def json_response(data, status=200, headers=None):
    return func.HttpResponse(
        json.dumps(data, default=encode, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", **(headers or {})},
    )


def body(req, model):
    if req.headers.get("content-type", "").split(";")[0] != "application/json":
        raise AppError(415, "Se requiere application/json.")
    if len(req.get_body()) > 262144:
        raise AppError(413, "Formulario demasiado grande.")
    try:
        return model.model_validate_json(req.get_body())
    except ValidationError as error:
        labels = {
            "name": "Nombre",
            "organization_id": "Empresa",
            "code": "Código",
            "location": "Ubicación",
            "email": "Correo",
            "password": "Contraseña",
            "roles": "Roles",
            "project_ids": "Proyectos",
        }
        messages = []
        for issue in error.errors(include_input=False, include_context=False, include_url=False):
            key = issue["loc"][0] if issue["loc"] else None
            label = labels.get(key, "Formulario")
            if issue["type"] == "extra_forbidden":
                message = "Formulario: contiene campos no permitidos; recarga la página."
            else:
                message = f"{label}: revisa el valor y los requisitos del campo."
            if message not in messages:
                messages.append(message)
        raise AppError(400, " ".join(messages)) from None
    except ValueError:
        raise AppError(400, "Revisa los campos: valores inválidos, faltantes o inesperados.") from None


def uid(value):
    try:
        return UUID(value)
    except (ValueError, TypeError):
        raise AppError(400, "Identificador inválido.") from None


def endpoint(fn):
    @functools.wraps(fn)
    def wrapped(req):
        try:
            with engine().begin() as db:
                result = fn(db, req)
            return result if isinstance(result, func.HttpResponse) else json_response(result)
        except AppError as e:
            return json_response({"error": e.message}, e.status)
        except IntegrityError:
            return json_response({"error": "Conflicto de datos. Revisa duplicados y relaciones."}, 409)
        except Exception as error:
            logging.getLogger(__name__).error("Unhandled request failure: %s", type(error).__name__)
            return json_response({"error": "No se pudo completar la operación."}, 500)

    # functools.wraps sets __wrapped__, which inspect.signature() follows by
    # default. The Azure Functions worker uses inspect.signature() to index
    # bindings, so without this it would see fn's (db, req) signature instead
    # of wrapped's actual (req) signature and reject the extra "db" param.
    del wrapped.__wrapped__
    return wrapped
