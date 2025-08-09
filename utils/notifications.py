# utils/notifications.py 
from sqlalchemy.orm import Session
from tables.notifications import Notification
from tables.users import Users
from tables.bookings import Booking
from datetime import datetime
from utils.firebase_notifications import send_push_notification


class NotificationService:
    @staticmethod
    async def create_notification_with_push(
        db: Session, 
        user_id: int, 
        title: str, 
        message: str, 
        notification_type: str,
        booking_id: int = None
    ):
        # Create database notification
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            related_booking_id=booking_id
        )
        db.add(notification)
        db.commit()
        
        # Get user's FCM token and send push notification
        user = db.query(Users).filter(Users.id == user_id).first()
        if user and user.fcm_token:
            data = {
                "notification_type": notification_type,
                "booking_id": str(booking_id) if booking_id else "",
                "notification_id": str(notification.id)
            }
            
            await send_push_notification(
                fcm_token=user.fcm_token,
                title=title,
                body=message,
                data=data
            )
        
        return notification

    @staticmethod
    async def notify_booking_received(db: Session, booking: Booking, customer: Users, barber: Users):
        title = "New Booking Received"
        message = f"{customer.first_name} {customer.last_name} has booked a slot with you."
        
        await NotificationService.create_notification_with_push(
            db, barber.id, title, message, "booking_received", booking.id
        )

    @staticmethod
    async def notify_booking_confirmed(db: Session, booking: Booking, customer: Users, barber: Users):
        title = "Booking Confirmed"
        message = f"Your booking with {barber.shop_name or f'{barber.first_name} {barber.last_name}'} has been confirmed."
        
        await NotificationService.create_notification_with_push(
            db, customer.id, title, message, "booking_confirmed", booking.id
        )
    @staticmethod
    def notify_booking_cancelled(db: Session, booking: Booking, customer: Users, barber: Users, cancelled_by_barber: bool = False):
        """Notify when booking is cancelled"""
        if cancelled_by_barber:
            # Notify customer
            title = "Booking Cancelled"
            message = f"Your booking with {barber.shop_name or f'{barber.first_name} {barber.last_name}'} has been cancelled."
            NotificationService.create_notification(
                db, customer.id, title, message, "booking_cancelled", booking.id
            )
        else:
            # Notify barber
            title = "Booking Cancelled"
            message = f"{customer.first_name} {customer.last_name} has cancelled their booking."
            NotificationService.create_notification(
                db, barber.id, title, message, "booking_cancelled", booking.id
            )