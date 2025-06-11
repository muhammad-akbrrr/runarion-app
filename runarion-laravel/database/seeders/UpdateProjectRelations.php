<?php

namespace Database\Seeders;

use App\Models\Projects;
use App\Models\User;
use App\Models\WorkspaceMember;
use Illuminate\Database\Seeder;

class UpdateProjectRelations extends Seeder
{
  /**
   * Run the database seeds.
   * 
   * 1. Updates the original_author field for all projects
   * 2. Sets highlighted projects for all users
   */
  public function run(): void
  {
    // First, update project authors
    Projects::all()->each(function ($project) {
      $owner = WorkspaceMember::where('workspace_id', $project->workspace_id)
        ->where('role', 'owner')
        ->first();

      if ($owner) {
        $project->original_author = $owner->user_id;
        $project->save();
      }
    });

    // Then, set highlighted projects for all users
    User::all()->each(function ($user) {
      // Get all workspaces the user is a member of
      $workspaces = WorkspaceMember::where('user_id', $user->id)
        ->with([
          'workspace' => function ($query) {
            $query->with('projects');
          }
        ])
        ->get()
        ->pluck('workspace');

      if ($workspaces->isNotEmpty()) {
        // Randomly select 1-3 projects to highlight
        $highlightedProjects = collect();
        foreach ($workspaces as $workspace) {
          if ($workspace->projects->isNotEmpty()) {
            $projectCount = min(3, $workspace->projects->count());
            $projects = $workspace->projects->random($projectCount);

            foreach ($projects as $project) {
              $highlightedProjects->push([
                'created_at' => now()->toIso8601String(),
                'project_id' => $project->id,
                'workspace_id' => $workspace->id,
              ]);
            }
          }
        }

        if ($highlightedProjects->isNotEmpty()) {
          $user->highlighted_projects = $highlightedProjects->toArray();
          $user->save();
        }
      }
    });
  }
}