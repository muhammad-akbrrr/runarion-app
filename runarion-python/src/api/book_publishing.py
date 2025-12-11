"""
API endpoints for book publishing features: image generation and PDF creation.
"""

from flask import Blueprint, request, jsonify, send_file
import io
import logging
import os
from services.image_compositor import ImageCompositor
from services.pdf_generator import PDFGenerator
import requests

logger = logging.getLogger(__name__)

book_publishing = Blueprint("book_publishing", __name__)

# Lazy initialization - only create when needed to avoid startup crashes
_image_compositor = None
_pdf_generator = None

def get_image_compositor():
    """Get or create ImageCompositor instance."""
    global _image_compositor
    if _image_compositor is None:
        _image_compositor = ImageCompositor()
    return _image_compositor

def get_pdf_generator():
    """Get or create PDFGenerator instance."""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = PDFGenerator()
    return _pdf_generator

# Stable Diffusion service URL (from environment or default)
# Note: Service name is 'stable-diffusion' in docker-compose, port 7860
# For local dev, use localhost:7860
def get_stable_diffusion_url():
    """Get Stable Diffusion service URL, auto-detecting Docker vs local."""
    url = os.getenv('STABLE_DIFFUSION_URL')
    if url:
        return url
    
    # Auto-detect: Check if we're in Docker
    is_docker = os.path.exists('/.dockerenv') or os.getenv('container') is not None
    return 'http://stable-diffusion:7860' if is_docker else 'http://localhost:7860'

STABLE_DIFFUSION_URL = get_stable_diffusion_url()


@book_publishing.route('/generate-chapter-cover', methods=['POST'])
def generate_chapter_cover():
    """
    Generate a chapter cover image using Stable Diffusion.
    
    Request body:
    {
        "prompt": "mystical forest scene",
        "chapter_id": 1,
        "width": 1024,
        "height": 1024,
        "transparent_background": false,
        "border_template_path": null
    }
    
    Returns:
        Image bytes (PNG)
    """
    try:
        data = request.get_json()
        
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Just try to call Stable Diffusion - let it handle its own readiness
        # If it's not ready, it will return an error we can handle
        # No need for complex health checks - just make the request and wait
        sd_request = {
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', 'text, watermark, signature, low quality, blurry'),
            'width': data.get('width', 1024),
            'height': data.get('height', 1024),
            'num_inference_steps': data.get('num_inference_steps', 30),
            'guidance_scale': data.get('guidance_scale', 7.5),
            'seed': data.get('seed'),
            'transparent_background': data.get('transparent_background', False)
        }
        
        logger.info(f"Calling Stable Diffusion service for chapter cover: {prompt[:50]}...")
        logger.info(f"Generation params: steps={sd_request['num_inference_steps']}, guidance={sd_request['guidance_scale']}, size={sd_request['width']}x{sd_request['height']}")
        
        try:
            response = requests.post(
                f"{STABLE_DIFFUSION_URL}/api/generate-cover",
                json=sd_request,
                timeout=600  # 10 minutes for SDXL image generation (can take 5-7 minutes)
            )
        except requests.exceptions.ConnectionError:
            # Service is not running at all
            return jsonify({
                'error': 'Stable Diffusion service is not running',
                'details': f'Could not connect to {STABLE_DIFFUSION_URL}. Make sure the service is started.',
                'hint': 'Start the service with: docker compose -f docker-compose.dev.yml up -d stable-diffusion. PDF generation works without it.'
            }), 503
        except requests.exceptions.Timeout:
            logger.error("Stable Diffusion service timeout")
            return jsonify({
                'error': 'Stable Diffusion service timeout',
                'details': 'The service took too long to respond. Generation can take 5-10 minutes. Try again or check if the service is running.'
            }), 504
        
        if response.status_code != 200:
            logger.error(f"Stable Diffusion service error: {response.status_code}")
            # Try to get error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', error_data.get('error', f'Service returned status {response.status_code}'))
            except:
                error_text = response.text[:500] if response.text else "Unknown error"
                error_msg = error_text
            
            return jsonify({
                'error': f'Stable Diffusion service error: {response.status_code}',
                'details': error_msg
            }), response.status_code
        
        image_bytes = response.content
        logger.info(f"Received image from Stable Diffusion: {len(image_bytes)} bytes")
        
        # Apply border if specified
        border_template_path = data.get('border_template_path')
        if border_template_path:
            try:
                compositor = get_image_compositor()
                image_bytes = compositor.composite_with_border(
                    image_bytes,
                    border_template_path=border_template_path
                )
                logger.info(f"Applied border, final image size: {len(image_bytes)} bytes")
            except Exception as e:
                logger.warning(f"Failed to apply border, returning image without border: {str(e)}")
                # Continue without border if compositing fails
        
        # Return image
        logger.info(f"Returning image to client: {len(image_bytes)} bytes")
        try:
            return send_file(
                io.BytesIO(image_bytes),
                mimetype='image/png',
                as_attachment=False
            )
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            raise
        
    except requests.exceptions.Timeout:
        logger.error("Stable Diffusion service timeout")
        return jsonify({
            'error': 'Stable Diffusion service timeout',
            'details': 'The service took too long to respond. Try again or check if the service is running.'
        }), 504
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Error connecting to Stable Diffusion service: {str(e)}")
        return jsonify({
            'error': 'Failed to connect to Stable Diffusion service',
            'details': f'Cannot reach {STABLE_DIFFUSION_URL}',
            'hint': 'Make sure Stable Diffusion is running. Check the service URL in your .env file.'
        }), 503
    except Exception as e:
        logger.error(f"Error generating chapter cover: {str(e)}")
        return jsonify({
            'error': 'Failed to generate chapter cover',
            'details': str(e)
        }), 500


@book_publishing.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Generate a PDF book from chapters with covers.
    
    Request body:
    {
        "chapters": [
            {
                "title": "Chapter 1",
                "content": "Chapter content...",
                "cover_image_bytes": "<base64_encoded_image>" (optional)
            }
        ],
        "paper_size": "a4",
        "margins": {
            "top": 1.0,
            "bottom": 1.0,
            "left": 1.25,
            "right": 1.25
        },
        "font_name": "Times-Roman",
        "font_size": 12,
        "line_spacing": 1.5,
        "include_covers": true,
        "drop_cap": true,
        "drop_cap_font": "UnifrakturCook",
        "drop_cap_uppercase": true,
        "chapter_borders": false,
        "include_toc": true
    }
    
    Returns:
        PDF file
    """
    try:
        data = request.get_json()
        
        chapters = data.get('chapters', [])
        if not chapters:
            return jsonify({'error': 'At least one chapter is required'}), 400
        
        # Decode base64 images if provided
        import base64
        for chapter in chapters:
            if chapter.get('cover_image_bytes'):
                try:
                    # Handle base64 string (remove data URL prefix if present)
                    image_data_str = chapter['cover_image_bytes']
                    if isinstance(image_data_str, str):
                        # Remove data URL prefix if present (e.g., "data:image/png;base64,")
                        if ',' in image_data_str:
                            image_data_str = image_data_str.split(',', 1)[1]
                        image_data = base64.b64decode(image_data_str)
                        chapter['cover_image_bytes'] = image_data
                    elif isinstance(image_data_str, bytes):
                        # Already bytes, use as-is
                        chapter['cover_image_bytes'] = image_data_str
                except Exception as e:
                    logger.warning(f"Failed to decode cover image for chapter '{chapter.get('title', 'Unknown')}': {str(e)}")
                    chapter['cover_image_bytes'] = None
        
        # Generate PDF with all new features
        generator = get_pdf_generator()
        pdf_bytes = generator.generate_pdf(
            chapters=chapters,
            paper_size=data.get('paper_size', 'a4'),
            margins=data.get('margins'),
            font_name=data.get('font_name', 'Times-Roman'),
            font_size=data.get('font_size', 12),
            line_spacing=data.get('line_spacing', 1.5),
            include_covers=data.get('include_covers', True),
            # New features
            drop_cap=data.get('drop_cap', True),
            drop_cap_font=data.get('drop_cap_font', 'UnifrakturCook'),
            drop_cap_uppercase=data.get('drop_cap_uppercase', True),
            chapter_borders=data.get('chapter_borders', False),
            include_toc=data.get('include_toc', True)
        )
        
        # Return PDF
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='book.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({
            'error': 'Failed to generate PDF',
            'details': str(e)
        }), 500


@book_publishing.route('/composite-image', methods=['POST'])
def composite_image():
    """
    Composite an image with a border template.
    
    Request body (multipart/form-data):
    - base_image: Image file
    - border_template: Border template file (optional)
    - border_template_path: Path to saved border template (optional)
    - position: Position of base image ("center", "top", "bottom", etc.)
    
    Returns:
        Composited image bytes (PNG)
    """
    try:
        if 'base_image' not in request.files:
            return jsonify({'error': 'base_image is required'}), 400
        
        base_image_file = request.files['base_image']
        base_image_bytes = base_image_file.read()
        
        border_template_path = request.form.get('border_template_path')
        border_template_bytes = None
        
        if 'border_template' in request.files:
            border_template_file = request.files['border_template']
            border_template_bytes = border_template_file.read()
        
        position = request.form.get('position', 'center')
        
        # Composite
        compositor = get_image_compositor()
        result_bytes = compositor.composite_with_border(
            base_image_bytes,
            border_template_path=border_template_path,
            border_template_bytes=border_template_bytes,
            position=position
        )
        
        return send_file(
            io.BytesIO(result_bytes),
            mimetype='image/png',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error compositing image: {str(e)}")
        return jsonify({
            'error': 'Failed to composite image',
            'details': str(e)
        }), 500


@book_publishing.route('/generate-border-template', methods=['POST'])
def generate_border_template():
    """
    Generate a decorative border template using Stable Diffusion ControlNet.
    
    Request body (JSON):
    {
        "prompt": "ornate decorative border",
        "width": 1024,
        "height": 1024,
        "border_thickness": 80,
        "border_style": "rectangular",
        "template_name": "ornate_border_1",
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
        "seed": null
    }
    
    Returns:
        Image bytes (PNG) and template name
    """
    try:
        data = request.get_json()
        
        prompt = data.get('prompt', 'ornate decorative border frame, intricate patterns, elegant design')
        width = data.get('width', 1024)
        height = data.get('height', 1024)
        border_thickness = data.get('border_thickness', 80)
        border_style = data.get('border_style', 'rectangular')
        template_name = data.get('template_name')
        num_inference_steps = data.get('num_inference_steps', 30)
        guidance_scale = data.get('guidance_scale', 7.5)
        seed = data.get('seed')
        
        # Check if Stable Diffusion is available
        try:
            health_check = requests.get(f"{STABLE_DIFFUSION_URL}/health", timeout=15)
            if health_check.status_code != 200:
                raise requests.exceptions.RequestException("Stable Diffusion service not healthy")
            
            # Check the actual status in the response
            health_data = health_check.json()
            if health_data.get("status") != "healthy":
                raise requests.exceptions.RequestException(
                    f"Stable Diffusion service not ready: {health_data.get('status', 'unknown')}"
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"Stable Diffusion service not available: {str(e)}")
            return jsonify({
                'error': 'Stable Diffusion service is not running',
                'details': f'Please start the Stable Diffusion service on {STABLE_DIFFUSION_URL}'
            }), 503
        
        # Call Stable Diffusion border generation endpoint
        sd_request = {
            'prompt': prompt,
            'width': width,
            'height': height,
            'border_thickness': border_thickness,
            'border_style': border_style,
            'num_inference_steps': num_inference_steps,
            'guidance_scale': guidance_scale,
            'seed': seed
        }
        
        logger.info(f"Generating border template: {prompt[:50]}...")
        
        response = requests.post(
            f"{STABLE_DIFFUSION_URL}/api/generate-border",
            json=sd_request,
            timeout=600  # 10 minutes for SDXL generation
        )
        
        if response.status_code != 200:
            error_text = response.text[:500] if response.text else "Unknown error"
            return jsonify({
                'error': f'Stable Diffusion service error: {response.status_code}',
                'details': error_text
            }), response.status_code
        
        border_bytes = response.content
        
        # Save as template if name provided
        saved_path = None
        if template_name:
            try:
                compositor = get_image_compositor()
                saved_path = compositor.save_border_template(border_bytes, template_name)
                logger.info(f"Saved border template: {saved_path}")
            except Exception as e:
                logger.warning(f"Failed to save border template: {str(e)}")
                # Continue anyway, return the image
        
        # Return image as base64
        import base64
        image_base64 = base64.b64encode(border_bytes).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{image_base64}',
            'image_bytes': image_base64,
            'template_name': template_name,
            'saved_path': saved_path
        })
        
    except requests.exceptions.Timeout:
        logger.error("Stable Diffusion service timeout")
        return jsonify({
            'error': 'Generation timed out',
            'details': 'Border generation took too long. Please try again.'
        }), 504
    except Exception as e:
        logger.error(f"Error generating border template: {str(e)}")
        return jsonify({
            'error': 'Failed to generate border template',
            'details': str(e)
        }), 500


@book_publishing.route('/border-templates', methods=['GET'])
def list_border_templates():
    """
    List available border templates.
    
    Returns:
        List of template names
    """
    try:
        compositor = get_image_compositor()
        templates = compositor.list_border_templates()
        return jsonify({
            'templates': templates
        })
    except Exception as e:
        logger.error(f"Error listing border templates: {str(e)}")
        return jsonify({
            'error': 'Failed to list border templates',
            'details': str(e)
        }), 500

