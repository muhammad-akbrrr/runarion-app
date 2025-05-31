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
    Schema::create('workspace_members', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->ulid('workspace_id');
      $table->foreignId('user_id')->constrained()->onDelete('cascade');
      $table->enum('role', ['owner', 'admin', 'member'])->default('member');
      $table->timestamps();

      $table->unique(['workspace_id', 'user_id']);
      $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
    });
  }

  /**
   * Reverse the migrations.
   */
  public function down(): void
  {
    Schema::dropIfExists('workspace_members');
  }
};