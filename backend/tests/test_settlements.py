"""Tests for the settlements module."""
from __future__ import annotations


def _auth_headers_for(client, email: str) -> dict[str, str]:
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_create_settlement(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    bob_id = group_with_members.members[1].user_id
    resp = client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": bob_id, "to_user_id": user_a.id, "amount": "25.00"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["from_user"] == bob_id
    assert data["to_user"] == user_a.id
    assert data["amount"] == "25.00"


def test_settlement_self_payment_rejected(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": user_a.id, "to_user_id": user_a.id, "amount": "10.00"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_settlement_non_member_rejected(client, group_with_members, user_a, db):
    from app.models import User
    from app.auth.security import hash_password

    outsider = User(name="Zoe", email="zoe@example.com", password_hash=hash_password("password123"))
    db.add(outsider)
    db.commit()
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": outsider.id, "to_user_id": user_a.id, "amount": "10.00"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_list_settlements(client, group_with_members, user_a):
    headers = _auth_headers_for(client, user_a.email)
    gid = group_with_members.id
    bob_id = group_with_members.members[1].user_id
    client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": bob_id, "to_user_id": user_a.id, "amount": "25.00"},
        headers=headers,
    )
    resp = client.get(f"/groups/{gid}/settlements", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_settlement_forbidden_for_non_member(client, group_with_members, db):
    from app.models import User
    from app.auth.security import hash_password

    outsider = User(name="Zoe", email="zoe@example.com", password_hash=hash_password("password123"))
    db.add(outsider)
    db.commit()
    headers = _auth_headers_for(client, outsider.email)
    gid = group_with_members.id
    resp = client.post(
        f"/groups/{gid}/settlements",
        json={"from_user_id": outsider.id, "to_user_id": group_with_members.created_by, "amount": "10.00"},
        headers=headers,
    )
    assert resp.status_code == 403
