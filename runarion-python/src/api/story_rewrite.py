import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pydantic import ValidationError
from models.deconstructor.story_rewrite import (
    StoryRewriteRequest,
    NewAuthorStyleRequest,
    ExistingAuthorStyleRequest,
    WritingPerspective
)
from models.request import CallerInfo, GenerationConfig
from services.deconstructor.story_rewrite_pipeline import StoryRewritePipeline
from psycopg2.pool import SimpleConnectionPool
from ulid import ULID
import logging

story_rewrite = Blueprint("story_rewrite", __name__)

# Configure file upload settings
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)


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
            logging.error("Database connection not available")
            return jsonify({"error": "Database connection not available"}), 500

        # Extract form data
        form_data = request.form.to_dict()
        logging.info(f"Received form data: {form_data}")

        # Get deconstructor_log id from form_data (must be provided by Laravel)
        request_id = form_data.get('id')
        if not request_id:
            logging.error("request_id is required")
            return jsonify({"error": "request_id is required"}), 400

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
            logging.error("Rough draft PDF file is required")
            return jsonify({"error": "Rough draft PDF file is required"}), 400

        rough_draft_file = request.files['rough_draft']
        if rough_draft_file.filename == '':
            logging.error("No rough draft file selected")
            return jsonify({"error": "No rough draft file selected"}), 400

        rough_draft_path = save_uploaded_file(rough_draft_file, "rough_draft")
        logging.info(f"Rough draft file saved at: {rough_draft_path}")
        if not rough_draft_path:
            logging.error(
                "Invalid rough draft file format. Only PDF files are allowed")
            return jsonify({"error": "Invalid rough draft file format. Only PDF files are allowed"}), 400

        # Step 2: Handle author style selection
        author_style_type = form_data.get('author_style_type')
        logging.info(f"Author style type: {author_style_type}")
        if not author_style_type:
            logging.error(
                "author_style_type is required ('new' or 'existing')")
            return jsonify({"error": "author_style_type is required ('new' or 'existing')"}), 400

        if author_style_type == 'new':
            # Handle new author style creation
            if 'author_samples' not in request.files:
                logging.error(
                    "Author sample files are required for new author style")
                return jsonify({"error": "Author sample files are required for new author style"}), 400

            author_samples = request.files.getlist('author_samples')
            if not author_samples or all(f.filename == '' for f in author_samples):
                logging.error("At least one author sample file is required")
                return jsonify({"error": "At least one author sample file is required"}), 400

            # Save author sample files
            sample_paths = []
            for sample in author_samples:
                if sample.filename != '':
                    sample_path = save_uploaded_file(sample, "author_sample")
                    if sample_path:
                        sample_paths.append(sample_path)
                        logging.info(
                            f"Author sample file saved at: {sample_path}")

            if not sample_paths:
                logging.error("No valid author sample files uploaded")
                return jsonify({"error": "No valid author sample files uploaded"}), 400

            author_style_request = NewAuthorStyleRequest(
                sample_files=sample_paths,
                author_name=form_data.get('author_name', '')
            )
            logging.info(f"NewAuthorStyleRequest: {author_style_request}")

        elif author_style_type == 'existing':
            # Handle existing author style selection
            author_style_id = form_data.get('author_style_id')
            if not author_style_id:
                logging.error(
                    "author_style_id is required for existing author style")
                return jsonify({"error": "author_style_id is required for existing author style"}), 400

            author_style_request = ExistingAuthorStyleRequest(
                author_style_id=author_style_id
            )
            logging.info(f"ExistingAuthorStyleRequest: {author_style_request}")

        else:
            logging.error(
                "Invalid author_style_type. Must be 'new' or 'existing'")
            return jsonify({"error": "Invalid author_style_type. Must be 'new' or 'existing'"}), 400

        # Step 3: Handle writing perspective
        perspective_type = form_data.get('writing_perspective_type')
        if not perspective_type:
            logging.error("writing_perspective_type is required")
            return jsonify({"error": "writing_perspective_type is required"}), 400

        writing_perspective = WritingPerspective(
            type=perspective_type,
            narrator_voice=form_data.get('narrator_voice', ''),
            character_focus=form_data.get('character_focus', '')
        )
        logging.info(f"WritingPerspective: {writing_perspective}")

        # Step 4: Create the story rewrite request
        story_request = StoryRewriteRequest(
            rough_draft_file=rough_draft_path,
            author_style_request=author_style_request,
            writing_perspective=writing_perspective,
            rewrite_config=None,  # Will be created by pipeline
            store_intermediate=form_data.get(
                'store_intermediate', 'false').lower() == 'true',
            chunk_overlap=form_data.get(
                'chunk_overlap', 'false').lower() == 'true'
        )
        logging.info(f"StoryRewriteRequest: {story_request}")

        # Create and run the pipeline
        pipeline = StoryRewritePipeline(
            caller=caller,
            connection_pool=connection_pool,
            provider=form_data.get('provider', 'gemini'),
            model=form_data.get('model', 'gemini-2.0-flash'),
            request_id=request_id,  # Pass the request_id down
        )
        logging.info(f"StoryRewritePipeline created: {pipeline}")

        # Process the request
        response = pipeline.process_request(story_request)
        logging.info(f"Pipeline response: {response}")

        # Clean up uploaded files
        try:
            os.remove(rough_draft_path)
            if author_style_type == 'new':
                for sample_path in sample_paths:
                    os.remove(sample_path)
        except Exception as e:
            logging.warning(f"Failed to clean up uploaded files: {e}")

        # Return the response
        return jsonify({
            "success": True,
            "session_id": response["session_id"],
            "author_style_id": response["author_style_id"],
            "original_story": response["original_story"],
            "rewritten_story": response["rewritten_story"],
            "metadata": {
                "total_chunks": response["total_chunks"],
                "total_original_chars": response["total_original_chars"],
                "total_rewritten_chars": response["total_rewritten_chars"],
                "total_tokens": response["total_tokens"],
                "processing_time_ms": response["processing_time_ms"],
                "average_style_confidence": response["average_style_confidence"],
            }
        }), 200

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        current_app.logger.error(f"Validation error: {e}")
        return jsonify({"error": "Invalid request data", "details": str(e)}), 400

    except Exception as e:
        logging.error(f"Story rewrite error: {type(e).__name__} - {e}")
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
