# routes/shops.py - New route for shop listings
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, distinct, or_
from config import get_db
from models.shops import ShopListResponse, ShopDetailsResponse, ShopSearchRequest
from tables.users import Users
from tables.slots import Slot
from tables.bookings import Booking
from repository.users import get_current_user
from datetime import datetime, date, timedelta
from typing import List, Optional

router = APIRouter(prefix="/shops", tags=["Shops"])

@router.get("/", response_model=List[ShopListResponse])
def list_all_shops(
    search: Optional[str] = Query(None, description="Search by shop name or address"),
    city: Optional[str] = Query(None, description="Filter by city"),
    has_available_slots: bool = Query(False, description="Only show shops with available slots"),
    limit: int = Query(50, description="Maximum number of shops to return", le=100),
    offset: int = Query(0, description="Number of shops to skip"),
    db: Session = Depends(get_db)
):
    """Get list of all barbershops with basic information"""
    
    query = db.query(Users).filter(
        and_(
            Users.is_barber == True,
            Users.shop_name.isnot(None)
        )
    )
    
    # Apply search filter
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Users.shop_name).like(search_term),
                func.lower(Users.shop_address).like(search_term),
                func.lower(Users.first_name).like(search_term),
                func.lower(Users.last_name).like(search_term)
            )
        )
    
    # Apply city filter
    if city:
        query = query.filter(func.lower(Users.shop_address).like(f"%{city.lower()}%"))
    
    # Get barbers
    barbers = query.offset(offset).limit(limit).all()
    
    result = []
    for barber in barbers:
        # Get available slots count if requested
        available_slots_count = 0
        if has_available_slots:
            available_slots_count = db.query(Slot).filter(
                and_(
                    Slot.barber_id == barber.id,
                    Slot.is_booked == False,
                    Slot.slot_date >= date.today()
                )
            ).count()
            
            # Skip shops with no available slots if filter is active
            if has_available_slots and available_slots_count == 0:
                continue
        
        # Get rating statistics
        rating_stats = db.query(
            func.avg(Booking.rating).label('avg_rating'),
            func.count(Booking.rating).label('total_reviews')
        ).join(Slot).filter(
            and_(
                Slot.barber_id == barber.id,
                Booking.rating.isnot(None)
            )
        ).first()
        
        avg_rating = float(rating_stats.avg_rating) if rating_stats.avg_rating else 0.0
        total_reviews = rating_stats.total_reviews or 0
        
        # Get next available slot
        next_slot = db.query(Slot).filter(
            and_(
                Slot.barber_id == barber.id,
                Slot.is_booked == False,
                Slot.slot_date >= date.today()
            )
        ).order_by(Slot.slot_date, Slot.start_time).first()
        
        result.append(ShopListResponse(
            barber_id=barber.id,
            shop_name=barber.shop_name,
            shop_address=barber.shop_address,
            shop_image_url=barber.shop_image_url,
            barber_name=f"{barber.first_name} {barber.last_name}",
            phone_number=barber.phone_number,
            license_number=barber.license_number,
            avg_rating=round(avg_rating, 1),
            total_reviews=total_reviews,
            available_slots_count=available_slots_count if has_available_slots else None,
            next_available_slot=next_slot.slot_date if next_slot else None,
            next_available_time=next_slot.start_time if next_slot else None,
            shop_status=barber.shop_status if barber.shop_status is not None else True,
        ))
    
    return result

@router.get("/{barber_id}", response_model=ShopDetailsResponse)
def get_shop_details(
    barber_id: int,
    include_slots: bool = Query(True, description="Include available slots"),
    days_ahead: int = Query(30, description="Days ahead to show slots", le=90),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific shop"""
    
    # Get barber details
    barber = db.query(Users).filter(
        and_(
            Users.id == barber_id,
            Users.is_barber == True
        )
    ).first()
    
    if not barber:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Get rating and review statistics
    rating_stats = db.query(
        func.avg(Booking.rating).label('avg_rating'),
        func.count(Booking.rating).label('total_reviews')
    ).join(Slot).filter(
        and_(
            Slot.barber_id == barber.id,
            Booking.rating.isnot(None)
        )
    ).first()
    
    avg_rating = float(rating_stats.avg_rating) if rating_stats.avg_rating else 0.0
    total_reviews = rating_stats.total_reviews or 0
    
    # Get recent reviews
    recent_reviews = db.query(Booking).options(
        joinedload(Booking.customer)
    ).join(Slot).filter(
        and_(
            Slot.barber_id == barber.id,
            Booking.rating.isnot(None),
            Booking.review_text.isnot(None)
        )
    ).order_by(Booking.completed_at.desc()).limit(5).all()
    
    reviews = []
    for booking in recent_reviews:
        reviews.append({
            "customer_name": f"{booking.customer.first_name} {booking.customer.last_name[0]}.",
            "rating": booking.rating,
            "review_text": booking.review_text,
            "date": booking.completed_at.date() if booking.completed_at else None
        })
    
    # Get available slots if requested
    available_slots = []
    if include_slots:
        end_date = date.today() + timedelta(days=days_ahead)
        
        slots = db.query(Slot).filter(
            and_(
                Slot.barber_id == barber.id,
                Slot.is_booked == False,
                Slot.slot_date >= date.today(),
                Slot.slot_date <= end_date
            )
        ).order_by(Slot.slot_date, Slot.start_time).all()
        
        for slot in slots:
            available_slots.append({
                "slot_id": slot.id,
                "slot_date": slot.slot_date,
                "start_time": slot.start_time,
                "end_time": slot.end_time
            })
    
    # Get business hours (you might want to add this to the users table)
    # For now, we'll derive it from available slots
    business_hours = {}
    if include_slots:
        for day in range(7):  # 0 = Monday, 6 = Sunday
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            # This is a simplified way - you might want a separate business_hours table
            business_hours[day_name] = "9:00 AM - 6:00 PM"  # Default hours
    
    return ShopDetailsResponse(
        barber_id=barber.id,
        shop_name=barber.shop_name,
        shop_address=barber.shop_address,
        shop_image_url=barber.shop_image_url,
        barber_name=f"{barber.first_name} {barber.last_name}",
        phone_number=barber.phone_number,
        email=barber.email,
        license_number=barber.license_number,
        avg_rating=round(avg_rating, 1),
        total_reviews=total_reviews,
        recent_reviews=reviews,
        available_slots=available_slots,
        business_hours=business_hours,
        member_since=barber.create_date.date() if barber.create_date else None,
        shop_status=barber.shop_status if barber.shop_status is not None else True,
    )

@router.get("/nearby")
def get_nearby_shops(
    latitude: float = Query(..., description="User's latitude"),
    longitude: float = Query(..., description="User's longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers", le=50),
    limit: int = Query(20, description="Maximum number of shops to return", le=50),
    db: Session = Depends(get_db)
):
    """Get nearby shops (requires shop coordinates - you'll need to add lat/lng to users table)"""
    # Note: This is a placeholder implementation
    # You'll need to add latitude/longitude columns to the users table
    # and implement proper geospatial queries
    
    # For now, return all shops with a note about implementation
    barbers = db.query(Users).filter(
        and_(
            Users.is_barber == True,
            Users.shop_name.isnot(None)
        )
    ).limit(limit).all()
    
    result = []
    for barber in barbers:
        result.append({
            "barber_id": barber.id,
            "shop_name": barber.shop_name,
            "shop_address": barber.shop_address,
            "distance_km": None,  # Placeholder - implement with actual coordinates
            "note": "Geolocation feature requires latitude/longitude fields in database"
        })
    
    return {
        "message": "Nearby shops feature requires geolocation setup",
        "shops": result
    }

@router.get("/search/advanced")
def advanced_shop_search(
    query: str = Query(..., description="Search query"),
    min_rating: Optional[float] = Query(None, description="Minimum rating filter", ge=0, le=5),
    max_distance: Optional[float] = Query(None, description="Maximum distance in km"),
    has_available_today: bool = Query(False, description="Has slots available today"),
    sort_by: str = Query("rating", description="Sort by: rating, distance, name, availability"),
    db: Session = Depends(get_db)
):
    """Advanced search for shops with multiple filters"""
    
    base_query = db.query(Users).filter(
        and_(
            Users.is_barber == True,
            Users.shop_name.isnot(None)
        )
    )
    
    # Apply text search
    search_term = f"%{query.lower()}%"
    base_query = base_query.filter(
        or_(
            func.lower(Users.shop_name).like(search_term),
            func.lower(Users.shop_address).like(search_term),
            func.lower(Users.first_name).like(search_term),
            func.lower(Users.last_name).like(search_term)
        )
    )
    
    barbers = base_query.all()
    result = []
    
    for barber in barbers:
        # Get rating
        rating_stats = db.query(func.avg(Booking.rating)).join(Slot).filter(
            and_(
                Slot.barber_id == barber.id,
                Booking.rating.isnot(None)
            )
        ).scalar()
        
        avg_rating = float(rating_stats) if rating_stats else 0.0
        
        # Apply rating filter
        if min_rating and avg_rating < min_rating:
            continue
        
        # Check availability today if requested
        has_slots_today = False
        if has_available_today:
            today_slots = db.query(Slot).filter(
                and_(
                    Slot.barber_id == barber.id,
                    Slot.is_booked == False,
                    Slot.slot_date == date.today()
                )
            ).count()
            has_slots_today = today_slots > 0
            
            if has_available_today and not has_slots_today:
                continue
        
        result.append({
            "barber_id": barber.id,
            "shop_name": barber.shop_name,
            "shop_address": barber.shop_address,
            "shop_image_url": barber.shop_image_url,
            "barber_name": f"{barber.first_name} {barber.last_name}",
            "avg_rating": round(avg_rating, 1),
            "has_slots_today": has_slots_today,
            "phone_number": barber.phone_number
        })
    
    # Sort results
    if sort_by == "rating":
        result.sort(key=lambda x: x["avg_rating"], reverse=True)
    elif sort_by == "name":
        result.sort(key=lambda x: x["shop_name"])
    elif sort_by == "availability":
        result.sort(key=lambda x: x["has_slots_today"], reverse=True)
    
    return {
        "query": query,
        "total_results": len(result),
        "shops": result
    }