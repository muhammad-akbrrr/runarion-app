import os
import tempfile
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pydantic import ValidationError
from models.deconstructor.story_rewrite_request import (
    StoryRewriteRequest,
    NewAuthorStyleRequest,
    ExistingAuthorStyleRequest
)
from models.request import CallerInfo, GenerationConfig
from services.deconstructor.story_rewrite_pipeline import StoryRewritePipeline
from psycopg2.pool import SimpleConnectionPool

story_rewrite = Blueprint("story_rewrite", __name__)

# Configure file upload settings
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'runarion_uploads')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, prefix="file"):
    """Save uploaded file and return the file path."""
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{prefix}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return filepath
    return None


@story_rewrite.route("/story-rewrite", methods=["POST"])
def story_rewrite_route():
    """
    API endpoint for story rewriting workflow:
    1. User uploads rough draft PDF
    2. User selects or creates author style
    3. User selects writing perspective
    4. System rewrites the story
    """
    try:
        # Get the connection pool from app context
        connection_pool = current_app.config.get('connection_pool')
        if not connection_pool:
            return jsonify({"error": "Database connection not available"}), 500

        # Extract form data
        form_data = request.form.to_dict()

        # Extract caller information
        caller = CallerInfo(
            user_id=form_data.get('user_id', 'default_user'),
            workspace_id=form_data.get('workspace_id', 'default_workspace'),
            project_id=form_data.get('project_id', 'default_project'),
            api_keys={
                'openai': os.getenv('OPENAI_API_KEY'),
                'gemini': os.getenv('GEMINI_API_KEY'),
            }
        )

        # Step 1: Handle rough draft file upload
        if 'rough_draft' not in request.files:
            return jsonify({"error": "Rough draft PDF file is required"}), 400

        rough_draft_file = request.files['rough_draft']
        if rough_draft_file.filename == '':
            return jsonify({"error": "No rough draft file selected"}), 400

        rough_draft_path = save_uploaded_file(rough_draft_file, "rough_draft")
        if not rough_draft_path:
            return jsonify({"error": "Invalid rough draft file format. Only PDF files are allowed"}), 400

        # Step 2: Handle author style selection
        author_style_type = form_data.get('author_style_type')
        if not author_style_type:
            return jsonify({"error": "author_style_type is required ('new' or 'existing')"}), 400

        if author_style_type == 'new':
            # Handle new author style creation
            if 'author_samples' not in request.files:
                return jsonify({"error": "Author sample files are required for new author style"}), 400

            author_samples = request.files.getlist('author_samples')
            if not author_samples or all(f.filename == '' for f in author_samples):
                return jsonify({"error": "At least one author sample file is required"}), 400

            # Save author sample files
            sample_paths = []
            for sample in author_samples:
                if sample.filename != '':
                    sample_path = save_uploaded_file(sample, "author_sample")
                    if sample_path:
                        sample_paths.append(sample_path)

            if not sample_paths:
                return jsonify({"error": "No valid author sample files uploaded"}), 400

            author_style_request = NewAuthorStyleRequest(
                sample_files=sample_paths,
                author_name=form_data.get('author_name', '')
            )

        elif author_style_type == 'existing':
            # Handle existing author style selection
            author_style_id = form_data.get('author_style_id')
            if not author_style_id:
                return jsonify({"error": "author_style_id is required for existing author style"}), 400

            author_style_request = ExistingAuthorStyleRequest(
                author_style_id=author_style_id
            )

        else:
            return jsonify({"error": "Invalid author_style_type. Must be 'new' or 'existing'"}), 400

        # Step 3: Handle writing perspective
        perspective_type = form_data.get('writing_perspective_type')
        if not perspective_type:
            return jsonify({"error": "writing_perspective_type is required"}), 400

        from models.deconstructor.content_rewrite import WritingPerspective
        writing_perspective = WritingPerspective(
            type=perspective_type,
            narrator_voice=form_data.get('narrator_voice', ''),
            character_focus=form_data.get('character_focus', '')
        )

        # Step 4: Optional configuration
        rewrite_config = None
        if form_data.get('target_genre') or form_data.get('target_tone'):
            from models.deconstructor.content_rewrite import ContentRewriteConfig
            rewrite_config = ContentRewriteConfig(
                target_genre=form_data.get('target_genre', ''),
                target_tone=form_data.get('target_tone', ''),
                preserve_key_elements=form_data.get('preserve_elements', '').split(
                    ',') if form_data.get('preserve_elements') else [],
                target_length=form_data.get('target_length', 'similar'),
                style_intensity=float(form_data.get('style_intensity', 0.7))
            )

        # Create the story rewrite request
        story_request = StoryRewriteRequest(
            rough_draft_file=rough_draft_path,
            author_style_request=author_style_request,
            writing_perspective=writing_perspective,
            rewrite_config=rewrite_config,
            store_intermediate=form_data.get(
                'store_intermediate', 'false').lower() == 'true',
            chunk_overlap=form_data.get(
                'chunk_overlap', 'false').lower() == 'true'
        )

        # Create and run the pipeline
        pipeline = StoryRewritePipeline(
            caller=caller,
            connection_pool=connection_pool,
            provider=form_data.get('provider', 'gemini'),
            model=form_data.get('model', 'gemini-2.5-flash'),
        )

        # Process the request
        response = pipeline.process_request(story_request)

        # Clean up uploaded files
        try:
            os.remove(rough_draft_path)
            if author_style_type == 'new':
                for sample_path in sample_paths:
                    os.remove(sample_path)
        except Exception as e:
            current_app.logger.warning(
                f"Failed to clean up uploaded files: {e}")

        # Return the response
        return jsonify({
            "success": True,
            "session_id": response.session_id,
            "author_style_id": response.author_style_id,
            "original_story": response.original_story,
            "rewritten_story": response.rewritten_story,
            "metadata": {
                "total_chunks": response.total_chunks,
                "total_original_chars": response.total_original_chars,
                "total_rewritten_chars": response.total_rewritten_chars,
                "total_tokens": response.total_tokens,
                "processing_time_ms": response.processing_time_ms,
                "average_style_confidence": response.average_style_confidence,
            }
        }), 200

    except ValidationError as e:
        current_app.logger.error(f"Validation error: {e}")
        return jsonify({"error": "Invalid request data", "details": str(e)}), 400

    except Exception as e:
        current_app.logger.error(
            f"Story rewrite error: {type(e).__name__} - {e}")
        return jsonify({"error": "Failed to process story rewrite request", "message": str(e)}), 500


@story_rewrite.route("/story-rewrite/health", methods=["GET"])
def story_rewrite_health():
    """Health check for story rewrite service."""
    return jsonify({
        "status": "healthy",
        "service": "story-rewrite",
        "upload_folder": UPLOAD_FOLDER,
        "max_file_size": MAX_CONTENT_LENGTH
    }), 200
