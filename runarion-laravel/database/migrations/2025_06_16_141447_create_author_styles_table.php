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
        Schema::create('intermediate_author_styles', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('structured_style_id');
            $table->text('style')->comment('Intermediate author style');
            $table->json('passages')->comment('Passages used in the style analysis: {source_file: [list of passage numbers]}');
            $table->integer('processing_time_ms');
            $table->timestamps();
        });

        Schema::create('structured_author_styles', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->ulid('project_id');
            $table->foreignId('user_id')->constrained()->nullOnDelete();
            $table->text('author_name');
            $table->json('style')->comment('Structured author style');
            $table->text('sources')->comment('Comma-separated list of source files used in the style analysis');
            $table->timestamp('started_at');
            $table->integer('total_time_ms');
            $table->timestamps();

            $table->foreign('workspace_id')->references('id')->on('workspaces')->cascade();
            $table->foreign('project_id')->references('id')->on('projects')->cascade();

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
