import json
import os
import traceback
from typing import Optional

from flask import Blueprint, current_app, jsonify, request
from models.request import CallerInfo
from psycopg2.pool import SimpleConnectionPool
from pydantic import BaseModel, ValidationError
from services.deconstructor import (
    AuthorStyleConfiguration,
    ParagraphExtractor,
)
from ulid import ULID
from werkzeug.utils import secure_filename


class CallerData(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str


class PageRangeItem(BaseModel):
    start_page: int = 1
    end_page: Optional[int] = None


class ConfigData(BaseModel):
    min_char_len: Optional[int] = None
    max_char_len: Optional[int] = None
    sentence_endings: Optional[list[str]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    generation_config: Optional[dict] = None
    paragraph_overlap: Optional[bool] = None
    store_intermediate: Optional[bool] = None


class AuthorStyleRequest(BaseModel):
    author_name: str
    caller: CallerData
    page_ranges: list[PageRangeItem]
    config: ConfigData = ConfigData()


author_style = Blueprint("author_style", __name__)


@author_style.route("/analyze-author-style", methods=["POST"])
def analyze_author_style():
    """
    Endpoint to analyze author style from uploaded PDF files.
    It validates the request, stores the files, and runs the analysis.
    It expects a multipart/form-data request with fields:
    - files: List of PDF files to analyze.
    - data: JSON string that follows the AuthorStyleRequest model
    """
    try:
        # Handle file upload first
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        # Get uploaded files
        pdf_files = request.files.getlist("files")
        if not pdf_files:
            return jsonify({"error": "No PDF files provided"}), 400

        # Get and validate request data
        request_data = request.form.to_dict()
        if not request_data.get("data"):
            return jsonify({"error": "No data provided"}), 400

        # Parse JSON data
        try:
            loaded_data = json.loads(request_data.get("data", "{}"))
            data = AuthorStyleRequest(**loaded_data)
        except (json.JSONDecodeError, ValidationError) as e:
            return jsonify({"error": f"Invalid request data: {str(e)}"}), 400
        if len(pdf_files) != len(data.page_ranges):
            return jsonify(
                {"error": "Number of PDF files must match number of page ranges"}
            ), 400

        # Check if author name already exists for this workspace
        connection_pool: Optional[SimpleConnectionPool] = current_app.config.get(
            "CONNECTION_POOL"
        )
        if not connection_pool:
            return jsonify({"error": "Database connection pool not configured"}), 500
        with connection_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM structured_author_styles WHERE author_name = %s AND workspace_id = %s)",
                    (
                        data.author_name,
                        data.caller.workspace_id,
                    ),
                )
                exists = cursor.fetchone()[0]
                if exists:
                    return jsonify(
                        {
                            "error": f"Author name '{data.author_name}' already exists for this workspace"
                        }
                    ), 400

        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(
            current_app.config["UPLOAD_PATH"], "pdf_files")
        os.makedirs(upload_dir, exist_ok=True)

        # Save uploaded files and create paragraph extractors
        paragraph_extractors = []
        for i, pdf_file in enumerate(
            pdf_files
        ):  # Secure the filename and save the file
            if pdf_file.filename:
                filename = secure_filename(pdf_file.filename)
            else:
                filename = "unnamed.pdf"
            unique_filename = f"{ULID()}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            pdf_file.save(file_path)
            page_range = data.page_ranges[i]

            extractor = ParagraphExtractor(
                file_path=file_path,
                start_page=page_range.start_page,
                end_page=page_range.end_page,
                min_char_len=data.config.min_char_len,
                max_char_len=data.config.max_char_len,
                sentence_endings=data.config.sentence_endings,
            )
            paragraph_extractors.append(extractor)

        # Create caller info for the service
        caller = CallerInfo(
            user_id=data.caller.user_id,
            workspace_id=data.caller.workspace_id,
            project_id=data.caller.project_id,
            api_keys={},  # NEED TO IMPLEMENT
        )

        # Create author style configuration
        author_style_config = AuthorStyleConfiguration(
            paragraph_extractors=paragraph_extractors,
            caller=caller,
            connection_pool=connection_pool,
            author_name=data.author_name,
            provider=data.config.provider,
            model=data.config.model,
            generation_config=data.config.generation_config,
            paragraph_overlap=data.config.paragraph_overlap,
            store_intermediate=data.config.store_intermediate,
        )

        # Run the author style analysis
        result = author_style_config.run()

        # Return the result
        return jsonify(result.model_dump()), 200

    except Exception as e:
        current_app.logger.error(f"Error in analyze_author_style: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
