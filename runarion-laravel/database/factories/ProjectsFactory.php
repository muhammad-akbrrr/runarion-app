<?php

namespace Database\Factories;

use App\Models\Folder;
use App\Models\Projects;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use App\Models\User;
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
        }

        foreach ($members as $member) {
          // Skip if member has no user (shouldn't happen, but just in case)
          if (!$member->user)
            continue;

          // Owner always has admin access
          if ($member->role === 'owner') {
            $access[] = [
              'user' => [
                'id' => $member->user->id,
                'name' => $member->user->name,
                'email' => $member->user->email,
                'avatar_url' => $member->user->avatar_url,
              ],
              'role' => 'admin'
            ];
            continue;
          }

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
    });
  }

  /**
   * Set the project as inactive.
   * 
   * @return self
   */
  public function inactive(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_active' => false,
    ]);
  }

  /**
   * Set the project's storage location.
   * 
   * @param string $location Storage location code ('01' = Server, '02' = GDrive, '03' = Dropbox, '04' = OneDrive)
   * @return self
   */
  public function storedIn(string $location): self
  {
    return $this->state(fn(array $attributes) => [
      'saved_in' => $location,
    ]);
  }

  /**
   * letakkan project dalam folder tertentu.
   * secara otomatis mengatur workspace_id untuk sesuai dengan folder.
   * 
   * @param Folder $folder The folder to place the project in
   * @return self
   */
  public function inFolder(Folder $folder): self
  {
    return $this->state(fn(array $attributes) => [
      'folder_id' => $folder->id,
      'workspace_id' => $folder->workspace_id,
    ]);
  }
}