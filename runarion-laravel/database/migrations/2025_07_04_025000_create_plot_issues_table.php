<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('plot_issues', function (Blueprint $table) {
            $table->id();
            $table->ulid('draft_id');
            $table->bigInteger('affected_scene_id');
            $table->string('issue_type');
            $table->string('description');
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
            $table->foreign('affected_scene_id')->references('id')->on('scenes')->onDelete('cascade');
            $table->index(['draft_id', 'issue_type']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('plot_issues');
    }
};