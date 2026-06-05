<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('record_relationship_types', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('project_id')->nullable()->comment('NULL = system type, otherwise project-specific custom type');
            $table->string('name')->comment('Display name: "Allied With", "Rival Of", etc.');
            $table->string('edge_label')->comment('Apache AGE edge label: "ALLIED_WITH", "RIVAL_OF", etc.');
            $table->boolean('is_system')->default(false)->comment('System types (INTERACTS_WITH, KNOWS, etc.) vs custom');
            $table->timestamps();
            $table->softDeletes();

            // Foreign key to projects (nullable for system types)
            $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');

            // Unique constraint: project_id + name must be unique
            $table->unique(['project_id', 'name']);

            // Index for faster lookups
            $table->index(['project_id', 'is_system']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('record_relationship_types');
    }
};
