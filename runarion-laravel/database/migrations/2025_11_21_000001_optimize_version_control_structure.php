<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Create dedicated version control tables for better performance
        Schema::create('content_nodes', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('project_id');
            $table->integer('chapter_order');
            $table->ulid('parent_node_id')->nullable();
            $table->integer('parent_version_index')->nullable();
            $table->longText('content');
            $table->json('generation_settings')->nullable();
            $table->boolean('is_user_generated')->default(true);
            $table->timestamp('created_at');
            $table->index(['project_id', 'chapter_order']);
            $table->index(['parent_node_id']);
        });

        Schema::create('content_versions', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('node_id');
            $table->integer('version_index');
            $table->longText('content');
            $table->timestamp('created_at');
            $table->unique(['node_id', 'version_index']);
        });

        Schema::create('chapter_states', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('project_id');
            $table->integer('chapter_order');
            $table->ulid('current_node_id');
            $table->integer('current_version_index')->default(0);
            $table->timestamp('updated_at');
            $table->unique(['project_id', 'chapter_order']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chapter_states');
        Schema::dropIfExists('content_versions');
        Schema::dropIfExists('content_nodes');
    }
};
