"""Tests for the groups module."""
from __future__ import annotations


def test_create_group(client, auth_headers):
    resp = client.post("/groups", json={"name": "Weekend Trip", "currency": "USD"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Weekend Trip"
    assert data["currency"] == "USD"
    # Creator is auto-added as a member.
    assert len(data["members"]) == 1


def test_list_groups_only_returns_my_groups(client, auth_headers, user_a, user_b, db):
    from app.models import Group, GroupMember

    # Group A: user_a is a member
    g_a = Group(name="A", currency="USD", created_by=user_a.id)
    db.add(g_a)
    db.flush()
    db.add(GroupMember(group_id=g_a.id, user_id=user_a.id))
    # Group B: only user_b
    g_b = Group(name="B", currency="USD", created_by=user_b.id)
    db.add(g_b)
    db.flush()
    db.add(GroupMember(group_id=g_b.id, user_id=user_b.id))
    db.commit()

    resp = client.get("/groups", headers=auth_headers)
    assert resp.status_code == 200
    names = {g["name"] for g in resp.json()}
    assert names == {"A"}


def test_get_group_forbidden_for_non_member(client, auth_headers, user_b, db):
    from app.models import Group, GroupMember

    g = Group(name="Private", currency="USD", created_by=user_b.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_b.id))
    db.commit()

    resp = client.get(f"/groups/{g.id}", headers=auth_headers)
    assert resp.status_code == 403


def test_get_group_not_found(client, auth_headers):
    resp = client.get("/groups/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_add_member_by_email(client, auth_headers, user_a, user_b, db):
    from app.models import Group, GroupMember

    g = Group(name="G", currency="USD", created_by=user_a.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_a.id))
    db.commit()

    resp = client.post(f"/groups/{g.id}/members", json={"email": "bob@example.com"}, headers=auth_headers)
    assert resp.status_code == 200
    emails = {m["email"] for m in resp.json()["members"]}
    assert "bob@example.com" in emails


def test_add_member_unknown_email(client, auth_headers, user_a, db):
    from app.models import Group, GroupMember

    g = Group(name="G", currency="USD", created_by=user_a.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_a.id))
    db.commit()

    resp = client.post(f"/groups/{g.id}/members", json={"email": "ghost@example.com"}, headers=auth_headers)
    assert resp.status_code == 404


def test_add_duplicate_member(client, auth_headers, user_a, user_b, db):
    from app.models import Group, GroupMember

    g = Group(name="G", currency="USD", created_by=user_a.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_a.id))
    db.add(GroupMember(group_id=g.id, user_id=user_b.id))
    db.commit()

    resp = client.post(f"/groups/{g.id}/members", json={"email": "bob@example.com"}, headers=auth_headers)
    assert resp.status_code == 409


def test_remove_member(client, auth_headers, user_a, user_b, db):
    from app.models import Group, GroupMember

    g = Group(name="G", currency="USD", created_by=user_a.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_a.id))
    db.add(GroupMember(group_id=g.id, user_id=user_b.id))
    db.commit()

    resp = client.delete(f"/groups/{g.id}/members/{user_b.id}", headers=auth_headers)
    assert resp.status_code == 204


def test_remove_member_not_found(client, auth_headers, user_a, db):
    from app.models import Group, GroupMember

    g = Group(name="G", currency="USD", created_by=user_a.id)
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=user_a.id))
    db.commit()

    resp = client.delete(f"/groups/{g.id}/members/9999", headers=auth_headers)
    assert resp.status_code == 404
