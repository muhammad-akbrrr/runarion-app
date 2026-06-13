<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('project_operations', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->ulid('project_id');
            $table->string('operation_type');
            $table->string('status');
            $table->string('phase')->nullable();
            $table->text('message')->nullable();
            $table->json('metadata')->nullable();
            $table->unsignedBigInteger('created_by')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
            $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
            $table->foreign('created_by')->references('id')->on('users')->nullOnDelete();

            $table->index(['workspace_id', 'project_id', 'status'], 'project_operations_workspace_project_status_idx');
            $table->index(['project_id', 'operation_type', 'created_at'], 'project_operations_project_type_created_idx');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('project_operations');
    }
};
