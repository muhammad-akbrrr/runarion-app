<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('generation_logs', function (Blueprint $table) {
            if (! Schema::hasColumn('generation_logs', 'usecase')) {
                $table->string('usecase')->nullable()->after('key_used');
            }
            if (! Schema::hasColumn('generation_logs', 'feature')) {
                $table->string('feature')->nullable()->after('usecase');
            }
            if (! Schema::hasColumn('generation_logs', 'token_basis')) {
                $table->string('token_basis')->default('gemini')->after('feature');
            }
            if (! Schema::hasColumn('generation_logs', 'workspace_usage_period_id')) {
                $table->uuid('workspace_usage_period_id')->nullable()->after('token_basis');
            }
            if (! Schema::hasColumn('generation_logs', 'billable_input_tokens')) {
                $table->unsignedBigInteger('billable_input_tokens')->nullable()->after('total_tokens');
            }
            if (! Schema::hasColumn('generation_logs', 'billable_output_tokens')) {
                $table->unsignedBigInteger('billable_output_tokens')->nullable()->after('billable_input_tokens');
            }
            if (! Schema::hasColumn('generation_logs', 'billable_total_tokens')) {
                $table->unsignedBigInteger('billable_total_tokens')->nullable()->after('billable_output_tokens');
            }
        });

        Schema::table('generation_logs', function (Blueprint $table) {
            if (Schema::hasColumn('generation_logs', 'workspace_usage_period_id')) {
                $table->foreign('workspace_usage_period_id')
                    ->references('id')
                    ->on('workspace_usage_periods')
                    ->nullOnDelete();
            }
        });
    }

    public function down(): void
    {
        Schema::table('generation_logs', function (Blueprint $table) {
            if (Schema::hasColumn('generation_logs', 'workspace_usage_period_id')) {
                $table->dropForeign(['workspace_usage_period_id']);
                $table->dropColumn('workspace_usage_period_id');
            }
            if (Schema::hasColumn('generation_logs', 'billable_total_tokens')) {
                $table->dropColumn('billable_total_tokens');
            }
            if (Schema::hasColumn('generation_logs', 'billable_output_tokens')) {
                $table->dropColumn('billable_output_tokens');
            }
            if (Schema::hasColumn('generation_logs', 'billable_input_tokens')) {
                $table->dropColumn('billable_input_tokens');
            }
            if (Schema::hasColumn('generation_logs', 'token_basis')) {
                $table->dropColumn('token_basis');
            }
            if (Schema::hasColumn('generation_logs', 'feature')) {
                $table->dropColumn('feature');
            }
            if (Schema::hasColumn('generation_logs', 'usecase')) {
                $table->dropColumn('usecase');
            }
        });
    }
};
