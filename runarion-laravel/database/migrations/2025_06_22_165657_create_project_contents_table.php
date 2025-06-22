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
        Schema::create('project_contents', function (Blueprint $table) {
            $table->id();
            $table->ulid('project_id');
            $table->longText('content')->nullable();
            $table->json('editor_state')->nullable();
            $table->integer('word_count')->default(0);
            $table->integer('character_count')->default(0);
            $table->integer('version')->default(1);
            $table->timestamp('last_edited_at')->useCurrent();
            $table->timestamps();
            
            // Foreign key constraint
            $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
            
            // Unique constraint to ensure one content entry per project
            $table->unique(['project_id']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('project_contents');
    }
};
