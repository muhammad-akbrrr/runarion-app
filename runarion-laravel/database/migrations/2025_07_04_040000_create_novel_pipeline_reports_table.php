<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('analysis_reports', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('draft_id');
            $table->string('report_type');
            $table->string('report_subject');
            $table->json('content_json');
            $table->timestamp('generated_at');
            $table->bigInteger('generated_by');
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->foreign('generated_by')->references('id')->on('users')->onDelete('cascade');
            $table->index(['draft_id', 'report_type']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('analysis_reports');
    }
};