"""Tests de integración de HU-51: reservas del cliente sin elegir mesa.

Sin `table_id` el backend asigna la mesa libre más pequeña con sitio; un customer no
puede reservar para más de 8 personas; sin mesa libre → 409; en el pasado → 422.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.security import create_access_token
from app.models.dining_table import OUT_OF_SERVICE, DiningTable
from app.models.model_user import Role, User
from app.routers import reservations as reservations_router

FUTURE_DAY = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
PAST_DAY = "2020-01-01"
LIMIT_MESSAGE = "Para reservas de más de 8 personas, llama al restaurante"


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _assert_error(response: Any, status_code: int, code: str) -> dict[str, Any]:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == code
    return body


def _request(party_size: int = 2, hour: str = "20:00", day: str = FUTURE_DAY, **extra):
    return {
        "reserved_at": f"{day}T{hour}:00",
        "party_size": party_size,
        **extra,
    }


@pytest.fixture
def make_table(db) -> Callable[..., DiningTable]:
    def _make(number: int, capacity: int, status: str = "available") -> DiningTable:
        table = DiningTable(
            number=number, capacity=capacity, location="indoor", status=status
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    return _make


@pytest.fixture
def tables(make_table) -> dict[int, DiningTable]:
    """Mesas de 2, 4 y 6 personas, indexadas por capacidad."""
    return {
        capacity: make_table(number=capacity, capacity=capacity)
        for capacity in (6, 2, 4)
    }


@pytest.fixture
def customer(make_user) -> User:
    return make_user(Role.customer, email="cliente@test.com")


@pytest.fixture
def customer_headers(customer) -> dict[str, str]:
    return _headers(customer)


@pytest.fixture
def sent_emails(monkeypatch) -> list[tuple[str, str, str]]:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        reservations_router, "send_email", lambda *args: sent.append(args)
    )
    return sent


@pytest.fixture
def waiter_headers(make_user) -> dict[str, str]:
    return _headers(make_user(Role.waiter, email="camarero@test.com"))


def test_customer_without_table_id_gets_the_tightest_table(
    client, tables, customer, customer_headers
):
    response = client.post(
        "/reservations", json=_request(2, notes="Ventana"), headers=customer_headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["table_id"] == tables[2].id
    assert body["user_id"] == customer.id
    assert body["status"] == "confirmed"
    assert body["notes"] == "Ventana"


def test_party_size_picks_the_smallest_table_that_fits(
    client, tables, customer_headers
):
    response = client.post("/reservations", json=_request(3), headers=customer_headers)

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == tables[4].id


def test_taken_table_falls_back_to_the_next_one(client, tables, customer_headers):
    first = client.post("/reservations", json=_request(2), headers=customer_headers)
    second = client.post("/reservations", json=_request(2), headers=customer_headers)

    assert first.json()["table_id"] == tables[2].id
    assert second.status_code == 201, second.text
    assert second.json()["table_id"] == tables[4].id


def test_out_of_service_table_is_skipped(client, make_table, customer_headers):
    make_table(number=1, capacity=2, status=OUT_OF_SERVICE)
    ok = make_table(number=2, capacity=4)

    response = client.post("/reservations", json=_request(2), headers=customer_headers)

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == ok.id


def test_cancelled_reservation_does_not_block_the_table(
    client, tables, customer_headers
):
    first = client.post("/reservations", json=_request(2), headers=customer_headers)
    client.patch(f"/reservations/{first.json()['id']}/cancel", headers=customer_headers)

    again = client.post("/reservations", json=_request(2), headers=customer_headers)

    assert again.status_code == 201, again.text
    assert again.json()["table_id"] == tables[2].id


def test_no_free_table_returns_409(client, make_table, customer_headers):
    make_table(number=1, capacity=2)
    client.post("/reservations", json=_request(2), headers=customer_headers)

    response = client.post("/reservations", json=_request(2), headers=customer_headers)

    body = _assert_error(response, 409, "no_table_available")
    assert (
        body["detail"]
        == f"No hay mesa libre para 2 personas el {FUTURE_DAY[8:]}/{FUTURE_DAY[5:7]}/{FUTURE_DAY[:4]} a las 20:00"
    )


def test_no_table_big_enough_returns_409(client, tables, customer_headers):
    _assert_error(
        client.post("/reservations", json=_request(8), headers=customer_headers),
        409,
        "no_table_available",
    )


def test_customer_with_more_than_8_people_returns_422(client, tables, customer_headers):
    response = client.post("/reservations", json=_request(9), headers=customer_headers)

    body = _assert_error(response, 422, "party_size_too_large")
    assert body["detail"] == LIMIT_MESSAGE


def test_customer_with_exactly_8_people_is_accepted(
    client, make_table, customer_headers
):
    big = make_table(number=1, capacity=8)

    response = client.post("/reservations", json=_request(8), headers=customer_headers)

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == big.id


def test_customer_with_table_id_and_more_than_8_people_returns_422(
    client, make_table, customer_headers
):
    table = make_table(number=1, capacity=12)

    response = client.post(
        "/reservations",
        json=_request(9, table_id=table.id),
        headers=customer_headers,
    )

    _assert_error(response, 422, "party_size_too_large")


def test_customer_edit_over_8_people_returns_422(client, make_table, customer_headers):
    table = make_table(number=1, capacity=12)
    created = client.post(
        "/reservations", json=_request(2, table_id=table.id), headers=customer_headers
    ).json()

    response = client.patch(
        f"/reservations/{created['id']}",
        json={"party_size": 9},
        headers=customer_headers,
    )

    body = _assert_error(response, 422, "party_size_too_large")
    assert body["detail"] == LIMIT_MESSAGE


def test_customer_edit_to_8_people_is_accepted(client, make_table, customer_headers):
    table = make_table(number=1, capacity=12)
    created = client.post(
        "/reservations", json=_request(2, table_id=table.id), headers=customer_headers
    ).json()

    response = client.patch(
        f"/reservations/{created['id']}",
        json={"party_size": 8},
        headers=customer_headers,
    )

    assert response.status_code == 200, response.text


def test_waiter_can_book_more_than_8_people(client, make_table, waiter_headers):
    big = make_table(number=1, capacity=12)

    response = client.post("/reservations", json=_request(9), headers=waiter_headers)

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == big.id


def test_waiter_edit_over_8_people_is_accepted(client, make_table, waiter_headers):
    table = make_table(number=1, capacity=12)
    created = client.post(
        "/reservations", json=_request(2, table_id=table.id), headers=waiter_headers
    ).json()

    response = client.patch(
        f"/reservations/{created['id']}",
        json={"party_size": 10},
        headers=waiter_headers,
    )

    assert response.status_code == 200, response.text


def test_admin_without_table_id_also_gets_a_table(client, tables, admin_headers):
    response = client.post("/reservations", json=_request(2), headers=admin_headers)

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == tables[2].id


def test_customer_can_still_send_table_id(client, tables, customer_headers):
    response = client.post(
        "/reservations",
        json=_request(2, table_id=tables[6].id),
        headers=customer_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["table_id"] == tables[6].id


def test_auto_assigned_reservation_appears_in_my_reservations(
    client, tables, customer_headers
):
    created = client.post("/reservations", json=_request(2), headers=customer_headers)

    listing = client.get("/reservations", headers=customer_headers)

    assert [item["id"] for item in listing.json()["items"]] == [created.json()["id"]]


def test_auto_assigned_reservation_sends_confirmation_email(
    client, tables, customer, customer_headers, sent_emails
):
    response = client.post("/reservations", json=_request(2), headers=customer_headers)

    assert response.status_code == 201, response.text
    assert len(sent_emails) == 1
    to, _subject, html = sent_emails[0]
    assert to == customer.email
    assert f"mesa {tables[2].number}" in html


def test_auto_assignment_in_the_past_returns_422(client, tables, customer_headers):
    response = client.post(
        "/reservations", json=_request(2, day=PAST_DAY), headers=customer_headers
    )

    _assert_error(response, 422, "reservation_in_past")


def test_past_reservation_with_table_id_keeps_working(client, tables, waiter_headers):
    response = client.post(
        "/reservations",
        json=_request(2, day=PAST_DAY, table_id=tables[2].id),
        headers=waiter_headers,
    )

    assert response.status_code == 201, response.text


def test_rejected_auto_reservation_sends_no_email(
    client, tables, customer_headers, sent_emails
):
    client.post("/reservations", json=_request(9), headers=customer_headers)

    assert sent_emails == []


def test_tables_available_stays_closed_to_customers(client, customer_headers):
    response = client.get(
        "/tables/available",
        params={"reserved_at": f"{FUTURE_DAY}T20:00:00", "party_size": 2},
        headers=customer_headers,
    )

    assert response.status_code == 403
