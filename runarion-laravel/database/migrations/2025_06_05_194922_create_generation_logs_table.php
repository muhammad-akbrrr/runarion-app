<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('generation_logs', function (Blueprint $table) {
            // Primary key: request_id is a UUID passed externally
            $table->uuid('request_id')->primary();

            // Optional provider request ID for tracing
            $table->string('provider_request_id')->nullable();

            // Foreign key columns
            $table->foreignId('user_id')->constrained()->onDelete('cascade');
            $table->ulid('workspace_id')->nullable();
            $table->ulid('project_id')->nullable();

            // Provider details
            $table->string('provider')->nullable();
            $table->string('model_used')->nullable();
            $table->string('key_used')->nullable();

            // Prompt and generation
            $table->text('prompt')->nullable();
            $table->text('instruction')->nullable();
            $table->longText('generated_text')->nullable();

            // Status and output
            $table->boolean('success')->default(false);
            $table->string('finish_reason')->nullable();
            $table->integer('input_tokens')->nullable();
            $table->integer('output_tokens')->nullable();
            $table->integer('total_tokens')->nullable();
            $table->integer('processing_time_ms')->nullable();

            // Error info
            $table->text('error_message')->nullable();

            // Timestamps
            $table->timestamp('created_at')->useCurrent();

            // Foreign key constraints
            $table->foreign('workspace_id')->references('id')->on('workspaces')->nullOnDelete();
            $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('generation_logs');
    }
};
