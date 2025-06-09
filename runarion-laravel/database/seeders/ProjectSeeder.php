<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\Projects;
use App\Models\Workspace;
use App\Models\Folder;

/**
 * Project Seeder
 * 
 * Seeds the projects table with initial data.
 * Creates sample projects within each folder of each workspace.
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
     * 
     * @return void
     */
    public function run(): void
    {
        // Create projects for each workspace
        Workspace::all()->each(function ($workspace) {
            // Get all folders for this workspace
            $folders = Folder::where('workspace_id', $workspace->id)->get();

            // Create 2-5 projects per folder
            foreach ($folders as $folder) {
                $projectCount = fake()->numberBetween(2, 5);

                for ($i = 0; $i < $projectCount; $i++) {
                    Projects::factory()->create([
                        'workspace_id' => $workspace->id,
                        'folder_id' => $folder->id,
                        'name' => "Project " . ($i + 1) . " in " . $folder->name,
                        'slug' => "project-" . $workspace->id . "-" . $folder->id . "-" . ($i + 1),
                        'category' => fake()->optional(0.8)->randomElement(['horror', 'sci-fi', 'fantasy', 'romance', 'thriller', 'mystery', 'adventure', 'comedy', 'dystopian', 'crime', 'fiction', 'biography', 'historical']),
                        'saved_in' => fake()->randomElement(['01', '02', '03', '04']),
                        'description' => fake()->optional(0.7)->paragraph(),
                        'is_active' => true,
                    ]);
                }
            }
        });
    }
}
