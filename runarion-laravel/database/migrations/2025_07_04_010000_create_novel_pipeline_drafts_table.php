<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('drafts', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->bigInteger('user_id')->unsigned();
            $table->string('original_filename');
            $table->string('file_path');
            $table->bigInteger('file_size');
            $table->integer('word_count')->nullable(); // Track word count for processing
            $table->enum('status', [
                'pending',
                'processing', 
                'stage_1_complete',
                'stage_2_complete',
                'stage_3_complete',
                'stage_4_complete',
                'stage_5_complete',
                'stage_6_complete',
                'completed',
                'failed'
            ])->default('pending');
            $table->timestamp('processing_started_at')->nullable();
            $table->timestamp('processing_completed_at')->nullable();
            $table->string('error_message')->nullable();
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
            $table->foreign('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->index(['workspace_id', 'status']);
            $table->index(['user_id', 'workspace_id']);
        });

        Schema::create('draft_chunks', function (Blueprint $table) {
            $table->id();
            $table->ulid('draft_id');
            $table->integer('chunk_number');
            $table->longText('raw_text');
            $table->longText('cleaned_text');
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->index(['draft_id', 'chunk_number']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('draft_chunks');
        Schema::dropIfExists('drafts');
    }
};