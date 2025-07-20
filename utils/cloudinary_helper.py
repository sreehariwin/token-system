import base64
import io
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException
from config import CLOUDINARY_ENABLED

def upload_base64_image(base64_string: str, folder: str = "barbershop") -> str:
    """
    Upload a base64 encoded image to Cloudinary
    
    Args:
        base64_string: Base64 encoded image string (with or without data:image prefix)
        folder: Cloudinary folder to store the image
    
    Returns:
        str: Cloudinary image URL
    """
    if not CLOUDINARY_ENABLED:
        raise HTTPException(status_code=500, detail="Image upload is not configured")
    
    try:
        # Remove data:image prefix if present
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            f"data:image/png;base64,{base64_string}",
            folder=folder,
            resource_type="image",
            quality="auto",
            fetch_format="auto"
        )
        
        return result['secure_url']
    
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")