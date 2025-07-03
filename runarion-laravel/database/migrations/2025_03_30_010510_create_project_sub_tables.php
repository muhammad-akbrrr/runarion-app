<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
  /**
   * Run the migrations.
   */
  public function up(): void
  {
    // Project Content Table
    Schema::create('project_content', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->ulid('project_id')->unique();
      $table->unsignedBigInteger('last_edited_by')->nullable();
      $table->json('content')->comment('Array of chapters with order (int), chapter_name (string), and content (string)');
      $table->json('metadata')->nullable()->comment('Additional metadata like word count, etc');
      $table->timestamp('last_edited_at')->nullable();
      $table->timestamps();
      $table->softDeletes();

      $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
      $table->foreign('last_edited_by')->references('id')->on('users')->onDelete('set null');
    });

    // Project Node Editor Table
    Schema::create('project_node_editor', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->ulid('project_id')->unique();
      $table->timestamps();
      $table->softDeletes();

      $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
    });
  }

  /**
   * Reverse the migrations.
   */
  public function down(): void
  {
    Schema::dropIfExists('project_node_editor');
    Schema::dropIfExists('project_content');
  }
};