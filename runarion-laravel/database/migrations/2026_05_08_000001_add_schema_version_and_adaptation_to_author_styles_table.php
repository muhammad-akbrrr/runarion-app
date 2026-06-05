<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('author_styles', function (Blueprint $table) {
            $table->unsignedSmallInteger('schema_version')
                ->default(1)
                ->after('author_name')
                ->comment('Author style schema version; v2 is the genre-neutral contract');
            $table->jsonb('adaptation_json')
                ->nullable()
                ->after('examples_json')
                ->comment('Portable traits, transfer risks, and suppression guidance');
        });
    }

    public function down(): void
    {
        Schema::table('author_styles', function (Blueprint $table) {
            $table->dropColumn(['schema_version', 'adaptation_json']);
        });
    }
};
