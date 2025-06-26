<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
  public function up()
  {
    Schema::create('deconstructor_logs', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->unsignedBigInteger('user_id')->nullable();
      $table->ulid('workspace_id')->nullable();
      $table->ulid('project_id')->nullable();
      $table->ulid('author_style_id')->nullable();
      $table->string('rough_draft_path')->nullable();
      $table->json('author_style_info')->nullable();
      $table->json('writing_perspective')->nullable();
      $table->json('caller_info')->nullable();
      $table->timestamp('requested_at')->nullable();
      $table->timestamp('completed_at')->nullable();
      $table->integer('duration_ms')->nullable();
      $table->json('response_metadata')->nullable();
      $table->string('status')->default('pending');
      $table->text('error_message')->nullable();
      $table->timestamps();

      $table->foreign('user_id')->references('id')->on('users')->nullOnDelete();
      $table->foreign('workspace_id')->references('id')->on('workspaces')->nullOnDelete();
      $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();
      $table->foreign('author_style_id')->references('id')->on('structured_author_styles')->nullOnDelete();

      $table->index(['status', 'requested_at']);
      $table->index(['user_id', 'status']);
      $table->index(['project_id', 'status']);
      $table->index('completed_at');
    });

    Schema::create('deconstructor_responses', function (Blueprint $table) {
      $table->id();
      $table->ulid('request_id');
      $table->ulid('session_id')->nullable();
      $table->ulid('author_style_id')->nullable();
      $table->ulid('project_id')->nullable();
      $table->longText('original_story')->nullable();
      $table->longText('rewritten_story')->nullable();
      $table->json('metadata')->nullable();
      $table->timestamps();

      $table->foreign('request_id')->references('id')->on('deconstructor_logs')->onDelete('cascade');
      $table->foreign('author_style_id')->references('id')->on('structured_author_styles')->nullOnDelete();
      $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();

      $table->unique('request_id');
      $table->index(['session_id', 'project_id']);
    });

    Schema::create('intermediate_deconstructor', function (Blueprint $table) {
      $table->id();
      $table->ulid('request_id');
      $table->ulid('project_id');
      $table->ulid('session_id')->nullable();
      $table->longText('original_story')->nullable();
      $table->longText('rewritten_story')->nullable();
      $table->jsonb('applied_style')->nullable();
      $table->jsonb('applied_perspective')->nullable();
      $table->integer('duration_ms')->nullable();
      $table->integer('token_count')->nullable();
      $table->decimal('style_intensity', 3, 2)->nullable();
      $table->longText('original_content')->nullable();
      $table->integer('chunk_num')->nullable();
      $table->timestamps();

      $table->foreign('request_id')->references('id')->on('deconstructor_logs')->onDelete('cascade');
      $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();

      $table->index(['request_id', 'chunk_num']);
      $table->index(['session_id', 'project_id']);
      $table->index('chunk_num');
    });

    Schema::create('deconstructor_sessions', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->unsignedBigInteger('user_id')->nullable();
      $table->ulid('workspace_id')->nullable();
      $table->ulid('project_id')->nullable();
      $table->json('author_style')->nullable();
      $table->json('writing_perspective')->nullable();
      $table->json('rewrite_config')->nullable();
      $table->integer('total_rewrites')->nullable();
      $table->timestamp('started_at')->nullable();
      $table->integer('total_time_ms')->nullable();
      $table->longText('original_content')->nullable();
      $table->timestamps();

      $table->foreign('user_id')->references('id')->on('users')->nullOnDelete();
      $table->foreign('workspace_id')->references('id')->on('workspaces')->nullOnDelete();
      $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();

      $table->index(['user_id', 'project_id']);
      $table->index('started_at');
    });
  }

  public function down()
  {
    Schema::dropIfExists('deconstructor_sessions');
    Schema::dropIfExists('intermediate_deconstructor');
    Schema::dropIfExists('deconstructor_responses');
    Schema::dropIfExists('deconstructor_logs');
  }
};