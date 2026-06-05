<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Add unique constraint to scenes table for draft_id + scene_number
        // This prevents duplicate scene numbers within the same draft
        Schema::table('scenes', function (Blueprint $table) {
            $table->unique(['draft_id', 'scene_number'], 'scenes_draft_scene_number_unique');
        });

        // Add unique constraint to draft_chunks table for draft_id + chunk_number
        // This prevents duplicate chunk numbers within the same draft
        Schema::table('draft_chunks', function (Blueprint $table) {
            $table->unique(['draft_id', 'chunk_number'], 'draft_chunks_draft_chunk_number_unique');
        });
    }

    public function down(): void
    {
        // Remove the unique constraints
        Schema::table('scenes', function (Blueprint $table) {
            $table->dropUnique('scenes_draft_scene_number_unique');
        });

        Schema::table('draft_chunks', function (Blueprint $table) {
            $table->dropUnique('draft_chunks_draft_chunk_number_unique');
        });
    }
};
