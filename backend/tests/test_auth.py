"""Tests for the auth module."""
from __future__ import annotations


def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Dave", "email": "dave@example.com", "password": "strongpass1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "dave@example.com"
    assert data["name"] == "Dave"
    assert "password_hash" not in data
    assert "password" not in data


def test_register_duplicate_email(client, user_a):
    resp = client.post(
        "/auth/register",
        json={"name": "Alice2", "email": "alice@example.com", "password": "strongpass1"},
    )
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Dave", "email": "dave@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_login_success(client, user_a):
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, user_a):
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_user(client, auth_headers, user_a):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user_a.email


def test_refresh_token(client, user_a):
    login = client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"})
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_invalid_token(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code == 401
