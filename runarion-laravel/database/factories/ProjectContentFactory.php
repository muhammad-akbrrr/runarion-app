<?php

namespace Database\Factories;

use App\Models\ProjectContent;
use App\Models\Projects;
use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * ProjectContent Factory
 * 
 * Factory untuk membuat project content test dengan data yang realistis
 * menyediakan metode untuk membuat content dengan berbagai jumlah chapter
 * dan metadata yang sesuai.
 */
class ProjectContentFactory extends Factory
{
  protected $model = ProjectContent::class;

  /**
   * Define the model's default state.
   * membuat content dengan chapter-chapter yang realistis dan metadata yang sesuai.
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    $chapterCount = fake()->numberBetween(1, 5);
    $chapters = [];

    for ($i = 0; $i < $chapterCount; $i++) {
      $chapters[] = [
        'order' => $i,
        'chapter_name' => fake()->sentence(3, false),
        'content' => fake()->paragraphs(fake()->numberBetween(3, 8), true),
      ];
    }

    $totalWords = 0;
    foreach ($chapters as $chapter) {
      $totalWords += str_word_count(strip_tags($chapter['content']));
    }

    return [
      'project_id' => null, // Will be set when creating with specific project
      'content' => $chapters,
      'metadata' => [
        'total_words' => $totalWords,
        'total_chapters' => $chapterCount,
        'average_words_per_chapter' => $chapterCount > 0 ? round($totalWords / $chapterCount) : 0,
        'created_at' => now()->toISOString(),
        'last_modified' => now()->toISOString(),
      ],
      'last_edited_at' => fake()->optional(0.9)->dateTimeBetween('-30 days', 'now'),
      'last_edited_by' => fake()->optional(0.8)->randomElement(User::pluck('id')->toArray()),
    ];
  }
}