# routes/slots.py - Updated to allow multiple slots at same time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from config import get_db
from models.slots import (
    SlotCreate, SlotCreateBulk, SlotResponse, SlotFilter, 
    SlotCreateMultiple, SlotTimeCount, SlotCountResponse, 
    BulkDeleteRequest, TemplateGenerateRequest
)
from tables.slots import Slot
from repository.users import get_current_user
from tables.users import Users
from datetime import date, time, datetime, timedelta
from typing import Optional, List

router = APIRouter(prefix="/slots", tags=["Slots"])

@router.post("/", response_model=SlotResponse)
def create_slot(
    slot_data: SlotCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Create a single slot - allows multiple slots at same time"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can create slots")

    # REMOVED: Overlap validation to allow multiple slots at same time
    # Barbers can now create multiple slots with identical times

    # Create slot_time for backward compatibility
    slot_datetime = datetime.combine(slot_data.slot_date, slot_data.start_time)

    new_slot = Slot(
        barber_id=current_user.id,
        slot_date=slot_data.slot_date,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time,
        slot_time=slot_datetime  # For backward compatibility
    )
    
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot

@router.post("/bulk", response_model=List[SlotResponse])
def create_bulk_slots(
    slot_data: SlotCreateBulk,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Create multiple slots - supports different times and counts"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can create slots")

    created_slots = []
    
    for time_slot in slot_data.time_slots:
        start_time = time.fromisoformat(time_slot['start_time'])
        end_time = time.fromisoformat(time_slot['end_time'])
        count = time_slot.get('count', 1)  # Default to 1 if not specified
        
        # Create multiple slots for this time slot
        for i in range(count):
            slot_datetime = datetime.combine(slot_data.slot_date, start_time)
            
            new_slot = Slot(
                barber_id=current_user.id,
                slot_date=slot_data.slot_date,
                start_time=start_time,
                end_time=end_time,
                slot_time=slot_datetime
            )
            
            db.add(new_slot)
            created_slots.append(new_slot)
    
    db.commit()
    
    # Refresh all created slots
    for slot in created_slots:
        db.refresh(slot)
    
    return created_slots

@router.post("/create-multiple", response_model=List[SlotResponse])
def create_multiple_identical_slots(
    slot_data: SlotCreate,
    count: int = Query(..., description="Number of identical slots to create", ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Create multiple identical slots with same date/time"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can create slots")

    if count > 50:
        raise HTTPException(status_code=400, detail="Cannot create more than 50 slots at once")

    created_slots = []
    slot_datetime = datetime.combine(slot_data.slot_date, slot_data.start_time)

    for i in range(count):
        new_slot = Slot(
            barber_id=current_user.id,
            slot_date=slot_data.slot_date,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            slot_time=slot_datetime
        )
        
        db.add(new_slot)
        created_slots.append(new_slot)
    
    db.commit()
    
    # Refresh all created slots
    for slot in created_slots:
        db.refresh(slot)
    
    return created_slots

@router.get("/", response_model=List[SlotResponse])
def get_available_slots(
    start_date: Optional[date] = Query(None, description="Filter slots from this date"),
    end_date: Optional[date] = Query(None, description="Filter slots until this date"),
    barber_id: Optional[int] = Query(None, description="Filter slots by barber ID"),
    available_only: bool = Query(True, description="Show only available slots"),
    db: Session = Depends(get_db)
):
    """Get slots with filtering options"""
    query = db.query(Slot)
    
    # Apply filters
    if available_only:
        query = query.filter(Slot.is_booked == False)
    
    if barber_id:
        query = query.filter(Slot.barber_id == barber_id)
    
    if start_date:
        query = query.filter(Slot.slot_date >= start_date)
    else:
        # Default to today if no start date provided
        query = query.filter(Slot.slot_date >= date.today())
    
    if end_date:
        query = query.filter(Slot.slot_date <= end_date)
    
    # Order by date, start time, and slot ID to show multiple slots at same time
    slots = query.order_by(Slot.slot_date, Slot.start_time, Slot.id).all()
    return slots

@router.get("/by-date/{slot_date}", response_model=List[SlotResponse])
def get_slots_by_date(
    slot_date: date,
    barber_id: Optional[int] = Query(None),
    available_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get all slots for a specific date"""
    query = db.query(Slot).filter(Slot.slot_date == slot_date)
    
    if available_only:
        query = query.filter(Slot.is_booked == False)
    
    if barber_id:
        query = query.filter(Slot.barber_id == barber_id)
    
    # Order by start time and slot ID to show multiple slots at same time
    slots = query.order_by(Slot.start_time, Slot.id).all()
    return slots

@router.get("/barber/my-slots")
def get_barber_slots(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_booked: bool = Query(True, description="Include booked slots"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get barber's own slots with filtering"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can access this")
    
    query = db.query(Slot).filter(Slot.barber_id == current_user.id)
    
    if start_date:
        query = query.filter(Slot.slot_date >= start_date)
    else:
        query = query.filter(Slot.slot_date >= date.today())
    
    if end_date:
        query = query.filter(Slot.slot_date <= end_date)
    
    if not include_booked:
        query = query.filter(Slot.is_booked == False)
    
    # Order by date, start time, and slot ID to show multiple slots at same time
    slots = query.order_by(Slot.slot_date, Slot.start_time, Slot.id).all()
    return slots

@router.get("/count-by-time", response_model=SlotCountResponse)
def count_slots_by_time(
    slot_date: date = Query(..., description="Date to count slots for"),
    barber_id: Optional[int] = Query(None, description="Filter by specific barber"),
    db: Session = Depends(get_db)
):
    """Get count of slots grouped by time for a specific date"""
    query = db.query(Slot).filter(Slot.slot_date == slot_date)
    
    if barber_id:
        query = query.filter(Slot.barber_id == barber_id)
    
    slots = query.all()
    
    # Group slots by time
    time_counts = {}
    for slot in slots:
        time_key = f"{slot.start_time}-{slot.end_time}"
        if time_key not in time_counts:
            time_counts[time_key] = SlotTimeCount(
                start_time=slot.start_time,
                end_time=slot.end_time,
                total_slots=0,
                available_slots=0,
                booked_slots=0
            )
        
        time_counts[time_key].total_slots += 1
        if slot.is_booked:
            time_counts[time_key].booked_slots += 1
        else:
            time_counts[time_key].available_slots += 1
    
    return SlotCountResponse(
        date=slot_date,
        barber_id=barber_id,
        time_slots=list(time_counts.values())
    )

@router.delete("/{slot_id}")
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Delete a slot (only if not booked and belongs to current barber)"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can delete slots")
    
    slot = db.query(Slot).filter(
        and_(Slot.id == slot_id, Slot.barber_id == current_user.id)
    ).first()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Cannot delete booked slot")
    
    db.delete(slot)
    db.commit()
    
    return {"message": "Slot deleted successfully", "slot_id": slot_id}

@router.delete("/bulk-delete")
def bulk_delete_slots(
    slot_date: date = Query(..., description="Date to delete slots from"),
    start_time: Optional[time] = Query(None, description="Start time filter"),
    end_time: Optional[time] = Query(None, description="End time filter"),
    unbooked_only: bool = Query(True, description="Only delete unbooked slots"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Delete multiple slots matching criteria"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can delete slots")
    
    query = db.query(Slot).filter(
        and_(
            Slot.barber_id == current_user.id,
            Slot.slot_date == slot_date
        )
    )
    
    if start_time:
        query = query.filter(Slot.start_time == start_time)
    
    if end_time:
        query = query.filter(Slot.end_time == end_time)
    
    if unbooked_only:
        query = query.filter(Slot.is_booked == False)
    
    slots_to_delete = query.all()
    
    if not slots_to_delete:
        raise HTTPException(status_code=404, detail="No slots found matching criteria")
    
    # Check if any slots are booked (if unbooked_only is False)
    if not unbooked_only:
        booked_slots = [slot for slot in slots_to_delete if slot.is_booked]
        if booked_slots:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete {len(booked_slots)} booked slots"
            )
    
    deleted_count = len(slots_to_delete)
    
    # Delete the slots
    for slot in slots_to_delete:
        db.delete(slot)
    
    db.commit()
    
    return {
        "message": f"Successfully deleted {deleted_count} slots",
        "deleted_count": deleted_count,
        "date": slot_date
    }

@router.get("/generate-template")
def generate_weekly_template(
    start_date: date = Query(..., description="Start date for the week"),
    daily_slots: str = Query(
        "09:00-10:00,10:00-11:00,11:00-12:00,14:00-15:00,15:00-16:00,16:00-17:00",
        description="Comma-separated time slots in format 'HH:MM-HH:MM'"
    ),
    slots_per_time: int = Query(1, description="Number of slots to create per time slot", ge=1, le=10),
    exclude_weekends: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Generate slots for a week based on template with multiple slots per time"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can generate slots")
    
    # Parse daily slots
    try:
        time_slots = []
        for slot_str in daily_slots.split(','):
            start_str, end_str = slot_str.strip().split('-')
            time_slots.append({
                'start_time': start_str.strip(),
                'end_time': end_str.strip()
            })
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid time slot format. Use 'HH:MM-HH:MM,HH:MM-HH:MM'"
        )
    
    created_slots = []
    current_date = start_date
    
    # Generate for 7 days
    for _ in range(7):
        # Skip weekends if requested
        if exclude_weekends and current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            current_date += timedelta(days=1)
            continue
        
        for time_slot in time_slots:
            try:
                start_time = time.fromisoformat(time_slot['start_time'])
                end_time = time.fromisoformat(time_slot['end_time'])
                
                # Create multiple slots for each time slot
                for slot_num in range(slots_per_time):
                    slot_datetime = datetime.combine(current_date, start_time)
                    new_slot = Slot(
                        barber_id=current_user.id,
                        slot_date=current_date,
                        start_time=start_time,
                        end_time=end_time,
                        slot_time=slot_datetime
                    )
                    db.add(new_slot)
                    created_slots.append(new_slot)
                    
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
        
        current_date += timedelta(days=1)
    
    db.commit()
    
    return {
        "message": f"Generated {len(created_slots)} slots successfully",
        "slots_created": len(created_slots),
        "slots_per_time": slots_per_time,
        "start_date": start_date,
        "end_date": current_date - timedelta(days=1)
    }