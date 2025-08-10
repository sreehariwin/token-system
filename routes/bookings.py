# routes/bookings.py - Enhanced with customer management and time restrictions
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from config import get_db
from models.bookings import (
    BookingRequest, BookingResponse, UpdateBookingStatusRequest,
    BookingDetailsResponse, BookingUpdateRequest, CancelBookingRequest,
    RatingRequest
)
from tables.bookings import Booking
from tables.slots import Slot
from tables.users import Users
from repository.users import get_current_user
from datetime import datetime, timedelta
from typing import List, Optional
from utils.notifications import NotificationService


router = APIRouter(prefix="/bookings", tags=["Bookings"])

def can_modify_booking(slot_datetime: datetime) -> bool:
    """Check if booking can be modified (2 hours before start time)"""
    current_time = datetime.utcnow()
    time_diff = slot_datetime - current_time
    return time_diff.total_seconds() > 7200  # 2 hours = 7200 seconds

@router.post("/book", response_model=BookingResponse)
async def book_slot( 
    req: BookingRequest, 
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    """Book a slot for customer"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Barbers cannot book slots")

    # Get slot with barber details
    slot = db.query(Slot).options(
        joinedload(Slot.barber)
    ).filter(
        Slot.id == req.slot_id, 
        Slot.is_booked == False
    ).first()
    
    if not slot:
        raise HTTPException(status_code=400, detail="Invalid or already booked slot")

    # Check if slot is in the future
    slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
    if slot_datetime <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot book slots in the past")

    # Check if customer already has a booking at the same time
    existing_booking = db.query(Booking).join(Slot).filter(
        and_(
            Booking.customer_id == current_user.id,
            Slot.slot_date == slot.slot_date,
            Slot.start_time == slot.start_time,
            Booking.status.in_(["pending", "confirmed"])
        )
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=400, 
            detail="You already have a booking at this time"
        )

    # Create booking
    slot.is_booked = True
    slot.booked_by = current_user.id
    booking = Booking(
        customer_id=current_user.id, 
        slot_id=slot.id,
        special_requests=req.special_requests
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)

    try:
        print(f"🔔 Sending booking notification for booking {booking.id}")
        print(f"📧 Customer: {current_user.first_name} {current_user.last_name}")
        print(f"💈 Barber: {slot.barber.first_name} {slot.barber.last_name}")
        print(f"🔔 Customer FCM: {current_user.fcm_token is not None}")
        print(f"🔔 Barber FCM: {slot.barber.fcm_token is not None}")
        
        # ADD 'await' HERE:
        await NotificationService.notify_booking_received(db, booking, current_user, slot.barber)
        
        # Also notify customer if booking is auto-confirmed
        if booking.status == "confirmed":
            await NotificationService.notify_booking_confirmed(db, booking, current_user, slot.barber)
        
        print(f"✅ Notifications sent successfully for booking {booking.id}")
        
    except Exception as e:
        print(f"❌ Notification error (booking still created): {e}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")

    return BookingResponse(
        booking_id=booking.id,
        slot_id=slot.id,
        status=booking.status,
        booked_at=booking.booked_at,
        slot_date=slot.slot_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        barber_name=f"{slot.barber.first_name} {slot.barber.last_name}",
        shop_name=slot.barber.shop_name,
        can_modify=can_modify_booking(slot_datetime)
    )

@router.get("/my", response_model=List[BookingDetailsResponse])
def get_my_bookings(
    status: Optional[str] = Query(None, description="Filter by status"),
    upcoming_only: bool = Query(False, description="Show only upcoming bookings"),
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    """Get customer's bookings with full details"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Barbers can't view this endpoint")

    query = db.query(Booking).options(
        joinedload(Booking.slot).joinedload(Slot.barber)
    ).filter(Booking.customer_id == current_user.id)
    
    if status:
        query = query.filter(Booking.status == status)
    
    if upcoming_only:
        current_date = datetime.utcnow().date()
        query = query.join(Slot).filter(Slot.slot_date >= current_date)
    
    bookings = query.order_by(Slot.slot_date.desc(), Slot.start_time.desc()).all()
    
    result = []
    for booking in bookings:
        slot = booking.slot
        barber = slot.barber
        slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
        
        result.append(BookingDetailsResponse(
            booking_id=booking.id,
            slot_id=slot.id,
            status=booking.status,
            booked_at=booking.booked_at,
            slot_date=slot.slot_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            barber_id=barber.id,
            barber_name=f"{barber.first_name} {barber.last_name}",
            shop_name=barber.shop_name,
            shop_address=barber.shop_address,
            shop_image_url=barber.shop_image_url,
            barber_phone=barber.phone_number,
            special_requests=booking.special_requests,
            can_modify=can_modify_booking(slot_datetime),
            is_past=slot_datetime < datetime.utcnow()
        ))
    
    return result

@router.post("/{booking_id}/rate")
def rate_booking(
    booking_id: int,
    req: RatingRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Rate and review a completed booking"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only customers can rate bookings")

    # Get booking
    booking = db.query(Booking).options(
        joinedload(Booking.slot).joinedload(Slot.barber)
    ).filter(
        and_(
            Booking.id == booking_id,
            Booking.customer_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Can only rate completed bookings")

    if booking.rating is not None:
        raise HTTPException(status_code=400, detail="Booking has already been rated")

    # Add rating and review
    booking.rating = req.rating
    booking.review_text = req.review_text
    booking.updated_at = datetime.utcnow()
    
    db.commit()

    return {
        "message": "Rating submitted successfully",
        "booking_id": booking_id,
        "rating": req.rating,
        "barber_name": f"{booking.slot.barber.first_name} {booking.slot.barber.last_name}",
        "shop_name": booking.slot.barber.shop_name
    }

@router.put("/{booking_id}", response_model=BookingDetailsResponse)
def update_booking(
    booking_id: int,
    req: BookingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Update booking details (only before 2 hours of start time)"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only customers can update their bookings")

    # Get booking with slot and barber details
    booking = db.query(Booking).options(
        joinedload(Booking.slot).joinedload(Slot.barber)
    ).filter(
        and_(
            Booking.id == booking_id,
            Booking.customer_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    slot = booking.slot
    slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
    
    # Check if booking can be modified
    if not can_modify_booking(slot_datetime):
        raise HTTPException(
            status_code=400, 
            detail="Cannot modify booking within 2 hours of start time"
        )

    if booking.status in ["cancelled", "completed"]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot modify cancelled or completed bookings"
        )

    # Handle slot change
    if req.new_slot_id and req.new_slot_id != slot.id:
        # Get new slot
        new_slot = db.query(Slot).filter(
            and_(
                Slot.id == req.new_slot_id,
                Slot.is_booked == False
            )
        ).first()
        
        if not new_slot:
            raise HTTPException(status_code=400, detail="New slot not available")

        new_slot_datetime = datetime.combine(new_slot.slot_date, new_slot.start_time)
        if not can_modify_booking(new_slot_datetime):
            raise HTTPException(
                status_code=400, 
                detail="Cannot reschedule to a slot within 2 hours"
            )

        # Free current slot and book new slot
        slot.is_booked = False
        slot.booked_by = None
        
        new_slot.is_booked = True
        new_slot.booked_by = current_user.id
        
        booking.slot_id = new_slot.id
        slot = new_slot

    # Update special requests
    if req.special_requests is not None:
        booking.special_requests = req.special_requests

    # Update last modified time
    booking.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(booking)

    # Return updated booking details
    barber = slot.barber
    return BookingDetailsResponse(
        booking_id=booking.id,
        slot_id=slot.id,
        status=booking.status,
        booked_at=booking.booked_at,
        slot_date=slot.slot_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        barber_id=barber.id,
        barber_name=f"{barber.first_name} {barber.last_name}",
        shop_name=barber.shop_name,
        shop_address=barber.shop_address,
        shop_image_url=barber.shop_image_url,
        barber_phone=barber.phone_number,
        special_requests=booking.special_requests,
        can_modify=can_modify_booking(datetime.combine(slot.slot_date, slot.start_time)),
        is_past=False
    )

@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    req: CancelBookingRequest = CancelBookingRequest(),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Cancel a booking (only before 2 hours of start time)"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only customers can cancel their bookings")

    # Get booking with slot details
    booking = db.query(Booking).options(
        joinedload(Booking.slot)
    ).filter(
        and_(
            Booking.id == booking_id,
            Booking.customer_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed booking")

    slot = booking.slot
    slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
    
    # Check if booking can be cancelled
    if not can_modify_booking(slot_datetime):
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel booking within 2 hours of start time"
        )

    # Cancel booking and free slot
    booking.status = "cancelled"
    booking.cancellation_reason = req.reason
    booking.cancelled_at = datetime.utcnow()
    
    slot.is_booked = False
    slot.booked_by = None
    
    NotificationService.notify_booking_cancelled(db, booking, current_user, slot.barber, cancelled_by_barber=False)

    db.commit()

    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking_id,
        "cancelled_at": booking.cancelled_at,
        "reason": req.reason
    }

@router.get("/barber")
def get_bookings_for_barber(
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db), 
    current_user: Users = Depends(get_current_user)
):
    """Get bookings for barber with enhanced filtering"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can access this")

    query = db.query(Booking).options(
        joinedload(Booking.slot),
        joinedload(Booking.customer)
    ).join(Slot).filter(Slot.barber_id == current_user.id)
    
    if status:
        query = query.filter(Booking.status == status)
    
    if date_from:
        query = query.filter(Slot.slot_date >= date_from)
    
    if date_to:
        query = query.filter(Slot.slot_date <= date_to)
    
    bookings = query.order_by(Slot.slot_date.desc(), Slot.start_time.desc()).all()
    
    result = []
    for booking in bookings:
        slot = booking.slot
        customer = booking.customer
        slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
        
        result.append({
            "booking_id": booking.id,
            "slot_id": slot.id,
            "status": booking.status,
            "booked_at": booking.booked_at,
            "slot_date": slot.slot_date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "customer_id": customer.id,
            "customer_name": f"{customer.first_name} {customer.last_name}",
            "customer_phone": customer.phone_number,
            "special_requests": booking.special_requests,
            "is_past": slot_datetime < datetime.utcnow(),
            "can_modify": can_modify_booking(slot_datetime)
        })
    
    return result

@router.put("/barber/status")
def update_booking_status(
    req: UpdateBookingStatusRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Update booking status by barber"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can update booking status")

    booking = db.query(Booking).options(
        joinedload(Booking.slot)
    ).join(Slot).filter(
        and_(
            Booking.id == req.booking_id,
            Slot.barber_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found or not your slot")

    # Validate status transition
    valid_statuses = ["pending", "confirmed", "in_progress", "completed", "cancelled", "no_show"]
    if req.new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    old_status = booking.status
    booking.status = req.new_status
    booking.updated_at = datetime.utcnow()
    
    # Handle status-specific logic
    if req.new_status == "completed":
        booking.completed_at = datetime.utcnow()
    elif req.new_status == "cancelled":
        booking.cancelled_at = datetime.utcnow()
        # Free the slot
        booking.slot.is_booked = False
        booking.slot.booked_by = None
    
    if req.new_status == "confirmed":
        NotificationService.notify_booking_confirmed(db, booking, booking.customer, current_user)
    elif req.new_status == "cancelled":
        NotificationService.notify_booking_cancelled(db, booking, booking.customer, current_user, cancelled_by_barber=True)
    
    db.commit()
    db.refresh(booking)
    
    return {
        "message": f"Status updated from {old_status} to {req.new_status}",
        "booking_id": booking.id,
        "old_status": old_status,
        "new_status": booking.status,
        "updated_at": booking.updated_at
    }

@router.get("/upcoming")
def get_upcoming_bookings(
    days_ahead: int = Query(7, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get upcoming bookings for customer"""
    if current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only customers can use this endpoint")

    end_date = (datetime.utcnow() + timedelta(days=days_ahead)).date()
    
    bookings = db.query(Booking).options(
        joinedload(Booking.slot).joinedload(Slot.barber)
    ).join(Slot).filter(
        and_(
            Booking.customer_id == current_user.id,
            Slot.slot_date >= datetime.utcnow().date(),
            Slot.slot_date <= end_date,
            Booking.status.in_(["pending", "confirmed", "in_progress"])
        )
    ).order_by(Slot.slot_date, Slot.start_time).all()

    result = []
    for booking in bookings:
        slot = booking.slot
        barber = slot.barber
        slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
        
        result.append({
            "booking_id": booking.id,
            "slot_date": slot.slot_date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "barber_name": f"{barber.first_name} {barber.last_name}",
            "shop_name": barber.shop_name,
            "status": booking.status,
            "can_modify": can_modify_booking(slot_datetime),
            "time_until": str(slot_datetime - datetime.utcnow()).split('.')[0] if slot_datetime > datetime.utcnow() else "Past"
        })
    
    return result