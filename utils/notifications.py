# utils/notifications.py - Enhanced with better debugging
from sqlalchemy.orm import Session
from tables.notifications import Notification
from tables.users import Users
from tables.bookings import Booking
from datetime import datetime
from utils.firebase_notifications import send_push_notification, test_fcm_token_validity


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
        print(f"\n🔔 Creating notification for user {user_id}")
        print(f"📋 Type: {notification_type}")
        print(f"📋 Title: {title}")
        print(f"📋 Message: {message}")
        
        # Create database notification (always create regardless of settings)
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            related_booking_id=booking_id
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        print(f"✅ Database notification created with ID: {notification.id}")
        
        # Get user details with explicit query
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            print(f"❌ User {user_id} not found")
            return notification
        
        print(f"👤 User: {user.first_name} {user.last_name}")
        print(f"📧 FCM Token exists: {bool(user.fcm_token)}")
        print(f"🔔 Notifications enabled: {user.notifications_enabled}")
        
        # Check if user has notifications enabled and has FCM token
        if user.notifications_enabled and user.fcm_token:
            print(f"📱 FCM Token (first 30 chars): {user.fcm_token[:30]}...")
            print(f"📱 FCM Token length: {len(user.fcm_token)}")
            
            # Test token validity first
            token_test = await test_fcm_token_validity(user.fcm_token)
            print(f"🧪 Token validation result: {token_test}")
            
            if not token_test['valid']:
                print(f"❌ Token validation failed: {token_test['error']}")
                # Optional: Mark token as invalid in database
                # user.fcm_token = None
                # db.commit()
                return notification
            
            data = {
                "notification_type": notification_type,
                "booking_id": str(booking_id) if booking_id else "",
                "notification_id": str(notification.id),
                "user_id": str(user_id)
            }
            
            print(f"📦 Sending push notification with data: {data}")
            
            success = await send_push_notification(
                fcm_token=user.fcm_token,
                title=title,
                body=message,
                data=data
            )
            
            if success:
                print(f"✅ Push notification sent successfully to user {user_id}")
            else:
                print(f"❌ Push notification failed for user {user_id}")
        else:
            reasons = []
            if not user.notifications_enabled:
                reasons.append("notifications disabled")
            if not user.fcm_token:
                reasons.append("no FCM token")
            
            print(f"⚠️ Skipping push notification: {', '.join(reasons)}")
        
        return notification

    @staticmethod
    async def notify_booking_received(db: Session, booking: Booking, customer: Users, barber: Users):
        """Send notification to barber when new booking is received"""
        print(f"\n📧 BOOKING RECEIVED NOTIFICATION")
        print(f"👤 Customer: {customer.first_name} {customer.last_name} (ID: {customer.id})")
        print(f"💈 Barber: {barber.first_name} {barber.last_name} (ID: {barber.id})")
        print(f"📅 Booking ID: {booking.id}")
        
        title = "New Booking Received"
        message = f"{customer.first_name} {customer.last_name} has booked a slot with you."
        
        return await NotificationService.create_notification_with_push(
            db, barber.id, title, message, "booking_received", booking.id
        )

    @staticmethod
    async def notify_booking_confirmed(db: Session, booking: Booking, customer: Users, barber: Users):
        """Send notification to customer when booking is confirmed"""
        print(f"\n📧 BOOKING CONFIRMED NOTIFICATION")
        
        title = "Booking Confirmed"
        message = f"Your booking with {barber.shop_name or f'{barber.first_name} {barber.last_name}'} has been confirmed."
        
        return await NotificationService.create_notification_with_push(
            db, customer.id, title, message, "booking_confirmed", booking.id
        )
    
    @staticmethod
    async def notify_booking_cancelled(db: Session, booking: Booking, customer: Users, barber: Users, cancelled_by_barber: bool = False):
        """Notify when booking is cancelled"""
        print(f"\n📧 BOOKING CANCELLED NOTIFICATION")
        print(f"💈 Cancelled by barber: {cancelled_by_barber}")
        
        if cancelled_by_barber:
            # Notify customer
            title = "Booking Cancelled"
            message = f"Your booking with {barber.shop_name or f'{barber.first_name} {barber.last_name}'} has been cancelled."
            return await NotificationService.create_notification_with_push(
                db, customer.id, title, message, "booking_cancelled", booking.id
            )
        else:
            # Notify barber
            title = "Booking Cancelled"
            message = f"{customer.first_name} {customer.last_name} has cancelled their booking."
            return await NotificationService.create_notification_with_push(
                db, barber.id, title, message, "booking_cancelled", booking.id
            )

    @staticmethod
    async def send_test_notification(db: Session, user_id: int):
        """Send a test notification with enhanced debugging"""
        print(f"\n🧪 SENDING TEST NOTIFICATION")
        print(f"👤 User ID: {user_id}")
        
        # Get user details first
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            print(f"❌ User {user_id} not found")
            raise Exception(f"User {user_id} not found")
        
        print(f"👤 User: {user.first_name} {user.last_name}")
        print(f"📧 Email: {user.email}")
        print(f"📱 Phone: {user.phone_number}")
        print(f"🔔 Notifications enabled: {user.notifications_enabled}")
        print(f"📱 Has FCM token: {bool(user.fcm_token)}")
        
        if user.fcm_token:
            print(f"📱 FCM Token (first 50 chars): {user.fcm_token[:50]}...")
            print(f"📱 FCM Token (last 20 chars): ...{user.fcm_token[-20:]}")
            print(f"📱 Token length: {len(user.fcm_token)}")
            
            # Test token validity
            token_test = await test_fcm_token_validity(user.fcm_token)
            print(f"🧪 Token validation: {token_test}")
        
        title = "Test Notification"
        message = "This is a test push notification from your barbershop app!"
        
        return await NotificationService.create_notification_with_push(
            db, user_id, title, message, "test_notification"
        )

    @staticmethod
    async def validate_user_fcm_token(db: Session, user_id: int):
        """Validate a user's FCM token"""
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user or not user.fcm_token:
            return {"valid": False, "error": "No FCM token found"}
        
        return await test_fcm_token_validity(user.fcm_token)