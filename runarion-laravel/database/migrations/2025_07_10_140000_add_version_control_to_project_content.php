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
        Schema::table('project_content', function (Blueprint $table) {
            $table->json('generation_history')->nullable()->after('content');
            $table->string('current_step_id')->nullable()->after('generation_history');
            $table->json('last_selected_versions')->nullable()->after('current_step_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('project_content', function (Blueprint $table) {
            $table->dropColumn(['generation_history', 'current_step_id', 'last_selected_versions']);
        });
    }
};
