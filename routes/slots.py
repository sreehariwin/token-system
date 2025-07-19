# routes/slots.py (was routes/slotes.py)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config import get_db
from models.slots import SlotCreate, SlotResponse
from tables.slots import Slot
from repository.users import get_current_user
from tables.users import Users

router = APIRouter(prefix="/slots", tags=["Slots"])

@router.post("/", response_model=SlotResponse)
def create_slot(
    slot_data: SlotCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can create slots")

    new_slot = Slot(
        slot_time=slot_data.slot_time,
        barber_id=current_user.id
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot

@router.get("/", response_model=list[SlotResponse])
def get_available_slots(db: Session = Depends(get_db)):
    slots = db.query(Slot).filter(Slot.is_booked == False).all()
    return slots

@router.get("/barber/my-slots")
def get_barber_slots(
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can access this")
    
    slots = db.query(Slot).filter(Slot.barber_id == current_user.id).all()
    return slots
