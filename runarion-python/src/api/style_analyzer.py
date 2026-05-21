import json
import os
from typing import Literal, Optional

from flask import Blueprint, current_app, jsonify, request
from src.models.request import CallerInfo
from psycopg2.pool import SimpleConnectionPool
from pydantic import BaseModel, Field, ValidationError
from src.services.style_analyzer import (
    ProfilingStage,
    SamplingStage,
    StyleAnalyzerOrchestrator,
)
from ulid import ULID
from werkzeug.utils import secure_filename


class CallerData(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str


class ConfigData(BaseModel):
    min_success_samples: Optional[int | float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    max_output_tokens: Optional[int] = None
    min_success_partial_style: Optional[int | float] = None


class AuthorStyleRequest(BaseModel):
    caller: CallerData
    author_name: str
    on_exist: Literal["update", "get", "error"] = "error"
    config: ConfigData = ConfigData()
    generation_config: dict = Field(default_factory=dict)


analyze_style = Blueprint("analyze_style", __name__)


@analyze_style.route("/analyze-style", methods=["POST"])
def analyze_author_style():
    """
    Endpoint to analyze author style from uploaded PDF files.
    It validates the request, stores the files, and runs the analysis.
    It expects a multipart/form-data request with fields:
    - files: List of author sample files to analyze.
    - data: JSON string that follows the AuthorStyleRequest model
    """
    try:
        # Check database connection pool
        db_pool: Optional[SimpleConnectionPool] = current_app.config.get(
            "CONNECTION_POOL"
        )
        if not db_pool:
            return jsonify({"error": "Database connection pool not configured"}), 500

        # Handle file upload first
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        # Get uploaded files
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files provided"}), 400

        # Get and validate request data
        request_data = request.form.to_dict()
        if not request_data.get("data"):
            return jsonify({"error": "No data provided"}), 400

        # Parse JSON data
        try:
            loaded_data = json.loads(request_data["data"])
            data = AuthorStyleRequest(**loaded_data)
        except (json.JSONDecodeError, ValidationError) as e:
            return jsonify({"error": f"Invalid request data: {str(e)}"}), 400

        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.config["UPLOAD_PATH"], "author_samples")
        os.makedirs(upload_dir, exist_ok=True)

        # Secure filenames and save files
        file_paths = []
        for i, file in enumerate(files):
            if file.filename:
                filename = secure_filename(file.filename)
            else:
                filename = "unnamed.pdf"
            unique_filename = f"{ULID()}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            file_paths.append(file_path)

        # Create caller info for the service
        caller = CallerInfo(
            user_id=data.caller.user_id,
            workspace_id=data.caller.workspace_id,
            project_id=data.caller.project_id,
            api_keys={},
        )

        # Initialize the style analyzer orchestrator
        orchestrator = StyleAnalyzerOrchestrator(
            db_pool,
            SamplingStage(
                db_pool=db_pool,
                min_success_samples=data.config.min_success_samples,
            ),
            ProfilingStage(
                db_pool=db_pool,
                provider=data.config.provider,
                model=data.config.model,
                max_output_tokens=data.config.max_output_tokens,
                generation_config=data.generation_config,
                min_success_partial_style=data.config.min_success_partial_style,
            ),
        )

        # Run check and clean up if needed
        try:
            author_style_id, author_style = orchestrator.check_and_clean(
                author_name=data.author_name,
                caller=caller,
                on_exist=data.on_exist,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Return existing author style if on_exist is 'get'
        if data.on_exist == "get" and author_style:
            return jsonify({"author_style": author_style.model_dump()}), 200

        # Run the author style analysis
        result = orchestrator.run_pipeline(
            author_style_id=author_style_id,
            author_name=data.author_name,
            file_paths=file_paths,
            caller=caller,
        )

        if result["status"] == "profiling_completed":
            return jsonify({"author_style": result["author_style"].model_dump()}), 200
        else:
            return jsonify(
                {
                    "error": result["error_message"],
                    "status": result["status"],
                }
            ), 500

    except Exception as e:
        current_app.logger.error(
            f"Error in analyze_author_style: {str(e)}", exc_info=True
        )
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
