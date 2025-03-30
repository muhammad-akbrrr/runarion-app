<?php

namespace Database\Factories;

use App\Models\Folder;
use App\Models\Projects;
use App\Models\Workspace;
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
      'name' => fake()->words(3, true),
      'slug' => fn(array $attributes) => Str::slug($attributes['name']),
      'description' => fake()->paragraph(),
      'settings' => [
        'theme' => fake()->randomElement(['light', 'dark']),
        'visibility' => fake()->randomElement(['public', 'private']),
        'notifications' => [
          'email' => true,
          'push' => true,
        ],
      ],
      'is_public' => fake()->boolean(30), // 30% chance of being public
      'is_active' => true,
    ];
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
   * Set the project as public.
   * 
   * @return self
   */
  public function public(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_public' => true,
    ]);
  }

  /**
   * Set the project as private.
   * 
   * @return self
   */
  public function private(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_public' => false,
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