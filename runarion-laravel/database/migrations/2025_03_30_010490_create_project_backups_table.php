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
    Schema::create('project_backups', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->foreignUlid('project_id')->constrained('projects')->cascadeOnDelete();
      $table->foreignUlid('workspace_id')->constrained('workspaces')->cascadeOnDelete();
      $table->timestamp('date');
      $table->enum('frequency', ['daily', 'weekly', 'manual']);
      $table->enum('backup_type', ['automatic', 'manual', 'pre-restore']);
      $table->bigInteger('size');
      $table->string('checksum');
      $table->enum('status', ['pending', 'completed', 'failed']);
      $table->text('error_details')->nullable();
      $table->string('storage_path');
      $table->json('storage_metadata')->nullable();
      $table->string('version')->nullable();
      $table->timestamps();
      $table->softDeletes();
    });
  }

  /**
   * Reverse the migrations.
   */
  public function down(): void
  {
    Schema::dropIfExists('project_backups');
  }
};