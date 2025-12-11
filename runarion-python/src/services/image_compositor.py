"""
Image compositing service for overlaying borders on chapter cover images.
"""

import os
import io
import logging
from PIL import Image
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ImageCompositor:
    """Service for compositing images with border templates."""
    
    def __init__(self, border_templates_dir: str = None):
        """
        Initialize the compositor.
        
        Args:
            border_templates_dir: Directory containing border template images
        """
        if border_templates_dir:
            self.border_templates_dir = border_templates_dir
        else:
            # Use a safe default path that works in both Docker and local
            default_dir = os.getenv('BORDER_TEMPLATES_DIR', '/app/storage/border_templates')
            # Fallback to relative path if absolute doesn't work
            if not os.path.isabs(default_dir):
                default_dir = os.path.join(
                    os.path.dirname(__file__), '../../storage/border_templates'
                )
            self.border_templates_dir = default_dir
        
        # Create directory safely
        try:
            os.makedirs(self.border_templates_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not create border templates directory {self.border_templates_dir}: {e}")
            # Use a fallback directory
            self.border_templates_dir = '/tmp/border_templates'
            try:
                os.makedirs(self.border_templates_dir, exist_ok=True)
            except Exception:
                logger.error("Could not create fallback border templates directory")
                self.border_templates_dir = None
    
    def composite_with_border(
        self,
        base_image: bytes,
        border_template_path: Optional[str] = None,
        border_template_bytes: Optional[bytes] = None,
        position: str = "center"
    ) -> bytes:
        """
        Composite a base image with a border template.
        
        Args:
            base_image: Base image bytes (PNG)
            border_template_path: Path to border template file
            border_template_bytes: Border template as bytes (alternative to path)
            position: Position of base image relative to border ("center", "top", "bottom", etc.)
        
        Returns:
            Composited image bytes (PNG)
        """
        try:
            # Load base image
            base = Image.open(io.BytesIO(base_image)).convert("RGBA")
            
            # Load border template
            if border_template_bytes:
                border = Image.open(io.BytesIO(border_template_bytes)).convert("RGBA")
            elif border_template_path:
                if os.path.exists(border_template_path):
                    border = Image.open(border_template_path).convert("RGBA")
                else:
                    logger.warning(f"Border template not found: {border_template_path}, skipping border")
                    # Return base image without border
                    output = io.BytesIO()
                    base.save(output, format='PNG')
                    return output.getvalue()
            else:
                # No border specified, return base image
                output = io.BytesIO()
                base.save(output, format='PNG')
                return output.getvalue()
            
            # Resize base image to fit within border (with padding)
            # Calculate padding (e.g., 5% of border size)
            padding_ratio = 0.05
            border_width, border_height = border.size
            max_base_width = int(border_width * (1 - 2 * padding_ratio))
            max_base_height = int(border_height * (1 - 2 * padding_ratio))
            
            # Maintain aspect ratio
            base_aspect = base.width / base.height
            max_aspect = max_base_width / max_base_height
            
            if base_aspect > max_aspect:
                # Base is wider, fit to width
                new_width = max_base_width
                new_height = int(new_width / base_aspect)
            else:
                # Base is taller, fit to height
                new_height = max_base_height
                new_width = int(new_height * base_aspect)
            
            base_resized = base.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Calculate position for centering
            x_offset = (border_width - new_width) // 2
            y_offset = (border_height - new_height) // 2
            
            # Adjust based on position parameter
            if position == "top":
                y_offset = int(border_height * padding_ratio)
            elif position == "bottom":
                y_offset = border_height - new_height - int(border_height * padding_ratio)
            elif position == "left":
                x_offset = int(border_width * padding_ratio)
            elif position == "right":
                x_offset = border_width - new_width - int(border_width * padding_ratio)
            
            # Composite: paste base image onto border
            result = border.copy()
            result.paste(base_resized, (x_offset, y_offset), base_resized)
            
            # Convert to bytes
            output = io.BytesIO()
            result.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error compositing image: {str(e)}")
            raise
    
    def save_border_template(self, template_bytes: bytes, template_name: str) -> str:
        """
        Save a border template for later use.
        
        Args:
            template_bytes: Border template image bytes
            template_name: Name for the template
        
        Returns:
            Path to saved template
        """
        template_path = os.path.join(self.border_templates_dir, f"{template_name}.png")
        with open(template_path, 'wb') as f:
            f.write(template_bytes)
        logger.info(f"Saved border template: {template_path}")
        return template_path
    
    def list_border_templates(self) -> list:
        """
        List available border templates.
        
        Returns:
            List of template names (without extension)
        """
        templates = []
        if self.border_templates_dir and os.path.exists(self.border_templates_dir):
            try:
                for filename in os.listdir(self.border_templates_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        templates.append(os.path.splitext(filename)[0])
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not list border templates: {e}")
        return templates

