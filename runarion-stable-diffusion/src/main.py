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
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stable Diffusion API")

# Configure CORS
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:5000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
CONTROLNET_MODEL_PATH = os.getenv("CONTROLNET_MODEL_PATH", "controlnet")
STABLE_DIFFUSION_MODEL_PATH = os.getenv(
    "STABLE_DIFFUSION_MODEL_PATH", "stable-diffusion-v1-5")
USE_SAFETENSORS = os.getenv("USE_SAFETENSORS", "true").lower() == "true"
ENABLE_MODEL_CACHING = os.getenv(
    "ENABLE_MODEL_CACHING", "true").lower() == "true"
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")

# Generation parameters
NUM_INFERENCE_STEPS = int(os.getenv("NUM_INFERENCE_STEPS", "20"))
GUIDANCE_SCALE = float(os.getenv("GUIDANCE_SCALE", "7.5"))

# GPU configuration
USE_CUDA = os.getenv("USE_CUDA", "true").lower() == "true"
ENABLE_XFORMERS = os.getenv("ENABLE_XFORMERS", "true").lower() == "true"
ENABLE_CPU_OFFLOAD = os.getenv("ENABLE_CPU_OFFLOAD", "true").lower() == "true"
ENABLE_SEQUENTIAL_CPU_OFFLOAD = os.getenv(
    "ENABLE_SEQUENTIAL_CPU_OFFLOAD", "true").lower() == "true"
ENABLE_ATTENTION_SLICING = os.getenv(
    "ENABLE_ATTENTION_SLICING", "true").lower() == "true"
ENABLE_VAE_TILING = os.getenv("ENABLE_VAE_TILING", "true").lower() == "true"
ENABLE_GRADIENT_CHECKPOINTING = os.getenv(
    "ENABLE_GRADIENT_CHECKPOINTING", "true").lower() == "true"

# Create cache directory if it doesn't exist
if ENABLE_MODEL_CACHING:
    os.makedirs(CACHE_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Loading models...")

        # Load ControlNet model
        controlnet = ControlNetModel.from_pretrained(
            os.path.join(MODELS_DIR, CONTROLNET_MODEL_PATH),
            torch_dtype=torch.float16,
            local_files_only=True,
            use_safetensors=USE_SAFETENSORS,
            cache_dir=CACHE_DIR if ENABLE_MODEL_CACHING else None
        )

        # Load Stable Diffusion model
        pipe = StableDiffusionPipeline.from_pretrained(
            os.path.join(MODELS_DIR, STABLE_DIFFUSION_MODEL_PATH),
            controlnet=controlnet,
            torch_dtype=torch.float16,
            local_files_only=True,
            safety_checker=None,
            requires_safety_checker=False,
            use_safetensors=USE_SAFETENSORS,
            cache_dir=CACHE_DIR if ENABLE_MODEL_CACHING else None
        )

        # Move to GPU if available and configured
        if torch.cuda.is_available() and USE_CUDA:
            pipe = pipe.to("cuda")
            if ENABLE_XFORMERS:
                pipe.enable_xformers_memory_efficient_attention()
                logger.info("XFormers memory efficient attention enabled")
            if ENABLE_SEQUENTIAL_CPU_OFFLOAD:
                pipe.enable_sequential_cpu_offload()
                logger.info("Sequential CPU offload enabled")
            if ENABLE_ATTENTION_SLICING:
                pipe.enable_attention_slicing()
                logger.info("Attention slicing enabled")
            if ENABLE_VAE_TILING:
                pipe.enable_vae_tiling()
                logger.info("VAE tiling enabled")
            if ENABLE_GRADIENT_CHECKPOINTING:
                pipe.unet.enable_gradient_checkpointing()
                logger.info("Gradient checkpointing enabled")
            logger.info(
                "Models loaded and moved to GPU with configured optimizations")
        else:
            logger.warning("CUDA not available or disabled, using CPU")

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
            "model_initialized": pipe_initialized
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
            num_inference_steps=NUM_INFERENCE_STEPS,
            guidance_scale=GUIDANCE_SCALE,
        )

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        output.images[0].save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
