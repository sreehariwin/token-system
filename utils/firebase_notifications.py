# utils/firebase_notifications.py - Fixed version
import firebase_admin
from firebase_admin import credentials, messaging
import json
import os

# Initialize Firebase Admin (do this once)
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Get Firebase service account from environment variable
            firebase_service_account = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            if not firebase_service_account:
                print("⚠️ FIREBASE_SERVICE_ACCOUNT environment variable not found")
                return False
                
            # Parse the JSON string
            service_account_info = json.loads(firebase_service_account)
            
            # Initialize with the service account info
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing Firebase service account JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            return False
    return True

async def send_push_notification(
    fcm_token: str, 
    title: str, 
    body: str, 
    data: dict = None
):
    """Send push notification to specific device"""
    if not initialize_firebase():
        print("❌ Firebase not initialized, skipping push notification")
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    channel_id="booking_notifications",
                    priority="high"
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        sound="default"
                    )
                )
            )
        )
        
        response = messaging.send(message)
        print(f'✅ Successfully sent push notification: {response}')
        return True
        
    except Exception as e:
        print(f'❌ Error sending push notification: {e}')
        return False

async def send_to_multiple_tokens(tokens: list, title: str, body: str, data: dict = None):
    """Send to multiple devices"""
    if not initialize_firebase():
        print("❌ Firebase not initialized, skipping push notifications")
        return None
    
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=tokens,
        )
        
        response = messaging.send_multicast(message)
        print(f'✅ {response.success_count} messages sent successfully out of {len(tokens)}')
        
        # Log any failures
        if response.failure_count > 0:
            for idx, result in enumerate(response.responses):
                if not result.success:
                    print(f'❌ Failed to send to token {idx}: {result.exception}')
        
        return response
        
    except Exception as e:
        print(f'❌ Error sending multicast notifications: {e}')
        return None