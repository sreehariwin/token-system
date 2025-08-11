# utils/firebase_notifications.py - Fixed version
import firebase_admin
from firebase_admin import credentials, messaging, exceptions
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
        # Convert all data values to strings (FCM requirement)
        string_data = {}
        if data:
            for key, value in data.items():
                string_data[key] = str(value) if value is not None else ""
        
        # Create the message with better Android configuration
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=string_data,
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority="high",  # This ensures immediate delivery
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    channel_id="booking_notifications",
                    priority="high",
                    default_sound=True,
                    notification_count=1,
                    visibility="public",
                    # color="#FF6B6B",  # Optional: notification color
                    # icon="ic_notification",  # Make sure this icon exists in your Flutter app
                    sound="default"
                ),
                # Add data to android section as well for background handling
                data=string_data
            ),
            apns=messaging.APNSConfig(
                headers={
                    "apns-priority": "10",  # High priority for iOS
                    "apns-push-type": "alert"
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        sound="default",
                        badge=1,
                        category="booking_notification"
                    ),
                    # Add custom data for iOS
                    **string_data
                )
            ),
            # Add web push config for completeness
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    # icon="https://your-app-icon-url.com/icon.png"  # Optional
                ),
                data=string_data
            )
        )

        print(f"📤 Sending notification to token: {fcm_token[:20]}...")
        print(f"📋 Title: {title}")
        print(f"📋 Body: {body}")
        print(f"📋 Data: {string_data}")
        
        response = messaging.send(message)
        print(f'✅ Successfully sent push notification: {response}')
        return True
        
    except exceptions.InvalidArgumentError as e:
        print(f'❌ Invalid argument error: {e}')
        print(f'   Token: {fcm_token[:20]}...')
        return False
    except messaging.UnregisteredError as e:
        print(f'❌ Unregistered token error: {e}')
        print(f'   Token may be invalid or app uninstalled: {fcm_token[:20]}...')
        return False
    except messaging.SenderIdMismatchError as e:
        print(f'❌ Sender ID mismatch error: {e}')
        print(f'   Check your Firebase project configuration')
        return False
    except messaging.QuotaExceededError as e:
        print(f'❌ Quota exceeded error: {e}')
        return False
    except Exception as e:
        print(f'❌ Error sending push notification: {e}')
        print(f'   Error type: {type(e).__name__}')
        import traceback
        print(f'   Full traceback: {traceback.format_exc()}')
        return False


async def send_to_multiple_tokens(tokens: list, title: str, body: str, data: dict = None):
    """Send to multiple devices with better error handling"""
    if not initialize_firebase():
        print("❌ Firebase not initialized, skipping push notifications")
        return None
    
    try:
        # Convert all data values to strings
        string_data = {}
        if data:
            for key, value in data.items():
                string_data[key] = str(value) if value is not None else ""
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=string_data,
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    channel_id="booking_notifications",
                    priority="high",
                    default_sound=True
                )
            )
        )
        
        response = messaging.send_multicast(message)
        print(f'✅ {response.success_count} messages sent successfully out of {len(tokens)}')
        
        # Log any failures with details
        if response.failure_count > 0:
            for idx, result in enumerate(response.responses):
                if not result.success:
                    error_code = result.exception.code if hasattr(result.exception, 'code') else 'unknown'
                    print(f'❌ Failed to send to token {idx}: {error_code} - {result.exception}')
        
        return response
        
    except Exception as e:
        print(f'❌ Error sending multicast notifications: {e}')
        return None
