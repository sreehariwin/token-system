# routes/devices.py - Device management routes
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from config import get_db
from models.notifications import (
    RegisterDeviceRequest, DeviceInfo, DeviceType
)
from models.users import ResponseSchema
from tables.user_devices import UserDevice, DeviceTypeEnum
from tables.users import Users
from repository.users import get_current_user
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Device Management"])

def get_client_info(request: Request):
    """Extract client information from request"""
    user_agent = request.headers.get('user-agent', 'Unknown')
    ip_address = request.client.host if request.client else 'Unknown'
    return user_agent[:500], ip_address

@router.post('/register')
async def register_device(
    request: RegisterDeviceRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Register a new device for push notifications"""
    try:
        user_agent, ip_address = get_client_info(req)
        
        # Check if this FCM token already exists for this user
        existing_device = db.query(UserDevice).filter(
            and_(
                UserDevice.user_id == current_user.id,
                UserDevice.fcm_token == request.fcm_token
            )
        ).first()
        
        if existing_device:
            # Update existing device
            existing_device.device_type = DeviceTypeEnum(request.device_type)
            existing_device.device_name = request.device_name
            existing_device.browser_info = request.browser_info or user_agent
            existing_device.is_active = True
            existing_device.updated_at = datetime.utcnow()
            existing_device.last_seen = datetime.utcnow()
            
            db.commit()
            logger.info(f"Updated existing device {existing_device.id} for user {current_user.id}")
            
            return ResponseSchema(
                code="200",
                status="OK",
                message="Device updated successfully",
                result={"device_id": existing_device.id, "action": "updated"}
            ).dict(exclude_none=True)
        
        # Generate device name if not provided
        device_name = request.device_name
        if not device_name:
            if request.device_type == DeviceType.WEB:
                # Extract browser from user agent
                if "Chrome" in user_agent:
                    device_name = "Chrome Browser"
                elif "Firefox" in user_agent:
                    device_name = "Firefox Browser"
                elif "Safari" in user_agent:
                    device_name = "Safari Browser"
                else:
                    device_name = "Web Browser"
            else:
                device_name = f"{request.device_type.value.title()} Device"
        
        # Create new device
        new_device = UserDevice(
            user_id=current_user.id,
            device_type=DeviceTypeEnum(request.device_type),
            fcm_token=request.fcm_token,
            device_id=request.device_id,
            device_name=device_name,
            browser_info=request.browser_info or user_agent,
            is_active=True
        )
        
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        
        logger.info(f"Registered new {request.device_type} device {new_device.id} for user {current_user.id}")
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Device registered successfully",
            result={
                "device_id": new_device.id,
                "device_name": device_name,
                "device_type": request.device_type,
                "action": "created"
            }
        ).dict(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Failed to register device"
        ).dict(exclude_none=True)

@router.get('/my', response_model=List[DeviceInfo])
async def get_my_devices(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get all devices registered for current user"""
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == current_user.id
    ).order_by(UserDevice.last_seen.desc()).all()
    
    return [
        DeviceInfo(
            id=device.id,
            device_type=DeviceType(device.device_type.value),
            device_name=device.device_name,
            is_active=device.is_active,
            created_at=device.created_at,
            last_seen=device.last_seen
        ) for device in devices
    ]

@router.put('/{device_id}/toggle')
async def toggle_device_notifications(
    device_id: int,
    enable: bool,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Enable/disable notifications for a specific device"""
    device = db.query(UserDevice).filter(
        and_(
            UserDevice.id == device_id,
            UserDevice.user_id == current_user.id
        )
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_active = enable
    device.updated_at = datetime.utcnow()
    db.commit()
    
    status = "enabled" if enable else "disabled"
    return ResponseSchema(
        code="200",
        status="OK",
        message=f"Device notifications {status}",
        result={
            "device_id": device_id,
            "device_name": device.device_name,
            "is_active": enable
        }
    ).dict(exclude_none=True)

@router.delete('/{device_id}')
async def remove_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Remove a device from user's registered devices"""
    device = db.query(UserDevice).filter(
        and_(
            UserDevice.id == device_id,
            UserDevice.user_id == current_user.id
        )
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_name = device.device_name
    db.delete(device)
    db.commit()
    
    return ResponseSchema(
        code="200",
        status="OK",
        message=f"Device '{device_name}' removed successfully"
    ).dict(exclude_none=True)

@router.put('/update-token')
async def update_device_token(
    device_id: int,
    new_fcm_token: str,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Update FCM token for a specific device"""
    device = db.query(UserDevice).filter(
        and_(
            UserDevice.id == device_id,
            UserDevice.user_id == current_user.id
        )
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.fcm_token = new_fcm_token
    device.updated_at = datetime.utcnow()
    device.last_seen = datetime.utcnow()
    db.commit()
    
    return ResponseSchema(
        code="200",
        status="OK",
        message="Device token updated successfully",
        result={"device_id": device_id}
    ).dict(exclude_none=True)