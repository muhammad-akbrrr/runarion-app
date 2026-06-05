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
        Schema::create('author_styles', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->ulid('project_id');
            $table->foreignId('user_id')->constrained()->nullOnDelete();
            $table->text('author_name');
            $table->jsonb('techniques_json')->nullable()->comment('Structured techniques of the author style');
            $table->jsonb('examples_json')->nullable()->comment('Structured examples of the author style');
            $table->enum('status', ['init_completed', 'sampling_completed', 'sampling_failed', 'profiling_completed', 'profiling_failed']);
            $table->text('error_message')->nullable()->comment('Error message if failed');
            $table->timestamp('started_at');
            $table->integer('total_time_ms')->nullable();
            $table->timestamp('created_at')->useCurrent();
            $table->timestamp('updated_at')->nullable();

            $table->foreign('workspace_id')->references('id')->on('workspaces')->cascade();
            $table->foreign('project_id')->references('id')->on('projects')->cascade();

            $table->unique(['workspace_id', 'author_name'], 'unique_workspace_author_name');
        });

        Schema::create('author_samples', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->text('document_path')->comment('Path to the document file');
            $table->text('document_hash')->nullable()->comment('Hash of the document file');
            $table->text('text_content')->nullable()->comment('The whole text content of the document');
            $table->text('error_message')->nullable()->comment('Error message if failed');
            $table->timestamp('created_at')->useCurrent();

            $table->unique(['document_hash'], 'unique_document_hash');
        });

        Schema::create('author_styles_to_samples', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('author_style_id');
            $table->ulid('author_sample_id');
            $table->timestamp('created_at')->useCurrent();
            $table->softDeletes();

            $table->foreign('author_style_id')->references('id')->on('author_styles')->cascade();
            $table->foreign('author_sample_id')->references('id')->on('author_samples')->cascade();

            $table->unique(['author_style_id', 'author_sample_id'], 'unique_author_styles_sample');
        });

        Schema::create('author_style_chunks', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('author_style_id');
            $table->ulid('author_sample_id')->nullable();
            $table->integer('chunk_number')->nullable()->comment('Chunk number used in the style analysis');
            $table->integer('chunk_start_index')->nullable()->comment('Start index of the used chunk in the sample text');
            $table->integer('chunk_char_count')->nullable()->comment('Character count of the used chunk');
            $table->integer('chunk_token_count')->nullable()->comment('Token count of the used chunk');
            $table->jsonb('author_style_chunk_ids')->nullable()->comment('List of style IDs used in the style analysis');
            $table->text('style_text')->nullable()->comment('Resulting style text from the analysis');
            $table->integer('style_text_token_count')->nullable()->comment('Token count of the style text');
            $table->text('error_message')->nullable()->comment('Error message if failed');
            $table->integer('processing_time_ms');
            $table->timestamp('created_at')->useCurrent();
            $table->softDeletes();

            $table->foreign('author_style_id')->references('id')->on('author_styles')->cascade();
            $table->foreign('author_sample_id')->references('id')->on('author_samples')->cascade();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('author_styles');
        Schema::dropIfExists('author_samples');
        Schema::dropIfExists('author_style_chunks');
    }
};
