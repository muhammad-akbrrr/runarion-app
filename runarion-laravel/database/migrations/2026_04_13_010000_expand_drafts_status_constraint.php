<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Expand the drafts.status CHECK constraint to include novel writer
     * and pipeline orchestrator status values added to DraftStatus after
     * the original migration was written.
     */
    public function up(): void
    {
        DB::statement('ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_status_check');

        DB::statement("
            ALTER TABLE drafts
            ADD CONSTRAINT drafts_status_check CHECK (status IN (
                'pending',
                'processing',
                'stage_1_complete',
                'stage_2_complete',
                'stage_3_complete',
                'stage_4_complete',
                'stage_5_complete',
                'stage_6_complete',
                'completed',
                'failed',
                'novel_writing',
                'nw_stage_1_complete',
                'nw_stage_2_complete',
                'nw_stage_3_complete',
                'nw_stage_4_complete',
                'nw_completed',
                'nw_failed',
                'pipeline_pending',
                'pipeline_phase_1_2_running',
                'pipeline_phase_3_running',
                'pipeline_completed',
                'pipeline_failed'
            ))
        ");
    }

    /**
     * Restore the original constraint (deconstructor statuses only).
     */
    public function down(): void
    {
        DB::statement('ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_status_check');

        DB::statement("
            ALTER TABLE drafts
            ADD CONSTRAINT drafts_status_check CHECK (status IN (
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
            ))
        ");
    }
};
