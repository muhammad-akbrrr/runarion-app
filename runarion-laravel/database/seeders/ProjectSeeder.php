<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\Projects;
use App\Models\Workspace;
use App\Models\Folder;
use App\Models\WorkspaceMember;

/**
 * Project Seeder
 * 
 * Seeds the projects table with initial data.
 * Creates sample projects within each folder of each workspace.
 * Also creates corresponding ProjectContent and ProjectNodeEditor records.
 */
class ProjectSeeder extends Seeder
{
    /**
     * Run the database seeds.
     * 
     * For each workspace:
     * 1. Gets all folders in the workspace
     * 2. For each folder:
     *    - Creates 2-5 random projects
     *    - All projects are set as active
     *    - Projects are named sequentially (Project 1, Project 2, etc.)
     *    - Projects are associated with their parent folder and workspace
     *    - Creates ProjectContent with realistic chapter data
     *    - Creates ProjectNodeEditor for node editor functionality
     * 
     * @return void
     */
    public function run(): void
    {
        // Create projects for each workspace
        Workspace::all()->each(function ($workspace) {
            // Get all folders for this workspace
            $folders = Folder::where('workspace_id', $workspace->id)->get();

            // Get workspace owner
            $owner = WorkspaceMember::where('workspace_id', $workspace->id)
                ->where('role', 'owner')
                ->with('user')
                ->first();

            if (!$owner || !$owner->user) {
                return; // Skip if no owner found
            }

            // Create 2-5 projects per folder
            foreach ($folders as $folder) {
                $projectCount = fake()->numberBetween(2, 5);

                for ($i = 0; $i < $projectCount; $i++) {
                    $project = Projects::factory()->create([
                        'workspace_id' => $workspace->id,
                        'folder_id' => $folder->id,
                        'name' => "Project " . ($i + 1) . " in " . $folder->name,
                        'slug' => "project-" . $workspace->id . "-" . $folder->id . "-" . ($i + 1),
                        'original_author' => $owner->user->id,
                    ]);

                    // Ensure original author is in access array with admin role
                    $access = $project->access ?? [];
                    $hasOriginalAuthor = false;

                    foreach ($access as $member) {
                        if ((string) $member['user']['id'] === (string) $owner->user->id) {
                            $hasOriginalAuthor = true;
                            break;
                        }
                    }

                    if (!$hasOriginalAuthor) {
                        $access[] = [
                            'user' => [
                                'id' => (string) $owner->user->id,
                                'name' => $owner->user->name,
                                'email' => $owner->user->email,
                                'avatar_url' => $owner->user->profile_photo_url ?? null,
                            ],
                            'role' => 'admin'
                        ];
                        $project->access = $access;
                        $project->save();
                    }
                }
            }
        });
    }
}
