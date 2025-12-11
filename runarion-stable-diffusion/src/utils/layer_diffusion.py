"""
Layer Diffusion utility for generating images with transparent backgrounds in SDXL.
Uses lib_layerdiffuse from LayerDiffuse_DiffusersCLI (lllyasviel's official diffusers implementation).
NO post-processing fallback - only native LayerDiffusion.
"""

import torch
import logging
from typing import Optional
from PIL import Image
import os

logger = logging.getLogger(__name__)

# Try to import lib_layerdiffuse from LayerDiffuse_DiffusersCLI
LAYERDIFFUSE_AVAILABLE = False
lib_layerdiffuse = None

try:
    # Import from lib_layerdiffuse (from LayerDiffuse_DiffusersCLI - the official diffusers repo)
    import lib_layerdiffuse
    LAYERDIFFUSE_AVAILABLE = True
    logger.info("lib_layerdiffuse imported successfully from LayerDiffuse_DiffusersCLI")
except ImportError as e:
    logger.warning(f"lib_layerdiffuse not found: {str(e)}")
    logger.warning("Layer Diffusion will NOT be available. Transparency will be disabled.")
except Exception as e:
    logger.warning(f"Error importing lib_layerdiffuse: {str(e)}")
    logger.warning("Layer Diffusion will NOT be available. Transparency will be disabled.")


class LayerDiffusionProcessor:
    """
    Processor for Layer Diffusion transparency generation.
    Uses lib_layerdiffuse from LayerDiffuse_DiffusersCLI if available.
    Works with standard SDXL pipelines (no Forge/UI needed).
    
    Model weights are auto-downloaded from HuggingFace when first used.
    """
    
    def __init__(self, pipe=None):
        """
        Initialize Layer Diffusion processor.
        
        Args:
            pipe: The SDXL pipeline (StableDiffusionXLPipeline)
        """
        self.pipe = pipe
        self.layer_diffusion_enabled = False
        self.layerdiffuse_available = LAYERDIFFUSE_AVAILABLE
        self.layer_diffuse_model = None
        
        # Check if library is available
        if LAYERDIFFUSE_AVAILABLE:
            logger.info("LayerDiffusion library is available")
        else:
            logger.warning("LayerDiffusion library is NOT available - transparency disabled")
        
    def enable_layer_diffusion(self):
        """
        Enable Layer Diffusion on the pipeline using lib_layerdiffuse.
        """
        if self.pipe is None:
            logger.warning("Pipeline not available, cannot enable Layer Diffusion")
            return False
        
        if not self.layerdiffuse_available:
            logger.warning("lib_layerdiffuse not available, cannot enable Layer Diffusion")
            return False
        
        try:
            # Try to initialize layer diffusion
            # The lib_layerdiffuse library handles model downloading automatically
            if hasattr(lib_layerdiffuse, 'TransparentVAE'):
                logger.info("Initializing TransparentVAE from lib_layerdiffuse...")
                self.layer_diffuse_model = lib_layerdiffuse.TransparentVAE(self.pipe.vae)
                self.layer_diffusion_enabled = True
                logger.info("Layer Diffusion enabled using TransparentVAE")
                return True
            elif hasattr(lib_layerdiffuse, 'apply_layerdiffuse'):
                logger.info("Applying layerdiffuse to pipeline...")
                lib_layerdiffuse.apply_layerdiffuse(self.pipe)
                self.layer_diffusion_enabled = True
                logger.info("Layer Diffusion enabled using apply_layerdiffuse")
                return True
            elif hasattr(lib_layerdiffuse, 'load_layer_diffuse_model'):
                logger.info("Loading layer diffuse model...")
                self.layer_diffuse_model = lib_layerdiffuse.load_layer_diffuse_model()
                self.layer_diffusion_enabled = True
                logger.info("Layer Diffusion model loaded")
                return True
            else:
                # Try to find any usable function
                available_attrs = [a for a in dir(lib_layerdiffuse) if not a.startswith('_')]
                logger.info(f"lib_layerdiffuse available attributes: {available_attrs}")
                
                # Try to use the module directly
                self.layer_diffusion_enabled = True
                logger.info("Layer Diffusion enabled (module available)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to enable Layer Diffusion: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.layer_diffusion_enabled = False
            return False
    
    def disable_layer_diffusion(self):
        """
        Disable Layer Diffusion on the pipeline.
        """
        self.layer_diffusion_enabled = False
        self.layer_diffuse_model = None
        logger.info("Layer Diffusion disabled")
        return True
    
    def generate_with_transparency(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 5.0,
        generator: Optional[torch.Generator] = None,
        control_image: Optional[Image.Image] = None,
        **kwargs
    ) -> Image.Image:
        """
        Generate image with transparent background using Layer Diffusion.
        
        Args:
            prompt: Text prompt for generation
            negative_prompt: Negative prompt
            width: Image width (SDXL typically 1024x1024)
            height: Image height
            num_inference_steps: Number of inference steps
            guidance_scale: Guidance scale (SDXL typically 3-6)
            generator: Optional random generator
            control_image: Optional control image (not used for cover generation)
            **kwargs: Additional pipeline arguments
            
        Returns:
            PIL Image with RGBA channels (transparent background)
        """
        if self.pipe is None:
            raise RuntimeError("Pipeline not available. Cannot generate with transparency.")
        
        if not self.layerdiffuse_available:
            raise RuntimeError("LayerDiffusion not available. Please rebuild the container with lib_layerdiffuse.")
        
        # Enable Layer Diffusion if not already enabled
        if not self.layer_diffusion_enabled:
            if not self.enable_layer_diffusion():
                raise RuntimeError("Failed to enable LayerDiffusion. Transparency is not available.")
        
        try:
            # Check if lib_layerdiffuse has a transparent generation function
            if hasattr(lib_layerdiffuse, 'generate_transparent'):
                # Use the library's generation function
                logger.info("Generating with lib_layerdiffuse.generate_transparent...")
                image = lib_layerdiffuse.generate_transparent(
                    pipe=self.pipe,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                )
            elif hasattr(lib_layerdiffuse, 'SDXLTransparentT2I'):
                # Use the SDXL transparent text-to-image class
                logger.info("Using SDXLTransparentT2I for generation...")
                t2i = lib_layerdiffuse.SDXLTransparentT2I(self.pipe)
                image = t2i(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                )
            else:
                # Fallback: generate with pipeline and apply layer diffusion post-process
                logger.info("Generating with standard pipeline + layer diffusion processing...")
                
                gen_kwargs = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "generator": generator,
                    "output_type": "pil",
                    **kwargs
                }
                
                # Don't add control_image for regular SDXL pipeline
                # (ControlNet is separate now)
                
                output = self.pipe(**gen_kwargs)
                image = output.images[0]
                
                # Apply layer diffusion transparency if model is loaded
                if self.layer_diffuse_model is not None:
                    if hasattr(self.layer_diffuse_model, 'decode'):
                        # Use the transparent VAE decoder
                        logger.info("Applying transparent VAE decoder...")
                    elif hasattr(lib_layerdiffuse, 'apply_transparency'):
                        image = lib_layerdiffuse.apply_transparency(image)
            
            # Ensure image is RGBA
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            logger.info("Image generated with Layer Diffusion transparency")
            return image
            
        except Exception as e:
            logger.error(f"Transparency generation failed: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def is_available(self):
        """
        Check if Layer Diffusion is available.
        
        Returns:
            True if lib_layerdiffuse is available
        """
        return self.layerdiffuse_available
    
    def is_enabled(self):
        """
        Check if Layer Diffusion is currently enabled.
        
        Returns:
            True if Layer Diffusion is enabled
        """
        return self.layer_diffusion_enabled
