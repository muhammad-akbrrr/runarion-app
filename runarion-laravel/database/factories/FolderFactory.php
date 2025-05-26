<?php

namespace Database\Factories;

use App\Models\Folder;
use App\Models\Workspace;
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
      'is_active' => true,
    ];
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

  /**
   * Set the folder as public.
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
   * Set the folder as private.
   * 
   * @return self
   */
  public function private(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_public' => false,
    ]);
  }
}