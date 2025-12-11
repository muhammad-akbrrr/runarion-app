from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLControlNetPipeline, ControlNetModel
import logging
import os
import io
import json
from PIL import Image
import numpy as np
import cv2
from dotenv import load_dotenv
from api.cover_generation import router as cover_router
from api.border_generation import router as border_router
from utils.layer_diffusion import LayerDiffusionProcessor

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stable Diffusion XL API")

# Configure CORS
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8000,http://python-app:5000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
CONTROLNET_MODEL_PATH = os.getenv("CONTROLNET_MODEL_PATH", "controlnet-sdxl")
STABLE_DIFFUSION_MODEL_PATH = os.getenv(
    "STABLE_DIFFUSION_MODEL_PATH", "juggernaut-xl-v11")  # Works with v8 or v11
USE_CONTROLNET = os.getenv("USE_CONTROLNET", "false").lower() == "true"
USE_SAFETENSORS = os.getenv("USE_SAFETENSORS", "true").lower() == "true"
ENABLE_MODEL_CACHING = os.getenv(
    "ENABLE_MODEL_CACHING", "true").lower() == "true"
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")
# Allow downloading from HuggingFace if models not found locally
ALLOW_HF_DOWNLOAD = os.getenv("ALLOW_HF_DOWNLOAD", "true").lower() == "true"
# SDXL model - default to base SDXL (available on HuggingFace)
# For Juggernaut XL v11, download from CivitAI and place in models/juggernaut-xl-v11/
SD_MODEL_ID = os.getenv("SD_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")

# Generation parameters (SDXL defaults)
NUM_INFERENCE_STEPS = int(os.getenv("NUM_INFERENCE_STEPS", "30"))
GUIDANCE_SCALE = float(os.getenv("GUIDANCE_SCALE", "5.0"))  # SDXL typically uses lower CFG

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
        logger.info("Loading SDXL models...")

        # Determine model path
        local_sd_path = os.path.join(MODELS_DIR, STABLE_DIFFUSION_MODEL_PATH)
        # Check if local model exists and is properly structured
        local_model_exists = False
        local_files_only = False
        checkpoint_file = None
        
        # Check for diffusers format (has model_index.json)
        if os.path.exists(local_sd_path) and os.path.exists(os.path.join(local_sd_path, "model_index.json")):
            local_model_exists = True
            local_files_only = not ALLOW_HF_DOWNLOAD
            logger.info(f"Found diffusers format model at {local_sd_path}")
        # Check for checkpoint format (single .safetensors file)
        elif os.path.exists(local_sd_path):
            safetensors_files = [f for f in os.listdir(local_sd_path) if f.endswith('.safetensors')]
            if safetensors_files:
                checkpoint_file = os.path.join(local_sd_path, safetensors_files[0])
                logger.info(f"Found checkpoint file: {checkpoint_file}")
                logger.info("Will load Juggernaut model from checkpoint format")
                local_model_exists = True

        # =================================================================
        # STEP 1: Load regular SDXL pipeline (for covers - no ControlNet)
        # =================================================================
        pipe = None
        
        # Try loading from checkpoint file first (Juggernaut)
        if checkpoint_file:
            try:
                logger.info(f"Loading Juggernaut model from checkpoint: {checkpoint_file}")
                pipe = StableDiffusionXLPipeline.from_single_file(
                    checkpoint_file,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                )
                logger.info("Loaded Juggernaut SDXL pipeline from checkpoint")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {str(e)}")
                logger.warning("Falling back to HuggingFace download...")
                checkpoint_file = None
                local_model_exists = False
        
        # Load from HuggingFace or diffusers format if checkpoint failed
        if pipe is None:
            logger.info(f"Loading SDXL model from {'local diffusers path' if local_model_exists else 'HuggingFace'}...")
            try:
                pipe = StableDiffusionXLPipeline.from_pretrained(
                    local_sd_path if local_model_exists else SD_MODEL_ID,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    variant="fp16" if torch.cuda.is_available() else None,
                    local_files_only=local_model_exists and not ALLOW_HF_DOWNLOAD,
                    use_safetensors=USE_SAFETENSORS,
                    cache_dir=CACHE_DIR if ENABLE_MODEL_CACHING else None
                )
                logger.info("Loaded SDXL pipeline")
            except Exception as e:
                logger.error(f"Failed to load SDXL pipeline: {str(e)}")
                raise

        # Move to GPU if available and configured
        use_gpu = False
        if torch.cuda.is_available() and USE_CUDA:
            try:
                logger.info("Moving pipeline to GPU...")
                pipe = pipe.to("cuda")
                logger.info("Pipeline moved to GPU successfully")
                use_gpu = True
                if ENABLE_XFORMERS:
                    try:
                        pipe.enable_xformers_memory_efficient_attention()
                        logger.info("XFormers memory efficient attention enabled")
                    except Exception as e:
                        logger.warning(f"XFormers not available: {str(e)}")
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
                logger.info("SDXL models loaded and moved to GPU with configured optimizations")
            except Exception as e:
                logger.warning(f"GPU setup failed: {str(e)}. Falling back to CPU.")
                use_gpu = False
        else:
            logger.warning("CUDA not available or disabled, using CPU")
            use_gpu = False
        
        # For CPU, enable optimizations
        if not use_gpu and ENABLE_ATTENTION_SLICING:
            pipe.enable_attention_slicing()
            logger.info("Attention slicing enabled for CPU")

        logger.info("Storing main pipeline in app state...")
        app.state.pipe = pipe  # Regular SDXL pipeline for covers
        logger.info("Main pipeline stored in app state")

        # =================================================================
        # STEP 2: Load ControlNet model + pipeline (for borders - optional)
        # =================================================================
        controlnet = None
        controlnet_pipe = None
        
        if USE_CONTROLNET:
            try:
                local_cn_path = os.path.join(MODELS_DIR, CONTROLNET_MODEL_PATH)
                default_cn_id = os.getenv("CONTROLNET_MODEL_ID", "diffusers/controlnet-canny-sdxl-1.0")
                
                # Check if local ControlNet exists (needs config.json)
                has_local_cn = os.path.exists(local_cn_path) and os.path.exists(os.path.join(local_cn_path, "config.json"))
                
                if has_local_cn:
                    logger.info(f"Loading ControlNet from local path: {local_cn_path}")
                    controlnet = ControlNetModel.from_pretrained(
                        local_cn_path,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        use_safetensors=USE_SAFETENSORS,
                    )
                elif ALLOW_HF_DOWNLOAD:
                    logger.info(f"Downloading ControlNet from HuggingFace: {default_cn_id}")
                    controlnet = ControlNetModel.from_pretrained(
                        default_cn_id,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        use_safetensors=USE_SAFETENSORS,
                        cache_dir=CACHE_DIR if ENABLE_MODEL_CACHING else None
                    )
                else:
                    logger.warning("No local ControlNet and HF download disabled, skipping ControlNet")
                    
                if controlnet:
                    logger.info("SDXL ControlNet model loaded successfully")
                    
                    # Create ControlNet pipeline (separate from main pipeline)
                    # Reuse components from main pipeline for memory efficiency
                    logger.info("Creating ControlNet pipeline (shares components with main pipeline)...")
                    controlnet_pipe = StableDiffusionXLControlNetPipeline(
                        vae=pipe.vae,
                        text_encoder=pipe.text_encoder,
                        text_encoder_2=pipe.text_encoder_2,
                        tokenizer=pipe.tokenizer,
                        tokenizer_2=pipe.tokenizer_2,
                        unet=pipe.unet,
                        controlnet=controlnet,
                        scheduler=pipe.scheduler,
                    )
                    
                    # Move ControlNet to GPU if main pipeline is on GPU
                    if use_gpu:
                        controlnet_pipe = controlnet_pipe.to("cuda")
                        if ENABLE_XFORMERS:
                            try:
                                controlnet_pipe.enable_xformers_memory_efficient_attention()
                            except:
                                pass
                    
                    logger.info("ControlNet pipeline created successfully")
                    
            except Exception as e:
                logger.warning(f"Failed to load ControlNet: {str(e)}. Border generation will be unavailable.")
                controlnet = None
                controlnet_pipe = None
        
        # Store ControlNet pipeline separately
        app.state.controlnet = controlnet
        app.state.controlnet_pipe = controlnet_pipe
        app.state.use_controlnet = controlnet_pipe is not None
        logger.info(f"ControlNet available: {app.state.use_controlnet}")
        
        # =================================================================
        # STEP 3: Initialize Layer Diffusion for transparency
        # =================================================================
        logger.info("Initializing Layer Diffusion processor...")
        try:
            layer_diffusion = LayerDiffusionProcessor(pipe=pipe)
            app.state.layer_diffusion = layer_diffusion
            if layer_diffusion.is_available():
                logger.info("Layer Diffusion processor initialized successfully (native transparency)")
            else:
                logger.warning("Layer Diffusion library not available, transparency will be disabled")
        except Exception as e:
            logger.warning(f"Layer Diffusion initialization failed: {str(e)}.")
            app.state.layer_diffusion = None
        
        logger.info("SDXL startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        app.state.startup_error = str(e)
        raise

# Register routers
app.include_router(cover_router, prefix="/api", tags=["cover-generation"])
app.include_router(border_router, prefix="/api", tags=["border-generation"])


@app.get("/health")
async def health_check():
    try:
        # Quick check - don't run actual inference (too slow for health checks)
        model_loaded = hasattr(app.state, "pipe")
        model_ready = False
        startup_error = getattr(app.state, "startup_error", None)
        
        if startup_error:
            return Response(
                content=json.dumps({
                    "status": "error",
                    "error": str(startup_error),
                    "cuda_available": torch.cuda.is_available(),
                    "model_loaded": False,
                    "model_ready": False,
                    "use_controlnet": False,
                    "model_type": "SDXL"
                }),
                status_code=503,
                media_type="application/json"
            )
        
        if model_loaded:
            # Just check if pipe exists and has required attributes
            # SDXL has text_encoder and text_encoder_2
            try:
                pipe = app.state.pipe
                # More lenient check - if pipe exists, it's ready
                # The hasattr checks might fail if pipe is partially loaded, but if it exists, we can use it
                model_ready = pipe is not None
                # Try to verify it's actually a valid pipeline (but don't fail if attributes are missing)
                if model_ready:
                    try:
                        # Quick validation - just check if it has the basic structure
                        # If any of these fail, the pipe isn't ready
                        _ = pipe.unet  # This will raise if not loaded
                        _ = pipe.vae
                        _ = pipe.text_encoder
                        _ = pipe.text_encoder_2
                        # If we get here, all components are loaded
                        model_ready = True
                    except (AttributeError, TypeError) as e:
                        # If attributes don't exist or are None, it's not ready
                        logger.debug(f"Pipeline components not fully loaded: {str(e)}")
                        model_ready = False
            except Exception as e:
                logger.warning(f"Health check model validation failed: {str(e)}")
                model_ready = False

        # If model is loaded, consider it healthy even if optimizations are still initializing
        # This allows generation to proceed while optimizations finish
        if model_loaded and model_ready:
            status = "healthy"
        elif model_loaded:
            # Model is loaded but not fully ready - still allow generation
            status = "healthy"  # Treat as healthy if model is loaded
        else:
            status = "initializing"
        status_code = 200 if status == "healthy" else 503
        
        response_data = {
            "status": status,
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": model_loaded,
            "model_ready": model_ready,
            "use_controlnet": getattr(app.state, "use_controlnet", False),
            "model_type": "SDXL",
            "message": "Service is initializing. Models are still loading..." if status == "initializing" else "Service is ready"
        }
        
        if status_code != 200:
            return Response(
                content=json.dumps(response_data),
                status_code=status_code,
                media_type="application/json"
            )
        return response_data
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response(
            content=json.dumps({
                "status": "error",
                "error": str(e),
                "cuda_available": torch.cuda.is_available(),
                "model_loaded": hasattr(app.state, "pipe"),
                "model_ready": False,
                "model_type": "SDXL"
            }),
            status_code=503,
            media_type="application/json"
        )


@app.get("/generate")
async def generate_image(prompt: str):
    try:
        if not hasattr(app.state, "pipe"):
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        pipe = app.state.pipe
        
        # Generate image (with or without ControlNet)
        # SDXL uses different default resolution (1024x1024)
        if hasattr(app.state, "use_controlnet") and app.state.use_controlnet:
            # Create a simple test image for ControlNet
            test_image = np.ones((1024, 1024, 3), dtype=np.uint8) * 255
            test_image = cv2.Canny(test_image, 100, 200)
            test_image = Image.fromarray(test_image)
            output = pipe(
                prompt=prompt,
                image=test_image,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                width=1024,
                height=1024,
            )
        else:
            # Simple text-to-image without ControlNet
            output = pipe(
                prompt=prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                width=1024,
                height=1024,
            )

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        output.images[0].save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
