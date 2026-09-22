"""Settlement routes: record and list payments."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Settlement, User
from app.schemas import SettlementCreate, SettlementOut
from app.services.balances import get_group_or_404, is_group_member

router = APIRouter(prefix="/groups/{group_id}/settlements", tags=["settlements"])


@router.get("", response_model=list[SettlementOut])
def list_settlements(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Settlement]:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    return list(
        db.scalars(
            select(Settlement)
            .where(Settlement.group_id == group_id)
            .order_by(Settlement.created_at.desc())
        ).all()
    )


@router.post("", response_model=SettlementOut, status_code=status.HTTP_201_CREATED)
def create_settlement(
    group_id: int,
    payload: SettlementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Settlement:
    get_group_or_404(db, group_id)
    if not is_group_member(db, group_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")

    if payload.from_user_id == payload.to_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot settle with yourself")

    if not is_group_member(db, group_id, payload.from_user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payer is not a group member")
    if not is_group_member(db, group_id, payload.to_user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payee is not a group member")

    settlement = Settlement(
        group_id=group_id,
        from_user=payload.from_user_id,
        to_user=payload.to_user_id,
        amount=payload.amount,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement
