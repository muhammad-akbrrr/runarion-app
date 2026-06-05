<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     *
     * Creates tables for the Advisor feature - a Cursor-style AI chat assistant
     * that has full story context and can suggest inline edits.
     */
    public function up(): void
    {
        // Advisor chats - each project can have multiple conversations
        Schema::create('advisor_chats', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('project_id');
            $table->string('title')->default('New Chat');
            $table->text('system_instructions')->nullable();
            $table->string('model')->default('gemini-2.5-flash');
            $table->timestamps();

            $table->foreign('project_id')
                ->references('id')
                ->on('projects')
                ->onDelete('cascade');

            // Index for listing recent chats by project
            $table->index(['project_id', 'updated_at']);
        });

        // Advisor messages - conversation history for each chat
        Schema::create('advisor_messages', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('chat_id');
            $table->enum('role', ['user', 'assistant', 'system']);
            $table->text('content');
            $table->jsonb('metadata')->nullable(); // For pending_edits, token_count, chapter references, etc.
            $table->timestamps();

            $table->foreign('chat_id')
                ->references('id')
                ->on('advisor_chats')
                ->onDelete('cascade');

            // Index for fetching messages in order
            $table->index(['chat_id', 'created_at']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('advisor_messages');
        Schema::dropIfExists('advisor_chats');
    }
};
