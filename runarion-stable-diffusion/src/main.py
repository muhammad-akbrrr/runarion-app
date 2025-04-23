from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import torch
from diffusers import StableDiffusionPipeline, ControlNetModel
import logging
import os
import io
from PIL import Image
import numpy as np
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stable Diffusion API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
MODELS_DIR = "/app/models"


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Loading models...")

        # Load ControlNet model
        controlnet = ControlNetModel.from_pretrained(
            os.path.join(MODELS_DIR, "controlnet"),
            torch_dtype=torch.float16,
            local_files_only=True,
            use_safetensors=False
        )

        # Load Stable Diffusion model
        pipe = StableDiffusionPipeline.from_pretrained(
            os.path.join(MODELS_DIR, "stable-diffusion-v1-5"),
            controlnet=controlnet,
            torch_dtype=torch.float16,
            local_files_only=True,
            safety_checker=None,
            requires_safety_checker=False
        )

        # Move to GPU if available
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
            pipe.enable_xformers_memory_efficient_attention()
            pipe.enable_model_cpu_offload()
            logger.info(
                "Models loaded and moved to GPU with xformers and CPU offload enabled")
        else:
            logger.warning("CUDA not available, using CPU")

        app.state.pipe = pipe
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


@app.get("/health")
async def health_check():
    try:
        pipe_initialized = False
        if hasattr(app.state, "pipe"):
            try:
                # Try a simple inference to verify the model works
                test_image = np.ones((512, 512, 3), dtype=np.uint8) * 255
                test_image = cv2.Canny(test_image, 100, 200)
                test_image = Image.fromarray(test_image)
                app.state.pipe(
                    prompt="test",
                    image=test_image,
                    num_inference_steps=1,
                    guidance_scale=7.5,
                )
                pipe_initialized = True
            except Exception as e:
                logger.error(f"Model initialization check failed: {str(e)}")
                pipe_initialized = False

        return {
            "status": "healthy" if pipe_initialized else "initializing",
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": hasattr(app.state, "pipe"),
            "model_initialized": pipe_initialized,
            "xformers_enabled": hasattr(app.state, "pipe") and hasattr(app.state.pipe, "enable_xformers_memory_efficient_attention")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generate")
async def generate_image(prompt: str):
    try:
        # Create a simple test image for ControlNet
        test_image = np.ones((512, 512, 3), dtype=np.uint8) * 255
        test_image = cv2.Canny(test_image, 100, 200)
        test_image = Image.fromarray(test_image)

        # Generate image
        output = app.state.pipe(
            prompt=prompt,
            image=test_image,
            num_inference_steps=20,
            guidance_scale=7.5,
        )

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        output.images[0].save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add more endpoints here for image generation, etc.
