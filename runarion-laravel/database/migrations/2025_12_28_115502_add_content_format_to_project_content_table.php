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
            $table->string('content_format')->default('markdown')->after('content');
            $table->index('content_format');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('project_content', function (Blueprint $table) {
            $table->dropIndex(['content_format']);
            $table->dropColumn('content_format');
        });
    }
};
