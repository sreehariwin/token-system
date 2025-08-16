# routes/notifications.py - Clean notification routes
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from config import get_db
from models.notifications import (
    TestNotificationRequest, NotificationResponse, NotificationStats, DeviceType
)
from models.users import ResponseSchema
from tables.notifications import Notification
from tables.users import Users
from repository.users import get_current_user
from utils.notification_service import NotificationService
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    limit: int = Query(20, description="Number of notifications to return", le=100),
    offset: int = Query(0, description="Number of notifications to skip"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get user's notifications"""
    notifications = NotificationService.get_user_notifications(
        db, current_user.id, unread_only, limit, offset
    )
    
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            message=n.message,
            type=n.type,
            is_read=n.is_read,
            related_booking_id=n.related_booking_id,
            data=n.data,
            created_at=n.created_at,
            push_success_count=n.push_success_count or 0,
            push_failure_count=n.push_failure_count or 0
        ) for n in notifications
    ]

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Mark notification as read"""
    success = NotificationService.mark_notification_read(db, notification_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return ResponseSchema(
        code="200",
        status="OK",
        message="Notification marked as read"
    ).dict(exclude_none=True)

@router.put("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Mark all notifications as read"""
    NotificationService.mark_all_notifications_read(db, current_user.id)
    
    return ResponseSchema(
        code="200",
        status="OK",
        message="All notifications marked as read"
    ).dict(exclude_none=True)

@router.get("/stats", response_model=NotificationStats)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get notification statistics"""
    stats = NotificationService.get_notification_stats(db, current_user.id)
    
    return NotificationStats(
        total_notifications=stats["total_notifications"],
        unread_count=stats["unread_count"],
        recent_count=stats["recent_count"],
        push_enabled_devices=stats["active_devices"],
        active_devices=stats["active_devices"]
    )

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

@router.put('/settings/toggle')
async def toggle_all_notifications(
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Enable or disable all push notifications for the user"""
    current_user.notifications_enabled = enabled
    db.commit()
    
    status = "enabled" if enabled else "disabled"
    return ResponseSchema(
        code="200",
        status="OK",
        message=f"All notifications {status} successfully",
        result={"notifications_enabled": enabled}
    ).dict(exclude_none=True)

@router.get('/settings/status')
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get current notification settings"""
    stats = NotificationService.get_notification_stats(db, current_user.id)
    
    return ResponseSchema(
        code="200",
        status="OK",
        message="Notification settings retrieved successfully",
        result={
            "notifications_enabled": current_user.notifications_enabled,
            "active_devices": stats["active_devices"],
            "total_notifications": stats["total_notifications"],
            "unread_count": stats["unread_count"]
        }
    ).dict(exclude_none=True)

@router.post('/test')
async def send_test_notification(
    request: TestNotificationRequest = TestNotificationRequest(),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Send a test notification to user's devices"""
    try:
        device_types = None
        if request.device_types:
            device_types = [dt.value for dt in request.device_types]
        
        notification = await NotificationService.send_test_notification(
            db=db,
            user_id=current_user.id,
            title=request.title,
            message=request.message,
            device_types=device_types
        )
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Test notification sent successfully",
            result={
                "notification_id": notification.id,
                "title": request.title,
                "message": request.message,
                "devices_targeted": device_types or "all",
                "push_success_count": notification.push_success_count,
                "push_failure_count": notification.push_failure_count
            }
        ).dict(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return ResponseSchema(
            code="500",
            status="Error",
            message=f"Failed to send test notification: {str(e)}"
        ).dict(exclude_none=True)

@router.delete('/{notification_id}')
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Delete a specific notification"""
    notification = db.query(Notification).filter(
        and_(Notification.id == notification_id, Notification.user_id == current_user.id)
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return ResponseSchema(
        code="200",
        status="OK",
        message="Notification deleted successfully"
    ).dict(exclude_none=True)

@router.delete('/clear-all')
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Delete all notifications for the current user"""
    deleted_count = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).delete()
    
    db.commit()
    
    return ResponseSchema(
        code="200",
        status="OK",
        message=f"Cleared {deleted_count} notifications",
        result={"deleted_count": deleted_count}
    ).dict(exclude_none=True)