# utils/notification_service.py - Clean notification service
from sqlalchemy.orm import Session
from sqlalchemy import and_
from tables.notifications import Notification
from tables.user_devices import UserDevice
from tables.users import Users
from tables.bookings import Booking
from utils.firebase_service import FirebaseService
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from datetime import timedelta


logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    async def create_and_send_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        booking_id: Optional[int] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create notification in DB and send push notifications to all user devices"""
        
        # Create notification in database
        notification_data = additional_data or {}
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            related_booking_id=booking_id,
            data=notification_data
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        logger.info(f"Created notification {notification.id} for user {user_id}")
        
        # Send push notifications
        await NotificationService._send_push_notifications(db, notification)
        
        return notification
    
    @staticmethod
    async def _send_push_notifications(db: Session, notification: Notification):
        """Send push notifications to all active devices of the user"""
        
        # Get user's active devices
        devices = db.query(UserDevice).filter(
            and_(
                UserDevice.user_id == notification.user_id,
                UserDevice.is_active == True
            )
        ).all()
        
        if not devices:
            logger.info(f"No active devices found for user {notification.user_id}")
            return
        
        # Check if user has notifications enabled
        user = db.query(Users).filter(Users.id == notification.user_id).first()
        if not user or not user.notifications_enabled:
            logger.info(f"Notifications disabled for user {notification.user_id}")
            return
        
        # Prepare device tokens
        tokens_with_types = []
        for device in devices:
            tokens_with_types.append({
                "token": device.fcm_token,
                "type": device.device_type.value,
                "device_id": device.id
            })
        
        # Prepare notification data
        push_data = {
            "notification_type": notification.type,
            "notification_id": str(notification.id),
            "user_id": str(notification.user_id)
        }
        
        if notification.related_booking_id:
            push_data["booking_id"] = str(notification.related_booking_id)
        
        if notification.data:
            push_data.update({k: str(v) for k, v in notification.data.items()})
        
        # Send notifications
        logger.info(f"Sending push notifications to {len(devices)} devices for user {notification.user_id}")
        
        results = await FirebaseService.send_to_multiple_devices(
            tokens_with_types,
            notification.title,
            notification.message,
            push_data
        )
        
        # Update notification with results
        notification.push_success_count = results["success"]
        notification.push_failure_count = results["failed"]
        notification.sent_to_devices = [d["device_id"] for d in tokens_with_types]
        
        # Remove invalid tokens
        if results["tokens_to_remove"]:
            logger.info(f"Removing {len(results['tokens_to_remove'])} invalid tokens")
            for token in results["tokens_to_remove"]:
                db.query(UserDevice).filter(UserDevice.fcm_token == token).update({
                    "is_active": False
                })
        
        db.commit()
        logger.info(f"Push notification results: {results['success']} success, {results['failed']} failed")
    
    # Specific notification methods for different events
    
    @staticmethod
    async def notify_booking_received(
        db: Session,
        booking: Booking,
        customer: Users,
        barber: Users
    ):
        """Notify barber when new booking is received"""
        logger.info(f"Sending booking received notification to barber {barber.id}")
        
        title = "New Booking Received"
        message = f"{customer.first_name} {customer.last_name} has booked a slot with you."
        
        # Get slot details for additional data
        slot = booking.slot
        additional_data = {
            "customer_name": f"{customer.first_name} {customer.last_name}",
            "customer_phone": customer.phone_number,
            "slot_date": slot.slot_date.isoformat(),
            "slot_time": slot.start_time.strftime("%H:%M"),
            "action": "view_booking"
        }
        
        return await NotificationService.create_and_send_notification(
            db, barber.id, title, message, "booking_received", booking.id, additional_data
        )
    
    @staticmethod
    async def notify_booking_confirmed(
        db: Session,
        booking: Booking,
        customer: Users,
        barber: Users
    ):
        """Notify customer when booking is confirmed"""
        logger.info(f"Sending booking confirmed notification to customer {customer.id}")
        
        title = "Booking Confirmed"
        shop_name = barber.shop_name or f"{barber.first_name} {barber.last_name}"
        message = f"Your booking with {shop_name} has been confirmed."
        
        slot = booking.slot
        additional_data = {
            "barber_name": f"{barber.first_name} {barber.last_name}",
            "shop_name": shop_name,
            "slot_date": slot.slot_date.isoformat(),
            "slot_time": slot.start_time.strftime("%H:%M"),
            "action": "view_booking"
        }
        
        return await NotificationService.create_and_send_notification(
            db, customer.id, title, message, "booking_confirmed", booking.id, additional_data
        )
    
    @staticmethod
    async def notify_booking_cancelled(
        db: Session,
        booking: Booking,
        customer: Users,
        barber: Users,
        cancelled_by_barber: bool = False
    ):
        """Notify about booking cancellation"""
        
        if cancelled_by_barber:
            # Notify customer
            logger.info(f"Sending booking cancelled notification to customer {customer.id}")
            
            title = "Booking Cancelled"
            shop_name = barber.shop_name or f"{barber.first_name} {barber.last_name}"
            message = f"Your booking with {shop_name} has been cancelled."
            
            additional_data = {
                "cancelled_by": "barber",
                "barber_name": f"{barber.first_name} {barber.last_name}",
                "shop_name": shop_name,
                "action": "view_bookings"
            }
            
            return await NotificationService.create_and_send_notification(
                db, customer.id, title, message, "booking_cancelled", booking.id, additional_data
            )
        else:
            # Notify barber
            logger.info(f"Sending booking cancelled notification to barber {barber.id}")
            
            title = "Booking Cancelled"
            message = f"{customer.first_name} {customer.last_name} has cancelled their booking."
            
            additional_data = {
                "cancelled_by": "customer",
                "customer_name": f"{customer.first_name} {customer.last_name}",
                "customer_phone": customer.phone_number,
                "action": "view_bookings"
            }
            
            return await NotificationService.create_and_send_notification(
                db, barber.id, title, message, "booking_cancelled", booking.id, additional_data
            )
    
    @staticmethod
    async def send_test_notification(
        db: Session,
        user_id: int,
        title: str = "Test Notification",
        message: str = "This is a test notification from your barbershop app!",
        device_types: Optional[List[str]] = None
    ):
        """Send test notification to user"""
        logger.info(f"Sending test notification to user {user_id}")
        
        additional_data = {
            "test": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # If specific device types are requested, filter devices
        if device_types:
            # Get only devices of specified types
            devices = db.query(UserDevice).filter(
                and_(
                    UserDevice.user_id == user_id,
                    UserDevice.is_active == True,
                    UserDevice.device_type.in_(device_types)
                )
            ).all()
            
            if not devices:
                raise Exception(f"No active devices of types {device_types} found")
            
            # Temporarily create notification and send to specific devices
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type="test_notification",
                data=additional_data
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Send to specific device types only
            tokens_with_types = []
            for device in devices:
                tokens_with_types.append({
                    "token": device.fcm_token,
                    "type": device.device_type.value,
                    "device_id": device.id
                })
            
            push_data = {
                "notification_type": "test_notification",
                "notification_id": str(notification.id),
                "user_id": str(user_id),
                "test": "true"
            }
            
            results = await FirebaseService.send_to_multiple_devices(
                tokens_with_types, title, message, push_data
            )
            
            notification.push_success_count = results["success"]
            notification.push_failure_count = results["failed"]
            db.commit()
            
            return notification
        else:
            # Send to all devices
            return await NotificationService.create_and_send_notification(
                db, user_id, title, message, "test_notification", None, additional_data
            )
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Notification]:
        """Get user's notifications"""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def mark_notification_read(db: Session, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        ).first()
        
        if notification:
            notification.is_read = True
            db.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_notifications_read(db: Session, user_id: int):
        """Mark all notifications as read for user"""
        db.query(Notification).filter(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        ).update({"is_read": True})
        db.commit()
    
    @staticmethod
    def get_notification_stats(db: Session, user_id: int) -> Dict[str, int]:
        """Get notification statistics for user"""
        total = db.query(Notification).filter(Notification.user_id == user_id).count()
        unread = db.query(Notification).filter(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        ).count()
        
        # Recent notifications (last 24 hours)
        recent_time = datetime.utcnow() - timedelta(hours=24)
        recent = db.query(Notification).filter(
            and_(Notification.user_id == user_id, Notification.created_at >= recent_time)
        ).count()
        
        # Active devices count
        active_devices = db.query(UserDevice).filter(
            and_(UserDevice.user_id == user_id, UserDevice.is_active == True)
        ).count()
        
        return {
            "total_notifications": total,
            "unread_count": unread,
            "recent_count": recent,
            "active_devices": active_devices
        }