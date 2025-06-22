<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
  public function up()
  {
    Schema::create('deconstructor_logs', function (Blueprint $table) {
      $table->id();
      $table->string('request_id')->unique();
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
    });

    Schema::create('deconstructor_responses', function (Blueprint $table) {
      $table->id();
      $table->string('request_id')->unique();
      $table->string('session_id')->nullable();
      $table->ulid('author_style_id')->nullable();
      $table->ulid('project_id')->nullable();
      $table->longText('original_story')->nullable();
      $table->longText('rewritten_story')->nullable();
      $table->json('metadata')->nullable();
      $table->timestamps();

      $table->foreign('request_id')->references('request_id')->on('deconstructor_logs')->onDelete('cascade');
      $table->foreign('author_style_id')->references('id')->on('structured_author_styles')->nullOnDelete();
      $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();
    });
  }

  public function down()
  {
    Schema::dropIfExists('deconstructor_responses');
    Schema::dropIfExists('deconstructor_logs');
  }
};