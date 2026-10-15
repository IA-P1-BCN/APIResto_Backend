from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse
from app.core.pagination import Page, PageParamsDep
from app.core.permissions import USERS, CurrentUser, require_role
from app.database import get_db
from app.models.model_user import Role
from app.schemas.schema_user import (
    PasswordChange,
    UserCreate,
    UserOut,
    UserProfileUpdate,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

me_router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]
IncludeDeleted = Annotated[
    bool, Query(description="Incluir también los usuarios borrados (soft delete)")
]


@router.post("/", response_model=UserOut, status_code=201, summary="Crear usuario")
def create_user(user: UserCreate, db: DbSession, actor: CurrentUser):
    return user_service.create_user(db, user, actor)


@router.get(
    "/",
    response_model=Page[UserOut],
    summary="Listar, filtrar y buscar usuarios",
    description=(
        "Listado paginado (HU-24). Los filtros se combinan entre sí. "
        "Orden fijo por `id` ascendente."
    ),
)
def list_users(
    db: DbSession,
    params: PageParamsDep,
    role: Annotated[
        Role | None, Query(description="Filtrar por rol.", examples=["waiter"])
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="`true`: solo activos; `false`: solo desactivados. Sin valor: todos."),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            description="Búsqueda parcial, sin distinguir mayúsculas, en nombre o email.",
            examples=["ana"],
        ),
    ] = None,
    include_deleted: IncludeDeleted = False,
):
    return user_service.list_users(
        db, params, role=role, is_active=is_active, q=q, include_deleted=include_deleted
    )


@router.get("/{user_id}", response_model=UserOut, summary="Obtener usuario")
def get_user(user_id: int, db: DbSession, include_deleted: IncludeDeleted = False):
    return user_service.get_user(db, user_id, include_deleted=include_deleted)


@router.put("/{user_id}", response_model=UserOut, summary="Editar usuario")
def update_user(user_id: int, data: UserUpdate, db: DbSession, actor: CurrentUser):
    return user_service.update_user(db, user_id, data, actor)


@router.patch("/{user_id}/deactivate", response_model=UserOut, summary="Desactivar usuario")
def deactivate(user_id: int, db: DbSession, actor: CurrentUser):
    return user_service.deactivate_user(db, user_id, actor)


@router.delete("/{user_id}", response_model=UserOut, summary="Borrar usuario (soft delete)")
def delete_user(user_id: int, db: DbSession, actor: CurrentUser):
    return user_service.delete_user(db, user_id, actor)


@router.post("/{user_id}/restore", response_model=UserOut, summary="Restaurar usuario borrado")
def restore_user(user_id: int, db: DbSession, actor: CurrentUser):
    return user_service.restore_user(db, user_id, actor)


def _me_errors(descriptions: dict[int, str]) -> dict[int | str, dict[str, Any]]:
    return {
        code: {"model": ErrorResponse, "description": description}
        for code, description in descriptions.items()
    }


@me_router.patch(
    "/me",
    response_model=UserOut,
    summary="Editar mi perfil",
    responses=_me_errors({
        401: "Falta el token o no es válido.",
        409: "El email ya pertenece a otro usuario (`conflict`).",
        422: "Datos no válidos o campos no editables como `role` o `is_active` "
        "(`validation_error`).",
    }),
)
def update_my_profile(data: UserProfileUpdate, db: DbSession, current_user: CurrentUser):
    """Edita `name`, `email` y `phone` del usuario autenticado, de cualquier rol.

    Solo se aplican los campos enviados. `role` e `is_active` no se pueden cambiar (422).
    El email se guarda en minúsculas y debe ser único (R-01, 409).
    """
    return user_service.update_profile(db, current_user, data)


@me_router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Cambiar mi contraseña",
    responses=_me_errors({
        400: "La cuenta no tiene contraseña, solo login social (`password_not_set`).",
        401: "Falta el token o no es válido.",
        403: "La contraseña actual no es correcta (`invalid_current_password`).",
        422: "Datos no válidos (`validation_error`) o nueva contraseña igual a la "
        "actual (`same_password`).",
    }),
)
def change_my_password(data: PasswordChange, db: DbSession, current_user: CurrentUser):
    """Cambia la contraseña del usuario autenticado verificando la actual.

    La nueva debe tener al menos 8 caracteres (R-02) y se guarda con bcrypt. Sin cuerpo.
    """
    user_service.change_password(db, current_user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
