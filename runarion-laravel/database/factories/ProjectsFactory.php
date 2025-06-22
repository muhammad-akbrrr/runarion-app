<?php

namespace Database\Factories;

use App\Models\Projects;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use App\Models\ProjectContent;
use App\Models\ProjectNodeEditor;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * Projects Factory
 * 
 * Factory untuk membuat project test dengan data yang realistis
 * menyediakan metode untuk membuat project dalam berbagai keadaan (aktif/tidak aktif, publik/privat)
 * dan bisa disimpan dalam folder tertentu.
 */
class ProjectsFactory extends Factory
{
  protected $model = Projects::class;

  /**
   * Define the model's default state.
   * membuat project dengan informasi dasar termasuk nama, deskripsi,
   * dan pengaturan. Project memiliki peluang 30% untuk menjadi publik secara default.
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    return [
      'workspace_id' => Workspace::factory(),
      'folder_id' => null,
      'original_author' => null, // Will be set in configure method
      'name' => fake()->words(3, true),
      'slug' => fn(array $attributes) => Str::slug($attributes['name']),
      'settings' => null,
      'category' => fake()->optional(0.8)->randomElement(['horror', 'sci-fi', 'fantasy', 'romance', 'thriller', 'mystery', 'adventure', 'comedy', 'dystopian', 'crime', 'fiction', 'biography', 'historical']),
      'saved_in' => fake()->randomElement(['01', '02', '03', '04']),
      'description' => fake()->optional(0.7)->paragraph(),
      'access' => null,
      'is_active' => true,
      'backup_frequency' => fake()->randomElement(['daily', 'weekly', 'manual']),
      'completed_onboarding' => false,
    ];
  }

  /**
   * Configure the model factory.
   */
  public function configure()
  {
    return $this->afterCreating(function (Projects $project) {
      // Get all workspace members
      $members = WorkspaceMember::where('workspace_id', $project->workspace_id)
        ->with('user:id,name,email,avatar_url')
        ->get();

      if ($members->isNotEmpty()) {
        $access = [];
        $owner = $members->firstWhere('role', 'owner');

        // Set original author to workspace owner if available
        if ($owner && $owner->user) {
          $project->original_author = $owner->user->id;

          // Always add original author as admin
          $access[] = [
            'user' => [
              'id' => $owner->user->id,
              'name' => $owner->user->name,
              'email' => $owner->user->email,
              'avatar_url' => $owner->user->avatar_url,
            ],
            'role' => 'admin'
          ];
        }

        foreach ($members as $member) {
          // Skip if member has no user (shouldn't happen, but just in case)
          if (!$member->user)
            continue;

          // Skip if this is the original author (already added above)
          if ((string) $member->user->id === (string) $project->original_author)
            continue;

          // For other roles, 70% chance of having access
          if (fake()->boolean(70)) {
            $access[] = [
              'user' => [
                'id' => $member->user->id,
                'name' => $member->user->name,
                'email' => $member->user->email,
                'avatar_url' => $member->user->avatar_url,
              ],
              'role' => fake()->randomElement(['editor', 'manager', 'admin'])
            ];
          }
        }

        $project->access = $access;
        $project->save();
      }

      // Create ProjectContent for this project
      ProjectContent::factory()->create([
        'project_id' => $project->id,
        'last_edited_by' => $project->original_author,
      ]);

      // Create ProjectNodeEditor for this project
      ProjectNodeEditor::factory()->create([
        'project_id' => $project->id,
      ]);
    });
  }
}