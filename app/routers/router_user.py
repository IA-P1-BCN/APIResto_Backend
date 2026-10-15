from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pagination import Page, PageParamsDep
from app.core.permissions import USERS, CurrentUser, require_role
from app.database import get_db
from app.models.model_user import Role
from app.schemas.schema_user import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(*USERS))],
)

DbSession = Annotated[Session, Depends(get_db)]
SEARCH_MAX_LENGTH = 100

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
