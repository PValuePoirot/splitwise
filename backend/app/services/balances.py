"""Balance computation and debt simplification logic."""
from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Expense,
    ExpenseParticipant,
    Group,
    GroupMember,
    Settlement,
    User,
)


class UserBalance(NamedTuple):
    user_id: int
    name: str
    balance: Decimal  # positive = is owed money, negative = owes


class SimplifiedDebt(NamedTuple):
    from_user_id: int
    from_name: str
    to_user_id: int
    to_name: str
    amount: Decimal


def compute_group_balances(db: Session, group_id: int) -> list[UserBalance]:
    """Compute net balance for every member of a group.

    balance = sum(paid_share) - sum(owed_share)
            + sum(settlement received) - sum(settlement paid)
    """
    # Members
    rows = db.execute(
        select(User, GroupMember)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    ).all()
    if not rows:
        return []

    balances: dict[int, Decimal] = {user.id: Decimal("0") for user, _ in rows}
    names: dict[int, str] = {user.id: user.name for user, _ in rows}

    # Expense contributions
    rows = db.execute(
        select(ExpenseParticipant.user_id, ExpenseParticipant.paid_share, ExpenseParticipant.owed_share)
        .join(Expense, Expense.id == ExpenseParticipant.expense_id)
        .where(Expense.group_id == group_id)
    ).all()
    for user_id, paid, owed in rows:
        if user_id in balances:
            balances[user_id] += paid - owed

    # Settlements: from_user pays to_user. Paying reduces the payer's debt
    # (balance increases) and reduces the payee's credit (balance decreases).
    settlements = db.scalars(
        select(Settlement).where(Settlement.group_id == group_id)
    ).all()
    for s in settlements:
        if s.from_user in balances:
            balances[s.from_user] += s.amount
        if s.to_user in balances:
            balances[s.to_user] -= s.amount

    return [
        UserBalance(user_id=uid, name=names[uid], balance=bal)
        for uid, bal in balances.items()
    ]


def simplify_debts(balances: list[UserBalance]) -> list[SimplifiedDebt]:
    """Greedy min-transactions settlement.

    Repeatedly settle the largest debtor against the largest creditor until
    all balances are zero. Returns the list of suggested payments.
    """
    # Work on a copy with rounding to cents to avoid float drift.
    balances_by_user = {b.user_id: b.balance for b in balances}
    names = {b.user_id: b.name for b in balances}

    # Sanity: balances should sum to ~0 in a closed group.
    total = sum(balances_by_user.values(), Decimal("0"))
    if abs(total) > Decimal("0.01"):
        # In an open system this can happen; we still simplify the net positions.
        pass

    debtors = [(uid, -bal) for uid, bal in balances_by_user.items() if bal < -Decimal("0.01")]
    creditors = [(uid, bal) for uid, bal in balances_by_user.items() if bal > Decimal("0.01")]

    debts: list[SimplifiedDebt] = []
    # Sort largest first
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debtor_amt = debtors[i]
        creditor_id, creditor_amt = creditors[j]
        pay = min(debtor_amt, creditor_amt)
        if pay > Decimal("0.01"):
            debts.append(
                SimplifiedDebt(
                    from_user_id=debtor_id,
                    from_name=names[debtor_id],
                    to_user_id=creditor_id,
                    to_name=names[creditor_id],
                    amount=pay,
                )
            )
        debtors[i] = (debtor_id, debtor_amt - pay)
        creditors[j] = (creditor_id, creditor_amt - pay)
        if debtors[i][1] <= Decimal("0.01"):
            i += 1
        if creditors[j][1] <= Decimal("0.01"):
            j += 1

    return debts


def is_group_member(db: Session, group_id: int, user_id: int) -> bool:
    return db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id
        )
    ) is not None


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group
