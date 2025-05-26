<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            $table->dropColumn('description');
            $table->string('timezone')->nullable();
            $table->json('permissions')->nullable();
            $table->json('cloud_storage')->nullable();
            $table->json('llm')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            $table->text('description')->nullable();
            $table->dropColumn('timezone');
            $table->dropColumn('permissions');
            $table->dropColumn('cloud_storage');
            $table->dropColumn('llm');
        });
    }
};
