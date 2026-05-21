<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('pipeline_runs', function (Blueprint $table) {
            $table->ulid('project_id')->nullable()->after('workspace_id');
            $table->string('import_status')->default('pending')->after('metadata');
            $table->text('import_error_message')->nullable()->after('import_status');
            $table->timestamp('imported_at')->nullable()->after('import_error_message');
            $table->ulid('project_snapshot_id')->nullable()->after('imported_at');

            $table->foreign('project_id')->references('id')->on('projects')->nullOnDelete();
            $table->foreign('project_snapshot_id')->references('id')->on('project_snapshots')->nullOnDelete();
            $table->index(['project_id', 'status']);
            $table->index(['project_id', 'import_status']);
        });

        $driver = Schema::getConnection()->getDriverName();

        if ($driver === 'pgsql') {
            DB::statement("
                UPDATE pipeline_runs
                SET project_id = NULLIF(config->'caller'->>'project_id', '')
                WHERE project_id IS NULL
            ");
        } elseif ($driver === 'mysql') {
            DB::statement("
                UPDATE pipeline_runs
                SET project_id = JSON_UNQUOTE(JSON_EXTRACT(config, '$.caller.project_id'))
                WHERE project_id IS NULL
            ");
        }

        DB::table('pipeline_runs')
            ->where('status', 'completed')
            ->update(['import_status' => 'completed']);

        DB::table('pipeline_runs')
            ->where('status', 'failed')
            ->update(['import_status' => 'failed']);
    }

    public function down(): void
    {
        Schema::table('pipeline_runs', function (Blueprint $table) {
            $table->dropForeign(['project_id']);
            $table->dropForeign(['project_snapshot_id']);
            $table->dropIndex(['project_id', 'status']);
            $table->dropIndex(['project_id', 'import_status']);
            $table->dropColumn([
                'project_id',
                'import_status',
                'import_error_message',
                'imported_at',
                'project_snapshot_id',
            ]);
        });
    }
};
