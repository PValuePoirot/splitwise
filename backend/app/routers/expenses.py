"""Expense routes: create, list, detail, delete."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Expense, ExpenseParticipant, Group, User
from app.schemas import ExpenseCreate, ExpenseOut, ParticipantOut
from app.services.balances import get_group_or_404, is_group_member

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])


def _validate_expense(payload: ExpenseCreate, db: Session, group_id: int) -> None:
    """Validate sums and membership before persisting."""
    member_ids = {
        row[0]
        for row in db.execute(
            select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        )
    }
    if not member_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    participant_ids = {p.user_id for p in payload.participants}
    if not participant_ids.issubset(member_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All participants must be members of the group",
        )

    paid_total = sum((p.paid_share for p in payload.participants), Decimal("0"))
    owed_total = sum((p.owed_share for p in payload.participants), Decimal("0"))

    if abs(paid_total - payload.total_amount) > Decimal("0.01"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sum of paid shares ({paid_total}) must equal total amount ({payload.total_amount})",
        )
    if abs(owed_total - payload.total_amount) > Decimal("0.01"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sum of owed shares ({owed_total}) must equal total amount ({payload.total_amount})",
        )

    if payload.split_type == "percentage":
        for p in payload.participants:
            if p.owed_share < 0 or p.owed_share > Decimal("100"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Percentage owed shares must be between 0 and 100",
                )


# Import GroupMember here to avoid circular import at module load.
from app.models import GroupMember  # noqa: E402


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Expense]:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    return list(
        db.scalars(
            select(Expense)
            .where(Expense.group_id == group_id)
            .order_by(Expense.created_at.desc())
        ).all()
    )


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: int,
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Expense:
    group = get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")

    _validate_expense(payload, db, group_id)

    expense = Expense(
        group_id=group_id,
        description=payload.description,
        total_amount=payload.total_amount,
        split_type=payload.split_type,
        created_by=current_user.id,
    )
    db.add(expense)
    db.flush()
    for p in payload.participants:
        db.add(
            ExpenseParticipant(
                expense_id=expense.id,
                user_id=p.user_id,
                paid_share=p.paid_share,
                owed_share=p.owed_share,
            )
        )
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    group_id: int,
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Expense:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    expense = db.get(Expense, expense_id)
    if expense is None or expense.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
def delete_expense(
    group_id: int,
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    expense = db.get(Expense, expense_id)
    if expense is None or expense.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    db.delete(expense)
    db.commit()
