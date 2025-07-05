<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('scenes', function (Blueprint $table) {
            $table->id();
            $table->ulid('draft_id');
            $table->integer('scene_number');
            $table->string('title');
            $table->longText('summary');
            $table->longText('setting');
            $table->json('characters');
            $table->longText('original_content');
            $table->json('analysis_json')->nullable();
            $table->longText('enhanced_content')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->index(['draft_id', 'scene_number']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('scenes');
    }
};