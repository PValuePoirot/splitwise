"""Tests for the expenses module."""
from __future__ import annotations

from decimal import Decimal


def _auth_headers_for(client, email: str) -> dict[str, str]:
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_create_expense_equal_split(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "total_amount": "90.00",
            "split_type": "equal",
            "participants": [
                {"user_id": user_a.id, "paid_share": "90.00", "owed_share": "30.00"},
                {"user_id": group_with_members.members[1].user_id, "paid_share": "0", "owed_share": "30.00"},
                {"user_id": group_with_members.members[2].user_id, "paid_share": "0", "owed_share": "30.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Dinner"
    assert Decimal(data["total_amount"]) == Decimal("90.00")
    assert len(data["participants"]) == 3


def test_create_expense_paid_shares_mismatch(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Bad",
            "total_amount": "90.00",
            "split_type": "exact",
            "participants": [
                {"user_id": user_a.id, "paid_share": "50.00", "owed_share": "90.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_create_expense_owed_shares_mismatch(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Bad",
            "total_amount": "100.00",
            "split_type": "exact",
            "participants": [
                {"user_id": user_a.id, "paid_share": "100.00", "owed_share": "50.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_create_expense_non_member_participant(client, group_with_members, user_a, db):
    from app.models import User
    from app.auth.security import hash_password

    outsider = User(name="Zoe", email="zoe@example.com", password_hash=hash_password("password123"))
    db.add(outsider)
    db.commit()

    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Sneaky",
            "total_amount": "10.00",
            "split_type": "exact",
            "participants": [
                {"user_id": outsider.id, "paid_share": "10.00", "owed_share": "10.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_create_expense_non_member_user_cannot_access(client, group_with_members, db):
    from app.models import User
    from app.auth.security import hash_password

    outsider = User(name="Zoe", email="zoe@example.com", password_hash=hash_password("password123"))
    db.add(outsider)
    db.commit()
    headers = _auth_headers_for(client, outsider.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Hack",
            "total_amount": "10.00",
            "split_type": "exact",
            "participants": [
                {"user_id": outsider.id, "paid_share": "10.00", "owed_share": "10.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 403


def test_list_expenses(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "total_amount": "30.00",
            "split_type": "equal",
            "participants": [
                {"user_id": user_a.id, "paid_share": "30.00", "owed_share": "30.00"},
            ],
        },
        headers=headers,
    )
    resp = client.get(f"/groups/{gid}/expenses", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_delete_expense(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    create = client.post(
        f"/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "total_amount": "30.00",
            "split_type": "equal",
            "participants": [
                {"user_id": user_a.id, "paid_share": "30.00", "owed_share": "30.00"},
            ],
        },
        headers=headers,
    )
    eid = create.json()["id"]
    resp = client.delete(f"/groups/{gid}/expenses/{eid}", headers=headers)
    assert resp.status_code == 204
