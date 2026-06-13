<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('project_snapshots', function (Blueprint $table) {
            $table->string('snapshot_kind')->default('manual')->after('description');
            $table->boolean('is_immutable')->default(false)->after('snapshot_kind');
            $table->ulid('source_snapshot_id')->nullable()->after('is_immutable');
            $table->unsignedSmallInteger('schema_version')->default(2)->after('source_snapshot_id');
            $table->string('state_hash', 64)->nullable()->after('schema_version');

            $table->foreign('source_snapshot_id')
                ->references('id')
                ->on('project_snapshots')
                ->nullOnDelete();

            $table->index(['project_id', 'snapshot_kind', 'created_at'], 'project_snapshots_kind_created_at_idx');
            $table->index(['project_id', 'state_hash'], 'project_snapshots_project_state_hash_idx');
        });

        Schema::table('project_node_editor', function (Blueprint $table) {
            $table->json('graph_state')->nullable()->after('project_id');
            $table->json('templates')->nullable()->after('graph_state');
        });
    }

    public function down(): void
    {
        Schema::table('project_node_editor', function (Blueprint $table) {
            $table->dropColumn(['graph_state', 'templates']);
        });

        Schema::table('project_snapshots', function (Blueprint $table) {
            $table->dropForeign(['source_snapshot_id']);
            $table->dropIndex('project_snapshots_kind_created_at_idx');
            $table->dropIndex('project_snapshots_project_state_hash_idx');
            $table->dropColumn([
                'snapshot_kind',
                'is_immutable',
                'source_snapshot_id',
                'schema_version',
                'state_hash',
            ]);
        });
    }
};
