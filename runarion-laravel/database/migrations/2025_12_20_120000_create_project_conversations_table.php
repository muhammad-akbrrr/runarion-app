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
        Schema::create('project_conversations', function (Blueprint $table) {
            $table->ulid('project_id')->primary();

            // JSONB array storing conversation history messages
            // Message structure:
            // {
            //   "role": "user" | "assistant",
            //   "content": "text content",
            //   "chapter_id": 1,
            //   "chapter_order": 1,
            //   "timestamp": "ISO string",
            //   "message_index": 0
            // }
            $table->jsonb('messages')->default('[]')->comment('Array of conversation messages stored chronologically');

            $table->timestamps();

            // Foreign key to projects table with cascade delete
            $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('project_conversations');
    }
};
