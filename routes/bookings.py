from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config import get_db
from models.bookings import BookingRequest, BookingResponse, UpdateBookingStatusRequest
from tables.bookings import Booking
from tables.slots import Slot
from repository.users import get_current_user
from tables.users import Users

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/book", response_model=BookingResponse)
def book_slot(req: BookingRequest, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Barbers cannot book slots")

    slot = db.query(Slot).filter(Slot.id == req.slot_id, Slot.is_booked == False).first()
    if not slot:
        raise HTTPException(status_code=400, detail="Invalid or already booked slot")

    slot.is_booked = True
    slot.booked_by = current_user.id
    booking = Booking(customer_id=current_user.id, slot_id=slot.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingResponse(
        booking_id=booking.id,
        slot_id=slot.id,
        status=booking.status,
        booked_at=booking.booked_at
    )

@router.get("/barber")
def get_bookings_for_barber(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can access this")

    bookings = (
        db.query(Booking)
        .join(Slot, Booking.slot_id == Slot.id)
        .filter(Slot.barber_id == current_user.id)
        .all()
    )
    return bookings

@router.put("/barber/status")
def update_booking_status(
    req: UpdateBookingStatusRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can update booking status")

    booking = (
        db.query(Booking)
        .join(Slot, Booking.slot_id == Slot.id)
        .filter(Booking.id == req.booking_id, Slot.barber_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or not your slot")

    booking.status = req.new_status
    db.commit()
    db.refresh(booking)
    return {"message": "Status updated", "booking_id": booking.id, "status": booking.status}

@router.get("/my")
def get_my_bookings(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Barbers can't view this endpoint")

    bookings = db.query(Booking).filter(Booking.customer_id == current_user.id).all()
    return bookings
