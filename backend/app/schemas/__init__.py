"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Groups ----------
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    currency: str
    created_by: int
    created_at: datetime


class GroupDetail(GroupOut):
    members: list["MemberOut"] = []


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    name: str
    email: str
    joined_at: datetime


class AddMemberRequest(BaseModel):
    email: EmailStr


# ---------- Expenses ----------
class ParticipantIn(BaseModel):
    user_id: int
    paid_share: Decimal = Field(default=Decimal("0"), ge=0)
    owed_share: Decimal = Field(default=Decimal("0"), ge=0)


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    total_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    split_type: str = Field(pattern="^(equal|exact|percentage)$")
    participants: list[ParticipantIn] = Field(min_length=1)

    @field_validator("participants")
    @classmethod
    def validate_participants_unique(cls, v: list[ParticipantIn]) -> list[ParticipantIn]:
        ids = [p.user_id for p in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate user_id in participants")
        return v


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    paid_share: Decimal
    owed_share: Decimal


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int
    description: str
    total_amount: Decimal
    split_type: str
    created_by: int
    created_at: datetime
    participants: list[ParticipantOut] = []


# ---------- Balances ----------
class UserBalance(BaseModel):
    user_id: int
    name: str
    balance: Decimal  # positive = owed money, negative = owes


class SimplifiedDebt(BaseModel):
    from_user_id: int
    from_name: str
    to_user_id: int
    to_name: str
    amount: Decimal


class GroupBalances(BaseModel):
    balances: list[UserBalance]
    simplified_debts: list[SimplifiedDebt]


# ---------- Settlements ----------
class SettlementCreate(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int
    from_user: int
    to_user: int
    amount: Decimal
    created_at: datetime


GroupDetail.model_rebuild()
