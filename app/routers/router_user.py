from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.openapi import error_responses
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
from app.services import email_verification_service, user_service
from app.services.auth_emails import verification_email
from app.services.notifications import send_email

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

me_router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]
SEARCH_MAX_LENGTH = 100

IncludeDeleted = Annotated[
    bool, Query(description="Incluir también los usuarios borrados (soft delete)")
]
UserId = Annotated[int, Path(description="Id del usuario.", examples=[7])]

NOT_ADMIN = "El usuario autenticado no es `admin` (`forbidden`)."
NOT_ADMIN_OR_SELF = (
    "El usuario autenticado no es `admin`, o un admin intenta desactivarse o borrarse a sí "
    "mismo (`forbidden`)."
)
USER_NOT_FOUND = "El usuario no existe o está borrado (`not_found`)."
EMAIL_TAKEN = "El email ya pertenece a otro usuario (`conflict`, R-01)."
BAD_USER_ID = "`user_id` no es un número entero (`validation_error`)."


@router.post(
    "/",
    response_model=UserOut,
    status_code=201,
    summary="Crear usuario",
    responses=error_responses(
        401,
        403,
        409,
        422,
        descriptions={403: NOT_ADMIN, 409: EMAIL_TAKEN},
    ),
)
def create_user(user: UserCreate, db: DbSession, actor: CurrentUser):
    """Crea un usuario de cualquier rol (R-03), activo al instante.

    El email se guarda en minúsculas y debe ser único (R-01). Rol: admin.
    """
    return user_service.create_user(db, user, actor)


@router.get(
    "/",
    response_model=Page[UserOut],
    summary="Listar, filtrar y buscar usuarios",
    description=(
        "Listado paginado (HU-24). Los filtros se combinan entre sí. "
        "Orden fijo por `id` ascendente. Los borrados solo salen con "
        "`include_deleted=true`. Rol: admin."
    ),
    responses=error_responses(
        401,
        403,
        422,
        descriptions={
            403: NOT_ADMIN,
            422: "Parámetros no válidos: `role` desconocido, `q` de más de "
            f"{SEARCH_MAX_LENGTH} caracteres, `page` menor que 1 o `size` fuera de 1-100 "
            "(`validation_error`).",
        },
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
            max_length=SEARCH_MAX_LENGTH,
            description=(
                "Búsqueda parcial en nombre o email, sin distinguir mayúsculas ni acentos. "
                f"Máximo {SEARCH_MAX_LENGTH} caracteres."
            ),
            examples=["jose"],
        ),
    ] = None,
    include_deleted: IncludeDeleted = False,
):
    return user_service.list_users(
        db, params, role=role, is_active=is_active, q=q, include_deleted=include_deleted
    )


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Obtener usuario",
    responses=error_responses(
        401,
        403,
        404,
        422,
        descriptions={
            403: NOT_ADMIN,
            404: "El usuario no existe, o está borrado y no se ha pedido "
            "`include_deleted=true` (`not_found`).",
            422: BAD_USER_ID,
        },
    ),
)
def get_user(user_id: UserId, db: DbSession, include_deleted: IncludeDeleted = False):
    """Devuelve un usuario por su id. Los borrados solo con `include_deleted=true`. Rol: admin."""
    return user_service.get_user(db, user_id, include_deleted=include_deleted)


@router.put(
    "/{user_id}",
    response_model=UserOut,
    summary="Editar usuario",
    responses=error_responses(
        401,
        403,
        404,
        409,
        422,
        descriptions={403: NOT_ADMIN, 404: USER_NOT_FOUND, 409: EMAIL_TAKEN},
    ),
)
def update_user(user_id: UserId, data: UserUpdate, db: DbSession, actor: CurrentUser):
    """Edita solo los campos enviados, incluidos `role` y `password` (se guarda con bcrypt).

    Rol: admin.
    """
    return user_service.update_user(db, user_id, data, actor)


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserOut,
    summary="Desactivar usuario",
    responses=error_responses(
        401,
        403,
        404,
        422,
        descriptions={403: NOT_ADMIN_OR_SELF, 404: USER_NOT_FOUND, 422: BAD_USER_ID},
    ),
)
def deactivate(user_id: UserId, db: DbSession, actor: CurrentUser):
    """Pone `is_active=false`: sigue en los listados, pero no puede iniciar sesión (R-04, R-08).

    Rol: admin.
    """
    return user_service.deactivate_user(db, user_id, actor)


@router.delete(
    "/{user_id}",
    response_model=UserOut,
    summary="Borrar usuario (soft delete)",
    responses=error_responses(
        401,
        403,
        404,
        422,
        descriptions={403: NOT_ADMIN_OR_SELF, 404: USER_NOT_FOUND, 422: BAD_USER_ID},
    ),
)
def delete_user(user_id: UserId, db: DbSession, actor: CurrentUser):
    """Soft delete: marca `deleted_at` e `is_active=false` y lo oculta de los listados (R-11).

    No hay borrado físico (R-04). Se puede deshacer con `POST /users/{user_id}/restore`.
    Rol: admin.
    """
    return user_service.delete_user(db, user_id, actor)


@router.post(
    "/{user_id}/restore",
    response_model=UserOut,
    summary="Restaurar usuario borrado",
    responses=error_responses(
        401,
        403,
        404,
        409,
        422,
        descriptions={
            403: NOT_ADMIN,
            404: "El usuario no existe (`not_found`).",
            409: "El usuario no está borrado (`conflict`).",
            422: BAD_USER_ID,
        },
    ),
)
def restore_user(user_id: UserId, db: DbSession, actor: CurrentUser):
    """Quita `deleted_at` y deja el usuario activo de nuevo. Rol: admin."""
    return user_service.restore_user(db, user_id, actor)


@me_router.patch(
    "/me",
    response_model=UserOut,
    summary="Editar mi perfil",
    responses=error_responses(
        401,
        409,
        422,
        descriptions={
            401: "Falta el token o no es válido.",
            409: "El email ya pertenece a otro usuario (`conflict`).",
            422: "Datos no válidos o campos no editables como `role` o `is_active` "
            "(`validation_error`).",
        },
    ),
)
def update_my_profile(
    data: UserProfileUpdate,
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    """Edita `name`, `email` y `phone` del usuario autenticado, de cualquier rol.

    Solo se aplican los campos enviados. `role` e `is_active` no se pueden cambiar (422).
    El email se guarda en minúsculas y debe ser único (R-01, 409). Si el email cambia,
    queda `email_verified=false`, se invalidan los enlaces pendientes y se envía uno nuevo
    a la dirección nueva (R-15, decisión E); el usuario no pierde el acceso.
    Rol: cualquier usuario autenticado.
    """
    user, token = email_verification_service.update_profile(db, current_user, data)
    if token is not None:
        background_tasks.add_task(send_email, *verification_email(user, token))
    return user


@me_router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Cambiar mi contraseña",
    responses=error_responses(
        400,
        401,
        403,
        422,
        descriptions={
            400: "La cuenta no tiene contraseña, solo login social (`password_not_set`).",
            401: "Falta el token o no es válido.",
            403: "La contraseña actual no es correcta (`invalid_current_password`).",
            422: "Datos no válidos (`validation_error`) o nueva contraseña igual a la "
            "actual (`same_password`).",
        },
    ),
)
def change_my_password(data: PasswordChange, db: DbSession, current_user: CurrentUser):
    """Cambia la contraseña del usuario autenticado verificando la actual.

    La nueva debe tener al menos 8 caracteres (R-02) y se guarda con bcrypt. Sin cuerpo.
    Rol: cualquier usuario autenticado.
    """
    user_service.change_password(db, current_user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
