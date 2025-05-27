<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
  public function up(): void
  {
    Schema::create('folders', function (Blueprint $table) {
      $table->id();
      $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
      $table->string('name');
      $table->string('slug');
      $table->boolean('is_active')->default(true);
      $table->timestamps();
      $table->softDeletes();

      $table->unique(['workspace_id', 'slug']);
    });
  }

  public function down(): void
  {
    Schema::dropIfExists('folders');
  }
};