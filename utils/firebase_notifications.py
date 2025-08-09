# utils/firebase_notifications.py
import firebase_admin
from firebase_admin import credentials, messaging
import json
import os

# Initialize Firebase Admin (do this once)
def initialize_firebase():
    if not firebase_admin._apps:
        # Use service account key file
        # cred = credentials.Certificate("path/to/serviceAccountKey.json")
        # Or use environment variable
        cred = credentials.Certificate(json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT')))
        
        firebase_admin.initialize_app(cred)

async def send_push_notification(
    fcm_token: str, 
    title: str, 
    body: str, 
    data: dict = None
):
    """Send push notification to specific device"""
    initialize_firebase()
    
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
    
    try:
        response = messaging.send(message)
        print(f'Successfully sent message: {response}')
        return True
    except Exception as e:
        print(f'Error sending push notification: {e}')
        return False

async def send_to_multiple_tokens(tokens: list, title: str, body: str, data: dict = None):
    """Send to multiple devices"""
    initialize_firebase()
    
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )
    
    response = messaging.send_multicast(message)
    print(f'{response.success_count} messages sent successfully')
    return response