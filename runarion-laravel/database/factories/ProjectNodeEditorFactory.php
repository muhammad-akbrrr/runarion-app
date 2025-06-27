<?php

namespace Database\Factories;

use App\Models\ProjectNodeEditor;
use App\Models\Projects;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * ProjectNodeEditor Factory
 * 
 * Factory untuk membuat project node editor test dengan data yang realistis
 * menyediakan metode untuk membuat node editor data dengan berbagai konfigurasi.
 */
class ProjectNodeEditorFactory extends Factory
{
  protected $model = ProjectNodeEditor::class;

  /**
   * Define the model's default state.
   * membuat node editor dengan data dasar yang diperlukan.
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    return [
      'project_id' => null, // Will be set when creating with specific project
    ];
  }

  /**
   * Configure the model factory.
   */
  public function configure()
  {
    return $this->afterCreating(function (ProjectNodeEditor $nodeEditor) {
      // Future: Add any post-creation logic here if needed
      // For now, the node editor table is minimal and just needs the project_id
    });
  }
}