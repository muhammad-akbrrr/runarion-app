<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            if (! Schema::hasColumn('workspaces', 'monthly_token_quota')) {
                $table->unsignedBigInteger('monthly_token_quota')->default(25000000)->after('is_active');
            }

            if (! Schema::hasColumn('workspaces', 'billing_cycle_anchor_at')) {
                $table->timestamp('billing_cycle_anchor_at')->nullable()->after('monthly_token_quota');
            }
        });

        DB::table('workspaces')
            ->whereNull('billing_cycle_anchor_at')
            ->update([
                'billing_cycle_anchor_at' => DB::raw('created_at'),
            ]);

        Schema::table('workspaces', function (Blueprint $table) {
            if (Schema::hasColumn('workspaces', 'cloud_storage')) {
                $table->dropColumn('cloud_storage');
            }
            if (Schema::hasColumn('workspaces', 'llm')) {
                $table->dropColumn('llm');
            }
            if (Schema::hasColumn('workspaces', 'monthly_quota')) {
                $table->dropColumn('monthly_quota');
            }
            if (Schema::hasColumn('workspaces', 'quota')) {
                $table->dropColumn('quota');
            }
        });

        Schema::table('projects', function (Blueprint $table) {
            if (Schema::hasColumn('projects', 'saved_in')) {
                $table->dropColumn('saved_in');
            }
        });
    }

    public function down(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            if (! Schema::hasColumn('workspaces', 'cloud_storage')) {
                $table->json('cloud_storage')->nullable();
            }
            if (! Schema::hasColumn('workspaces', 'llm')) {
                $table->json('llm')->nullable();
            }
            if (! Schema::hasColumn('workspaces', 'monthly_quota')) {
                $table->integer('monthly_quota')->default(50);
            }
            if (! Schema::hasColumn('workspaces', 'quota')) {
                $table->integer('quota')->default(50);
            }
            if (Schema::hasColumn('workspaces', 'billing_cycle_anchor_at')) {
                $table->dropColumn('billing_cycle_anchor_at');
            }
            if (Schema::hasColumn('workspaces', 'monthly_token_quota')) {
                $table->dropColumn('monthly_token_quota');
            }
        });

        Schema::table('projects', function (Blueprint $table) {
            if (! Schema::hasColumn('projects', 'saved_in')) {
                $table->string('saved_in', 2)->default('01');
            }
        });
    }
};
