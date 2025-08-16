# utils/firebase_notifications.py - Fixed version
import firebase_admin
from firebase_admin import credentials, messaging, exceptions
import json
import os
from typing import Optional, Dict, Any

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
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in service_account_info]
            if missing_fields:
                print(f"❌ Missing required fields in service account: {missing_fields}")
                return False
            
            # Initialize with the service account info
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully")
            print(f"📋 Project ID: {service_account_info.get('project_id')}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing Firebase service account JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            import traceback
            print(f"Full error: {traceback.format_exc()}")
            return False
    else:
        print("✅ Firebase already initialized")
    return True

def validate_fcm_token(token: str) -> bool:
    """Basic FCM token validation"""
    if not token:
        return False
    
    # FCM tokens are typically 152+ characters long
    if len(token) < 140:
        print(f"❌ Token too short: {len(token)} characters")
        return False
    
    # Should not contain spaces or special characters except : - _
    # import re
    # if not re.match(r'^[A-Za-z0-9:_-]+$', token):
    #     print("❌ Token contains invalid characters")
    #     return False
    
    return True

async def send_push_notification(
    fcm_token: str, 
    title: str, 
    body: str, 
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """Send push notification to specific device with enhanced error handling"""
    print(f"\n🚀 Starting push notification process...")
    print(f"📱 Token (first 20 chars): {fcm_token[:20]}...")
    print(f"📋 Title: {title}")
    print(f"📋 Body: {body}")
    
    # Initialize Firebase if not already done
    if not initialize_firebase():
        print("❌ Firebase not initialized, skipping push notification")
        return False
    
    # Validate FCM token
    if not validate_fcm_token(fcm_token):
        print(f"❌ Invalid FCM token format")
        return False
    
    try:
        # Convert all data values to strings (FCM requirement)
        string_data = {}
        if data:
            for key, value in data.items():
                if value is not None:
                    string_data[key] = str(value)
                else:
                    string_data[key] = ""
            print(f"📋 Data payload: {string_data}")
        
        # Create a simple message first (minimal config)
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=string_data,
            token=fcm_token,
            # Simplified Android config
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    sound="default",
                    click_action="FLUTTER_NOTIFICATION_CLICK"
                )
            )
        )

        print(f"📤 Sending notification...")
        response = messaging.send(message)
        print(f'✅ Successfully sent push notification')
        print(f'📋 Response ID: {response}')
        return True
        
    except exceptions.InvalidArgumentError as e:
        print(f'❌ Invalid argument error: {e}')
        print(f'   This usually means the FCM token format is invalid')
        return False
        
    except messaging.UnregisteredError as e:
        print(f'❌ Unregistered token error: {e}')
        print(f'   Token may be expired, invalid, or app uninstalled')
        # You might want to remove this token from your database
        return False
        
    except messaging.SenderIdMismatchError as e:
        print(f'❌ Sender ID mismatch error: {e}')
        print(f'   The FCM token was registered with a different Firebase project')
        return False
        
    except messaging.QuotaExceededError as e:
        print(f'❌ Quota exceeded error: {e}')
        print(f'   Firebase messaging quota exceeded')
        return False
        
    except exceptions.UnavailableError as e:
        print(f'❌ Service unavailable error: {e}')
        print(f'   Firebase service is temporarily unavailable')
        return False
        
    except exceptions.InternalError as e:
        print(f'❌ Internal Firebase error: {e}')
        return False
        
    except Exception as e:
        print(f'❌ Unexpected error sending push notification: {e}')
        print(f'   Error type: {type(e).__name__}')
        import traceback
        print(f'   Full traceback: {traceback.format_exc()}')
        return False

async def test_fcm_token_validity(fcm_token: str) -> Dict[str, Any]:
    """Test if an FCM token is valid by attempting to send a dry-run message"""
    if not initialize_firebase():
        return {"valid": False, "error": "Firebase not initialized"}
    
    if not validate_fcm_token(fcm_token):
        return {"valid": False, "error": "Invalid token format"}
    
    try:
        # Create a simple test message with dry_run=True
        message = messaging.Message(
            notification=messaging.Notification(
                title="Test",
                body="Test message"
            ),
            token=fcm_token
        )
        
        # Send with dry_run=True (doesn't actually send)
        response = messaging.send(message, dry_run=True)
        print(f"✅ Token validation successful: {response}")
        return {"valid": True, "response": response}
        
    except exceptions.InvalidArgumentError as e:
        return {"valid": False, "error": f"Invalid argument: {e}"}
    except messaging.UnregisteredError as e:
        return {"valid": False, "error": f"Unregistered token: {e}"}
    except messaging.SenderIdMismatchError as e:
        return {"valid": False, "error": f"Sender ID mismatch: {e}"}
    except Exception as e:
        return {"valid": False, "error": f"Unexpected error: {e}"}

# Keep the multicast function but simplified
async def send_to_multiple_tokens(tokens: list, title: str, body: str, data: dict = None):
    """Send to multiple devices with better error handling"""
    if not initialize_firebase():
        print("❌ Firebase not initialized, skipping push notifications")
        return None
    
    # Filter out invalid tokens
    valid_tokens = [token for token in tokens if validate_fcm_token(token)]
    if not valid_tokens:
        print("❌ No valid FCM tokens found")
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
            tokens=valid_tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    sound="default"
                )
            )
        )
        
        response = messaging.send_multicast(message)
        print(f'✅ {response.success_count} messages sent successfully out of {len(valid_tokens)}')
        
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