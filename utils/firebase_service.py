# utils/firebase_service.py - Clean Firebase service
import firebase_admin
from firebase_admin import credentials, messaging, exceptions
import json
import os
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class FirebaseService:
    _initialized = False
    _app = None
    
    @classmethod
    def initialize(cls) -> bool:
        """Initialize Firebase Admin SDK once"""
        if cls._initialized:
            return True
            
        try:
            firebase_service_account = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            if not firebase_service_account:
                logger.error("FIREBASE_SERVICE_ACCOUNT environment variable not found")
                return False
                
            service_account_info = json.loads(firebase_service_account)
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in service_account_info]
            if missing:
                logger.error(f"Missing required fields in service account: {missing}")
                return False
            
            cred = credentials.Certificate(service_account_info)
            cls._app = firebase_admin.initialize_app(cred)
            cls._initialized = True
            
            logger.info(f"Firebase initialized successfully for project: {service_account_info.get('project_id')}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Firebase service account JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            return False
    
    @classmethod
    def is_initialized(cls) -> bool:
        return cls._initialized
    
    @classmethod
    async def send_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        device_type: str = "android"
    ) -> Dict[str, Any]:
        """Send notification to a single device"""
        if not cls.initialize():
            return {"success": False, "error": "Firebase not initialized"}
        
        try:
            # Prepare data (FCM requires string values)
            notification_data = {}
            if data:
                notification_data = {k: str(v) for k, v in data.items()}
            
            # Build message based on device type
            if device_type.lower() == "web":
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=notification_data,
                    token=token,
                    webpush=messaging.WebpushConfig(
                        notification=messaging.WebpushNotification(
                            title=title,
                            body=body,
                            icon="/icon-192x192.png",  # Default icon
                            # click_action="/"
                        ),
                        fcm_options=messaging.WebpushFCMOptions(
                            link="/"
                        )
                    )
                )
            else:  # Android/iOS
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=notification_data,
                    token=token,
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            title=title,
                            body=body,
                            sound="default",
                            # click_action="FLUTTER_NOTIFICATION_CLICK"
                        )
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                alert=messaging.ApsAlert(title=title, body=body),
                                sound="default"
                            )
                        )
                    )
                )
            
            response = messaging.send(message)
            logger.info(f"Notification sent successfully to {device_type} device: {response}")
            return {"success": True, "response": response}
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token is unregistered: {token[:20]}...")
            return {"success": False, "error": "unregistered_token", "should_remove": True}
        except exceptions.InvalidArgumentError as e:
            logger.error(f"Invalid argument: {e}")
            return {"success": False, "error": "invalid_argument"}
        except messaging.SenderIdMismatchError:
            logger.error("Sender ID mismatch")
            return {"success": False, "error": "sender_mismatch", "should_remove": True}
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    async def send_to_multiple_devices(
        cls,
        tokens_with_types: List[Dict[str, str]],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send notifications to multiple devices with different types"""
        if not cls.initialize():
            return {"success": False, "error": "Firebase not initialized"}
        
        results = {
            "total": len(tokens_with_types),
            "success": 0,
            "failed": 0,
            "tokens_to_remove": [],
            "errors": []
        }
        
        for device_info in tokens_with_types:
            token = device_info["token"]
            device_type = device_info.get("type", "android")
            
            result = await cls.send_notification(token, title, body, data, device_type)
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "token": token[:20] + "...",
                    "error": result["error"],
                    "device_type": device_type
                })
                
                if result.get("should_remove"):
                    results["tokens_to_remove"].append(token)
        
        return results
    
    @classmethod
    async def validate_token(cls, token: str) -> Dict[str, Any]:
        """Validate FCM token with dry run"""
        if not cls.initialize():
            return {"valid": False, "error": "Firebase not initialized"}
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(title="Test", body="Test"),
                token=token
            )
            
            messaging.send(message, dry_run=True)
            return {"valid": True}
            
        except messaging.UnregisteredError:
            return {"valid": False, "error": "unregistered_token"}
        except exceptions.InvalidArgumentError:
            return {"valid": False, "error": "invalid_token"}
        except messaging.SenderIdMismatchError:
            return {"valid": False, "error": "sender_mismatch"}
        except Exception as e:
            return {"valid": False, "error": str(e)}