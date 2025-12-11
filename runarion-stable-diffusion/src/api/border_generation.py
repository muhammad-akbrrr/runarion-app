"""
API endpoint for generating decorative border templates using ControlNet with SDXL.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import torch
from PIL import Image
import io
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class BorderGenerationRequest(BaseModel):
    prompt: str = "ornate decorative border frame, intricate patterns, elegant design"
    negative_prompt: Optional[str] = "text, watermark, signature, low quality, blurry, incomplete border"
    width: int = 1024  # SDXL default
    height: int = 1024  # SDXL default
    num_inference_steps: int = 30  # SDXL recommended
    guidance_scale: float = 5.0  # SDXL typically uses 3-6
    seed: Optional[int] = None
    border_thickness: int = 80  # Thickness of the border frame
    border_style: str = "rectangular"  # rectangular, circular, ornate


@router.post("/generate-border")
async def generate_border(request: BorderGenerationRequest, req: Request):
    """
    Generate a decorative border template using ControlNet with SDXL.
    
    Creates a control image with edge detection on a border shape,
    then uses ControlNet to generate a decorative border design.
    
    Args:
        request: BorderGenerationRequest with generation parameters
        req: FastAPI Request object to access app state
    
    Returns:
        Image bytes (PNG format, transparent background)
    """
    try:
        app_state = req.app.state
        
        # Border generation requires the ControlNet pipeline (separate from main pipeline)
        controlnet_pipe = getattr(app_state, "controlnet_pipe", None)
        
        if controlnet_pipe is None:
            raise HTTPException(
                status_code=400, 
                detail="ControlNet is required for border generation. Enable USE_CONTROLNET=true and restart the service."
            )
        
        pipe = controlnet_pipe  # Use ControlNet pipeline for borders
        
        # Set seed if provided
        generator = None
        if request.seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(request.seed)
        
        # Create control image: border frame outline
        control_image = np.ones((request.height, request.width, 3), dtype=np.uint8) * 255
        
        thickness = request.border_thickness
        
        if request.border_style == "circular":
            # Circular border
            center = (request.width // 2, request.height // 2)
            radius = min(request.width, request.height) // 2 - thickness
            cv2.circle(control_image, center, radius, (0, 0, 0), thickness)
            cv2.circle(control_image, center, radius - thickness, (255, 255, 255), thickness)
        elif request.border_style == "ornate":
            # Ornate border with decorative corners
            # Outer rectangle
            cv2.rectangle(control_image, (thickness, thickness), 
                         (request.width - thickness, request.height - thickness), (0, 0, 0), thickness)
            # Inner rectangle
            cv2.rectangle(control_image, (thickness * 2, thickness * 2), 
                         (request.width - thickness * 2, request.height - thickness * 2), (255, 255, 255), thickness)
            # Decorative corners
            corner_size = thickness * 3
            # Top-left corner
            cv2.rectangle(control_image, (thickness, thickness), 
                         (thickness + corner_size, thickness + corner_size), (0, 0, 0), 2)
            # Top-right corner
            cv2.rectangle(control_image, (request.width - thickness - corner_size, thickness), 
                         (request.width - thickness, thickness + corner_size), (0, 0, 0), 2)
            # Bottom-left corner
            cv2.rectangle(control_image, (thickness, request.height - thickness - corner_size), 
                         (thickness + corner_size, request.height - thickness), (0, 0, 0), 2)
            # Bottom-right corner
            cv2.rectangle(control_image, (request.width - thickness - corner_size, request.height - thickness - corner_size), 
                         (request.width - thickness, request.height - thickness), (0, 0, 0), 2)
        else:
            # Rectangular border (default)
            cv2.rectangle(control_image, (thickness, thickness), 
                         (request.width - thickness, request.height - thickness), (0, 0, 0), thickness)
            cv2.rectangle(control_image, (thickness * 2, thickness * 2), 
                         (request.width - thickness * 2, request.height - thickness * 2), (255, 255, 255), thickness)
        
        # Apply Canny edge detection for ControlNet
        gray = cv2.cvtColor(control_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        control_image = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        control_image_pil = Image.fromarray(control_image)
        
        logger.info(f"Generating SDXL border with prompt: {request.prompt[:50]}...")
        
        # Generate border using ControlNet (SDXL)
        output = pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            image=control_image_pil,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            generator=generator,
        )
        
        image = output.images[0]
        
        # Make background transparent (borders should have transparent centers)
        image = image.convert("RGBA")
        data = np.array(image)
        
        # Create mask for the border area (keep edges, make center transparent)
        h, w = data.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Create distance from center mask
        y_coords, x_coords = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
        max_dist = np.sqrt(center_x**2 + center_y**2)
        
        # Keep border area (outer edges), make center transparent
        # Border is roughly the outer 15-20% of the image
        border_mask = dist_from_center > (max_dist * 0.7)
        
        # Also use edge detection to find actual border edges
        gray_img = cv2.cvtColor(data[:, :, :3], cv2.COLOR_RGB2GRAY)
        img_edges = cv2.Canny(gray_img, 50, 150)
        edge_mask = img_edges > 0
        
        # Combine: keep pixels that are either in border area OR part of edge structure
        keep_mask = border_mask | edge_mask
        
        # Smooth the mask
        keep_mask_uint8 = (keep_mask * 255).astype(np.uint8)
        keep_mask_smooth = cv2.GaussianBlur(keep_mask_uint8, (5, 5), 2)
        
        # Create alpha channel
        alpha = np.clip(keep_mask_smooth, 0, 255).astype(np.uint8)
        data[:, :, 3] = alpha
        image = Image.fromarray(data)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        logger.info("Border template generated successfully")
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating border: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate border: {str(e)}")
