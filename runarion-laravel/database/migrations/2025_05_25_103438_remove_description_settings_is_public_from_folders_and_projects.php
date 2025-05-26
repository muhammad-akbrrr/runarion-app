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
        Schema::table('folders', function (Blueprint $table) {
            $table->dropColumn(['description', 'settings', 'is_public']);
        });

        Schema::table('projects', function (Blueprint $table) {
            $table->dropColumn(['description', 'is_public']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('folders', function (Blueprint $table) {
            $table->text('description')->nullable();
            $table->json('settings')->nullable();
            $table->boolean('is_public')->default(false);
        });

        Schema::table('projects', function (Blueprint $table) {
            $table->text('description')->nullable();
            $table->boolean('is_public')->default(false);
        });
    }
};
