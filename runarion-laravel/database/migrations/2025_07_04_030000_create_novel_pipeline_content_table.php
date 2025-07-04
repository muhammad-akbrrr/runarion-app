<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('chapters', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('draft_id');
            $table->integer('chapter_number');
            $table->string('title');
            $table->longText('content');
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->index(['draft_id', 'chapter_number']);
        });

        Schema::create('final_manuscripts', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('draft_id');
            $table->longText('final_content');
            $table->integer('word_count');
            $table->timestamp('generated_at');
            $table->bigInteger('generated_by');
            $table->longText('processing_summary')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->foreign('generated_by')->references('id')->on('users')->onDelete('cascade');
            $table->index(['draft_id', 'generated_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('final_manuscripts');
        Schema::dropIfExists('chapters');
    }
};