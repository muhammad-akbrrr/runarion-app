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
      $table->boolean('is_active')->default(true);
      $table->timestamps();
      $table->softDeletes();

      $table->unique(['workspace_id', 'slug']);
      $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
    });
  }

  public function down(): void
  {
    Schema::dropIfExists('folders');
  }
};