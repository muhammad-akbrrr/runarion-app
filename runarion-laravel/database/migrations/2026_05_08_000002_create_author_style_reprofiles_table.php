<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('author_style_reprofiles', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('author_style_id');
            $table->ulid('workspace_id');
            $table->text('author_name');
            $table->unsignedSmallInteger('legacy_schema_version')->default(1);
            $table->enum('status', ['pending', 'processing', 'completed', 'failed', 'skipped'])->default('pending');
            $table->text('failure_reason')->nullable();
            $table->timestamp('requested_at')->useCurrent();
            $table->timestamp('processed_at')->nullable();
            $table->timestamp('created_at')->useCurrent();
            $table->timestamp('updated_at')->nullable();

            $table->foreign('author_style_id')->references('id')->on('author_styles')->cascade();
            $table->foreign('workspace_id')->references('id')->on('workspaces')->cascade();
            $table->unique('author_style_id', 'unique_author_style_reprofile');
        });

        $legacyRows = DB::table('author_styles')
            ->select('id', 'workspace_id', 'author_name', 'schema_version')
            ->where('schema_version', 1)
            ->get();

        foreach ($legacyRows as $row) {
            DB::table('author_style_reprofiles')->insert([
                'id' => (string) Str::ulid(),
                'author_style_id' => $row->id,
                'workspace_id' => $row->workspace_id,
                'author_name' => $row->author_name,
                'legacy_schema_version' => (int) $row->schema_version,
                'status' => 'pending',
                'requested_at' => now(),
                'created_at' => now(),
                'updated_at' => now(),
            ]);
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('author_style_reprofiles');
    }
};
