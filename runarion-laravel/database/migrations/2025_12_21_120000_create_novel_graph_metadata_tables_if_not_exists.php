<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Create novel_graph_vertices table if it doesn't exist
        if (!Schema::hasTable('novel_graph_vertices')) {
            Schema::create('novel_graph_vertices', function (Blueprint $table) {
                $table->id();
                $table->ulid('draft_id')->nullable()->comment('For deconstructor entities');
                $table->ulid('project_id')->nullable()->comment('For records system entities');
                $table->string('entity_type')->comment('Lowercase: character, location, item, faction, etc.');
                $table->string('entity_name');
                $table->bigInteger('vertex_id')->comment('Apache AGE vertex ID');
                $table->string('vertex_label')->comment('AGE vertex label: Character, Location, Faction, etc.');
                $table->json('properties')->nullable()->comment('Entity properties as JSON');
                $table->timestamps();
                $table->softDeletes();

                // Foreign keys
                $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
                $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
                
                // Indexes
                $table->index(['draft_id', 'entity_type']);
                $table->index(['project_id', 'entity_type']);
                $table->index('vertex_id');
                $table->index('entity_name');
                
                // Ensure either draft_id or project_id is set
                $table->rawIndex('(CASE WHEN draft_id IS NOT NULL THEN draft_id ELSE project_id END)', 'graph_context_index');
            });
        } else {
            // Table exists, just add project_id if it doesn't exist
            if (!Schema::hasColumn('novel_graph_vertices', 'project_id')) {
                Schema::table('novel_graph_vertices', function (Blueprint $table) {
                    $table->ulid('project_id')->nullable()->after('draft_id');
                    $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
                    $table->index(['project_id', 'entity_type']);
                });
            }
        }

        // Create novel_graph_edges table if it doesn't exist
        if (!Schema::hasTable('novel_graph_edges')) {
            Schema::create('novel_graph_edges', function (Blueprint $table) {
                $table->id();
                $table->ulid('draft_id')->nullable()->comment('For deconstructor relationships');
                $table->ulid('project_id')->nullable()->comment('For records system relationships');
                $table->unsignedBigInteger('scene_id')->nullable();
                $table->bigInteger('source_vertex_id')->comment('Apache AGE source vertex ID');
                $table->bigInteger('target_vertex_id')->comment('Apache AGE target vertex ID');
                $table->bigInteger('edge_id')->comment('Apache AGE edge ID');
                $table->string('edge_label')->comment('AGE edge label: INTERACTS_WITH, ALLIED_WITH, etc.');
                $table->json('properties')->nullable()->comment('Relationship properties as JSON');
                $table->timestamps();
                $table->softDeletes();

                // Foreign keys
                $table->foreign('draft_id')->references('id')->on('drafts')->onDelete('cascade');
                $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
                $table->foreign('scene_id')->references('id')->on('scenes')->onDelete('set null');
                // Note: source_vertex_id and target_vertex_id are Apache AGE vertex IDs, not Laravel foreign keys
                // They reference vertices in the graph database, not this table directly
                // We use indexes for performance but don't enforce referential integrity at the database level
                
                // Indexes
                $table->index(['draft_id', 'edge_label']);
                $table->index(['project_id', 'edge_label']);
                $table->index('edge_id');
                $table->index(['source_vertex_id', 'target_vertex_id']);
            });
        } else {
            // Table exists, just add project_id if it doesn't exist
            if (!Schema::hasColumn('novel_graph_edges', 'project_id')) {
                Schema::table('novel_graph_edges', function (Blueprint $table) {
                    $table->ulid('project_id')->nullable()->after('draft_id');
                    $table->foreign('project_id')->references('id')->on('projects')->onDelete('cascade');
                    $table->index(['project_id', 'edge_label']);
                });
            }
        }
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // Don't drop tables if they exist (they might be used by deconstructor)
        // Just remove project_id columns if they were added
        if (Schema::hasColumn('novel_graph_vertices', 'project_id')) {
            Schema::table('novel_graph_vertices', function (Blueprint $table) {
                $table->dropForeign(['project_id']);
                $table->dropIndex(['project_id', 'entity_type']);
                $table->dropColumn('project_id');
            });
        }

        if (Schema::hasColumn('novel_graph_edges', 'project_id')) {
            Schema::table('novel_graph_edges', function (Blueprint $table) {
                $table->dropForeign(['project_id']);
                $table->dropIndex(['project_id', 'edge_label']);
                $table->dropColumn('project_id');
            });
        }
    }
};

