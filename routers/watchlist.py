from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import CompanyWatchlist
from schemas import WatchlistCreateRequest, WatchlistResponse

router = APIRouter(tags=["Watchlist"])


@router.get("/watchlist", response_model=List[WatchlistResponse])
def list_company_watchlist(db: Session = Depends(get_db)):
    """List all target company ATS watchlists."""
    return db.query(CompanyWatchlist).order_by(CompanyWatchlist.id.asc()).all()


@router.get("/watchlist/{id}", response_model=WatchlistResponse)
def get_watchlist_item_by_id(id: int, db: Session = Depends(get_db)):
    """Get watchlist item details by ID."""
    item = db.query(CompanyWatchlist).filter(CompanyWatchlist.id == id).first()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"watchlist id {id} does not exist"},
        )
    return item


@router.post("/watchlist", response_model=WatchlistResponse, status_code=201)
def create_watchlist_item(payload: WatchlistCreateRequest, db: Session = Depends(get_db)):
    """Add a company to the ATS watchlist."""
    existing = db.query(CompanyWatchlist).filter(CompanyWatchlist.company == payload.company).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate_company", "detail": f"company '{payload.company}' already in watchlist"},
        )

    item = CompanyWatchlist(
        company=payload.company,
        ats=payload.ats,
        token=payload.token,
        active=payload.active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/watchlist/{id}", response_model=WatchlistResponse)
def update_watchlist_item(id: int, payload: WatchlistCreateRequest, db: Session = Depends(get_db)):
    """Update an existing watchlist entry by ID."""
    item = db.query(CompanyWatchlist).filter(CompanyWatchlist.id == id).first()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"watchlist id {id} does not exist"},
        )

    item.company = payload.company
    item.ats = payload.ats
    item.token = payload.token
    item.active = payload.active
    db.commit()
    db.refresh(item)
    return item


@router.delete("/watchlist/{id}", status_code=204)
def delete_watchlist_item(id: int, db: Session = Depends(get_db)):
    """Delete a company from the ATS watchlist by ID."""
    item = db.query(CompanyWatchlist).filter(CompanyWatchlist.id == id).first()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"watchlist id {id} does not exist"},
        )
    db.delete(item)
    db.commit()
    return None
