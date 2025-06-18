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
    Schema::create('project_logs', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->timestamp('date');
      $table->foreignId('user_id')->constrained('users')->cascadeOnDelete();
      $table->string('event');
      $table->foreignUlid('project_id')->constrained('projects')->cascadeOnDelete();
      $table->foreignUlid('workspace_id')->constrained('workspaces')->cascadeOnDelete();
      $table->json('metadata')->nullable();
      $table->string('ip_address')->nullable();
      $table->string('user_agent')->nullable();
      $table->enum('severity', ['info', 'warning', 'error', 'critical']);
      $table->json('related_entity_id')->nullable();
      $table->json('related_entity_type')->nullable();
      $table->json('changes')->nullable();
      $table->timestamps();
      $table->softDeletes();
    });
  }

  /**
   * Reverse the migrations.
   */
  public function down(): void
  {
    Schema::dropIfExists('project_logs');
  }
};