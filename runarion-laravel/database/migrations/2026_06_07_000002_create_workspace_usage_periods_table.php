<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('workspace_usage_periods')) {
            return;
        }

        Schema::create('workspace_usage_periods', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->ulid('workspace_id');
            $table->timestamp('period_start_at');
            $table->timestamp('period_end_at');
            $table->unsignedBigInteger('token_quota')->default(25000000);
            $table->unsignedBigInteger('tokens_reserved')->default(0);
            $table->unsignedBigInteger('tokens_consumed')->default(0);
            $table->timestamps();

            $table->unique(['workspace_id', 'period_start_at']);
            $table->foreign('workspace_id')->references('id')->on('workspaces')->cascadeOnDelete();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('workspace_usage_periods');
    }
};
