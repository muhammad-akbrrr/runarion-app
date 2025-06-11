<?php

namespace Database\Factories;

use App\Models\Folder;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * Folder Factory
 * 
 * Factory untuk membuat folder test dengan data yang realistis
 * menyediakan metode untuk membuat folder dalam berbagai keadaan (aktif/tidak aktif, publik/privat)
 */
class FolderFactory extends Factory
{
  protected $model = Folder::class;

  /**
   * Define the model's default state.
   * membuat folder dengan informasi dasar seperti nama
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    return [
      'workspace_id' => Workspace::factory(),
      'name' => fake()->words(3, true),
      'slug' => fn(array $attributes) => Str::slug($attributes['name']),
      'original_author' => null,
      'is_active' => true,
    ];
  }

  /**
   * Configure the model factory.
   */
  public function configure()
  {
    return $this->afterCreating(function (Folder $folder) {
      // Get workspace owner
      $owner = WorkspaceMember::where('workspace_id', $folder->workspace_id)
        ->where('role', 'owner')
        ->with('user')
        ->first();

      if ($owner && $owner->user) {
        $folder->original_author = $owner->user->id;
        $folder->save();
      }
    });
  }

  /**
   * Set the folder as inactive.
   * 
   * @return self
   */
  public function inactive(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_active' => false,
    ]);
  }

}