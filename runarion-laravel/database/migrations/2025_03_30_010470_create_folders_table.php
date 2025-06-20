<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
  public function up(): void
  {
    Schema::create('folders', function (Blueprint $table) {
      $table->ulid('id')->primary();
      $table->ulid('workspace_id');
      $table->string('name');
      $table->string('slug');
      $table->unsignedBigInteger('original_author')->nullable();
      $table->boolean('is_active')->default(true);
      $table->timestamps();
      $table->softDeletes();

      $table->unique(['workspace_id', 'slug', 'is_active']);
      $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
      $table->foreign('original_author')->references('id')->on('users')->onDelete('set null');
    });
  }

  public function down(): void
  {
    Schema::dropIfExists('folders');
  }
};