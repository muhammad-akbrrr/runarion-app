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
        Schema::create('workspace_invitations', function (Blueprint $table) {
            $table->ulid('id')->primary();
            $table->ulid('workspace_id');
            $table->string('user_email');
            $table->enum('role', ['owner', 'admin', 'member'])->default('member');
            $table->string('token', 100)->unique();
            $table->timestamp('expired_at');
            $table->timestamps();

            $table->unique(['workspace_id', 'user_email']);
            $table->foreign('workspace_id')->references('id')->on('workspaces')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('workspace_invitations');
    }
};
