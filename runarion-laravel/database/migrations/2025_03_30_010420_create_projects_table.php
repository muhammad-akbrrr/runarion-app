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
        Schema::create('projects', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->ulid('folder_id')->nullable();
            $table->unsignedBigInteger('original_author')->nullable();
            $table->string('name');
            $table->string('slug');
            $table->json('settings')->nullable()->comment('For in-project settings like LLM settings, etc');
            $table->enum('category', ['horror', 'sci-fi', 'fantasy', 'romance', 'thriller', 'mystery', 'adventure', 'comedy', 'dystopian', 'crime', 'fiction', 'biography', 'historical'])->nullable();
            $table->string('saved_in', 2)->default('01')->comment('01 = Server, 02 = GDrive, 03 = Dropbox, 04 = OneDrive');
            $table->longText('description')->nullable();
            $table->json('access')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamps();
            $table->softDeletes();

            $table->unique(['workspace_id', 'slug', 'is_active']);
            $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
            $table->foreign('folder_id')->references('id')->on('folders')->onDelete('set null');
            $table->foreign('original_author')->references('id')->on('users')->onDelete('set null');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('projects');
    }
};
