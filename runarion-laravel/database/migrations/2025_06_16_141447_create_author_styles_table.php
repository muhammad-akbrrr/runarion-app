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
        Schema::create('intermediate_author_styles', function (Blueprint $table) {
            // Primary key: id is a ULID
            $table->ulid('id')->primary();

            // Reference to structured_author_styles
            $table->ulid('structured_style_id');

            // Intermediate author style
            $table->text('style');

            // Passages used in the style analysis: {source_file: [list of passage numbers]}
            $table->json('passages');

            // Processing time in milliseconds
            $table->integer('processing_time_ms');
            
            // Created at and updated at timestamps
            $table->timestamps();
        });

        Schema::create('structured_author_styles', function (Blueprint $table) {
            // Primary key: id is a ULID
            $table->ulid('id')->primary();

            // Foreign keys
            $table->ulid('workspace_id');
            $table->ulid('project_id');
            $table->foreignId('user_id')->constrained()->nullOnDelete();
            
            // Author name as identifier
            $table->text('author_name');

            // Final structured author style
            $table->json('style');

            // Comma-separated list of source files used in the style analysis
            $table->text('sources');

            // Start time and total processing time
            $table->timestamp('started_at');
            $table->integer('total_time_ms');

            // Created at and updated at timestamps
            $table->timestamps();

            // Foreign key constraints
            $table->foreign('workspace_id')->references('id')->on('workspaces')->cascade();
            $table->foreign('project_id')->references('id')->on('projects')->cascade();

            // Unique index for author name in the context of workspace
            $table->unique(['workspace_id', 'author_name'], 'unique_workspace_author_name');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('intermediate_author_styles');
        Schema::dropIfExists('structured_author_styles');
    }
};
