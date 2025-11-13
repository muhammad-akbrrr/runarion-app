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
        Schema::table('chapters', function (Blueprint $table) {
            // Add chapter metadata from v2.0 chaptering architecture
            $table->integer('word_count')->nullable()->after('content');
            $table->integer('start_scene')->nullable()->after('word_count');
            $table->integer('end_scene')->nullable()->after('start_scene');
            $table->integer('scene_count')->nullable()->after('end_scene');
            $table->json('scene_titles')->nullable()->after('scene_count');

            // Add indices for performance when querying by scene ranges
            $table->index(['draft_id', 'start_scene', 'end_scene'], 'chapters_draft_scene_range');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('chapters', function (Blueprint $table) {
            // Drop the index first
            $table->dropIndex('chapters_draft_scene_range');

            // Drop the columns
            $table->dropColumn([
                'word_count',
                'start_scene',
                'end_scene',
                'scene_count',
                'scene_titles'
            ]);
        });
    }
};
