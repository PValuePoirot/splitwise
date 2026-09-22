"""Group routes: create, list, detail, add/remove members, balances."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Group, GroupMember, User
from app.schemas import (
    AddMemberRequest,
    GroupBalances,
    GroupCreate,
    GroupDetail,
    GroupOut,
    MemberOut,
    SimplifiedDebt,
    UserBalance,
)
from app.services.balances import (
    compute_group_balances,
    get_group_or_404,
    is_group_member,
    simplify_debts,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Group]:
    rows = db.scalars(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == current_user.id)
        .order_by(Group.created_at.desc())
    ).all()
    return list(rows)


@router.post("", response_model=GroupDetail, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Group:
    group = Group(name=payload.name, currency=payload.currency.upper(), created_by=current_user.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=current_user.id))
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Group:
    group = get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    return group


@router.post("/{group_id}/members", response_model=GroupDetail)
def add_member(
    group_id: int,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Group:
    group = get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")

    invitee = db.scalar(select(User).where(User.email == payload.email))
    if invitee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that email does not exist. Ask them to register first.",
        )
    if is_group_member(db, group_id, invitee.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")
    db.add(GroupMember(group_id=group_id, user_id=invitee.id))
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
def remove_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")

    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    db.delete(membership)
    db.commit()


@router.get("/{group_id}/balances", response_model=GroupBalances)
def get_balances(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupBalances:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    balances = compute_group_balances(db, group_id)
    debts = simplify_debts(balances)
    return GroupBalances(
        balances=[UserBalance(user_id=b.user_id, name=b.name, balance=b.balance) for b in balances],
        simplified_debts=[
            SimplifiedDebt(
                from_user_id=d.from_user_id,
                from_name=d.from_name,
                to_user_id=d.to_user_id,
                to_name=d.to_name,
                amount=d.amount,
            )
            for d in debts
        ],
    )
