from app.models.model_category import Station
from app.models.model_user import Role

STATION_BY_ROLE = {
    Role.kitchen.value: Station.kitchen,
    Role.bartender.value: Station.bar,
}


def station_for_role(role: str) -> Station | None:
    """Estación que atiende el rol (R-14); None si ve todas (admin, waiter)."""
    return STATION_BY_ROLE.get(role)
