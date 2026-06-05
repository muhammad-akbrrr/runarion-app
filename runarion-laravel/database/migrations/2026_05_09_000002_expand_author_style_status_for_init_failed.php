<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        $driver = Schema::getConnection()->getDriverName();
        $statuses = "'init_completed','init_failed','sampling_completed','sampling_failed','profiling_completed','profiling_failed'";

        if ($driver === 'pgsql') {
            DB::statement('ALTER TABLE author_styles DROP CONSTRAINT IF EXISTS author_styles_status_check');
            DB::statement("ALTER TABLE author_styles ADD CONSTRAINT author_styles_status_check CHECK (status::text = ANY (ARRAY[{$statuses}]::text[]))");

            return;
        }

        if ($driver === 'mysql') {
            DB::statement("ALTER TABLE author_styles MODIFY status ENUM({$statuses}) NOT NULL");
        }
    }

    public function down(): void
    {
        $driver = Schema::getConnection()->getDriverName();
        $statuses = "'init_completed','sampling_completed','sampling_failed','profiling_completed','profiling_failed'";

        if ($driver === 'pgsql') {
            DB::statement('ALTER TABLE author_styles DROP CONSTRAINT IF EXISTS author_styles_status_check');
            DB::statement("ALTER TABLE author_styles ADD CONSTRAINT author_styles_status_check CHECK (status::text = ANY (ARRAY[{$statuses}]::text[]))");

            return;
        }

        if ($driver === 'mysql') {
            DB::statement("ALTER TABLE author_styles MODIFY status ENUM({$statuses}) NOT NULL");
        }
    }
};
