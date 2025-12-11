"""
API endpoint for generating chapter cover images with transparency support using SDXL.
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
import os

logger = logging.getLogger(__name__)

router = APIRouter()


class CoverGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "text, watermark, signature, low quality, blurry"
    width: int = 1024  # SDXL default
    height: int = 1024  # SDXL default (or 832x1216 for portrait)
    num_inference_steps: int = 30  # SDXL recommended
    guidance_scale: float = 5.0  # SDXL typically uses 3-6
    seed: Optional[int] = None
    transparent_background: bool = False


@router.post("/generate-cover")
async def generate_cover(request: CoverGenerationRequest, req: Request):
    """
    Generate a chapter cover image with optional transparency using SDXL.
    
    Args:
        request: CoverGenerationRequest with generation parameters
        req: FastAPI Request object to access app state
    
    Returns:
        Image bytes (PNG format, with alpha channel if transparent_background=True)
    """
    try:
        app_state = req.app.state
        if not hasattr(app_state, "pipe"):
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        pipe = app_state.pipe
        
        # Set seed if provided
        generator = None
        if request.seed is not None:
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
            generator.manual_seed(request.seed)
        
        # Generate image
        logger.info(f"Generating SDXL cover image with prompt: {request.prompt[:50]}...")
        logger.info(f"Generation params: steps={request.num_inference_steps}, guidance={request.guidance_scale}, size={request.width}x{request.height}")
        
        # Initialize variables
        image = None
        use_layer_diffusion = False
        layer_diffusion = getattr(app_state, "layer_diffusion", None)
        
        # Try Layer Diffusion for transparency if requested
        if request.transparent_background and layer_diffusion is not None:
            logger.info("Attempting Layer Diffusion for native transparency...")
            try:
                # Layer Diffusion is already initialized, just use it
                if layer_diffusion.is_available() or layer_diffusion.enable_layer_diffusion():
                    # Generate with Layer Diffusion for native transparency
                    # Note: ControlNet + Layer Diffusion work together - Layer Diffusion modifies the pipeline
                    # and ControlNet conditions are passed through normally
                    image = layer_diffusion.generate_with_transparency(
                        prompt=request.prompt,
                        negative_prompt=request.negative_prompt,
                        width=request.width,
                        height=request.height,
                        num_inference_steps=request.num_inference_steps,
                        guidance_scale=request.guidance_scale,
                        generator=generator,
                        control_image=None,  # ControlNet is handled by the pipeline itself
                    )
                    use_layer_diffusion = True
                    logger.info("Image generated with Layer Diffusion transparency")
                else:
                    logger.warning("Layer Diffusion not available, falling back to post-processing")
                    
            except Exception as e:
                logger.warning(f"Layer Diffusion generation failed: {str(e)}, falling back to standard generation")
                use_layer_diffusion = False
                image = None
        
        # Standard generation (without transparency or if Layer Diffusion failed)
        if image is None:
            # SDXL text-to-image generation
            output = pipe(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                num_inference_steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale,
                generator=generator,
            )
            image = output.images[0]
        
        # If transparency was requested but Layer Diffusion wasn't used/available
        if request.transparent_background and not use_layer_diffusion:
            logger.warning("Transparent background requested but Layer Diffusion not available")
            logger.warning("Returning image without transparency - please rebuild container with LayerDiffuse_DiffusersCLI")
        
        # Convert to bytes with error handling
        try:
            img_byte_arr = io.BytesIO()
            # Ensure image is in correct mode before saving
            if image.mode == "RGBA":
                image.save(img_byte_arr, format='PNG')
            else:
                image = image.convert("RGB")
                image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            logger.info("Cover image generated successfully")
            return Response(content=img_byte_arr.getvalue(), media_type="image/png")
        except Exception as save_error:
            logger.error(f"Error saving image: {str(save_error)}")
            # Try saving without transparency as fallback
            try:
                image = image.convert("RGB")
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                logger.info("Cover image saved with RGB fallback")
                return Response(content=img_byte_arr.getvalue(), media_type="image/png")
            except Exception as fallback_error:
                logger.error(f"Fallback save also failed: {str(fallback_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to save image: {str(save_error)}")
        
    except Exception as e:
        logger.error(f"Error generating cover image: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")
