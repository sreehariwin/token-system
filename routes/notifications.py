# routes/notifications.py - Create new file
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from config import get_db
from tables.notifications import Notification
from tables.users import Users
from repository.users import get_current_user
from typing import List

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/")
def get_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    limit: int = Query(20, description="Number of notifications to return", le=100),
    offset: int = Query(0, description="Number of notifications to skip"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get user's notifications"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "is_read": n.is_read,
                "related_booking_id": n.related_booking_id,
                "created_at": n.created_at
            } for n in notifications
        ],
        "total_unread": db.query(Notification).filter(
            and_(Notification.user_id == current_user.id, Notification.is_read == False)
        ).count()
    }

@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Mark notification as read"""
    notification = db.query(Notification).filter(
        and_(Notification.id == notification_id, Notification.user_id == current_user.id)
    ).first()
    
    if not notification:
        return {"message": "Notification not found"}
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.put("/mark-all-read")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        and_(Notification.user_id == current_user.id, Notification.is_read == False)
    ).update({"is_read": True})
    db.commit()
    
    return {"message": "All notifications marked as read"}

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        and_(Notification.user_id == current_user.id, Notification.is_read == False)
    ).count()
    
    return {"unread_count": count}