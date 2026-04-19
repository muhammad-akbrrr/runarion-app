<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     *
     * Creates the pipeline_runs table for tracking full novel pipeline orchestration.
     * Each pipeline run coordinates 3 phases:
     *   Phase 1: Deconstructor  - analyzes and deconstructs the source manuscript
     *   Phase 2: Style Analyzer - profiles the author's writing voice from sample files
     *   Phase 3: Novel Writer   - rewrites the source material in the author's voice
     *
     * Phases 1 and 2 run in parallel. Phase 3 depends on both completing successfully.
     */
    public function up(): void
    {
        Schema::create('pipeline_runs', function (Blueprint $table) {
            $table->ulid('id')->primary();

            // Core relations
            $table->ulid('draft_id')->comment('The source manuscript draft being processed');
            $table->ulid('workspace_id');
            $table->bigInteger('user_id')->unsigned();

            // Style analyzer output link (populated after Phase 2 completes)
            $table->ulid('author_style_id')->nullable()->comment('Linked author_styles record, set after Phase 2');
            $table->text('author_name')->comment('Target author voice name');

            // Overall pipeline status
            $table->enum('status', [
                'pending',
                'phase_1_2_running',  // Phases 1 & 2 running in parallel
                'phase_3_running',    // Phase 3 (Novel Writer) running
                'completed',
                'failed',
            ])->default('pending');

            $table->smallInteger('current_phase')->nullable()->comment('Active phase number: 1, 2, or 3');

            // Per-phase status tracking
            $table->enum('phase_1_status', [
                'pending', 'running', 'completed', 'failed', 'skipped',
            ])->default('pending')->comment('Deconstructor phase status');

            $table->enum('phase_2_status', [
                'pending', 'running', 'completed', 'failed', 'skipped',
            ])->default('pending')->comment('Style Analyzer phase status');

            $table->enum('phase_3_status', [
                'pending', 'running', 'completed', 'failed', 'skipped',
            ])->default('pending')->comment('Novel Writer phase status');

            // Full configuration snapshot for auditability and retry support
            $table->json('config')->nullable()->comment('Pipeline configuration used for this run');

            // Error tracking
            $table->text('error_message')->nullable();
            $table->smallInteger('failed_phase')->nullable()->comment('Phase number that caused the failure (1, 2, or 3)');

            // Timing
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();

            // Phase-level diagnostics: per-phase timing, results, and error detail
            $table->json('metadata')->nullable()->comment('Phase-level timing, results, and diagnostics');

            $table->timestamps();
            $table->softDeletes();

            // Foreign keys
            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
            $table->foreign('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->foreign('author_style_id')->references('id')->on('author_styles')->onDelete('set null');

            // Indexes for common query patterns
            $table->index(['workspace_id', 'status']);
            $table->index(['draft_id', 'status']);
            $table->index(['user_id', 'workspace_id']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('pipeline_runs');
    }
};
