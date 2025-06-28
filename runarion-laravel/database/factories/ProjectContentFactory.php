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
   * By default, returns the not completed onboarding state.
   *
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    // Default to not completed onboarding, no project context
    return $this->definitionNotCompleted(null);
  }

  /**
   * Definition for completed onboarding (at least 3 chapters, real text, etc)
   */
  public function definitionCompleted($project): array
  {
    $chapterCount = fake()->numberBetween(3, 5);
    $chapters = [];
    for ($i = 0; $i < $chapterCount; $i++) {
      $chapters[] = [
        'order' => $i,
        'chapter_name' => fake()->realTextBetween(10, 20),
        'content' => self::getRealisticText(2000),
        'summary' => fake()->optional(0.7)->sentence(10),
        'plot_points' => fake()->optional(0.7)->words(fake()->numberBetween(3, 7)),
      ];
    }
    $totalWords = array_sum(array_map(function ($chapter) {
      return str_word_count(strip_tags($chapter['content']));
    }, $chapters));
    $chapterCount = count($chapters);
    return [
      'project_id' => $project ? $project->id : null,
      'content' => $chapters,
      'metadata' => [
        'total_words' => $totalWords,
        'total_chapters' => $chapterCount,
        'average_words_per_chapter' => $chapterCount > 0 ? round($totalWords / $chapterCount) : 0,
        'created_at' => now()->toISOString(),
        'last_modified' => now()->toISOString(),
      ],
      'last_edited_at' => fake()->optional(0.9)->dateTimeBetween('-30 days', 'now'),
      'last_edited_by' => ($project && property_exists($project, 'original_author') && $project->original_author) ? $project->original_author : (fake()->optional(0.8)->randomElement(\App\Models\User::pluck('id')->toArray()) ?? null),
    ];
  }

  /**
   * Definition for not completed onboarding (1 empty chapter)
   */
  public function definitionNotCompleted($project): array
  {
    return [
      'project_id' => $project ? $project->id : null,
      'content' => [
        [
          'order' => 0,
          'chapter_name' => 'Chapter 1',
          'content' => '',
          'summary' => null,
          'plot_points' => null,
        ]
      ],
      'metadata' => [
        'total_words' => 0,
        'total_chapters' => 1,
        'average_words_per_chapter' => 0,
        'created_at' => now()->toISOString(),
        'last_modified' => now()->toISOString(),
      ],
      'last_edited_at' => fake()->optional(0.9)->dateTimeBetween('-30 days', 'now'),
      'last_edited_by' => ($project && property_exists($project, 'original_author') && $project->original_author) ? $project->original_author : (fake()->optional(0.8)->randomElement(\App\Models\User::pluck('id')->toArray()) ?? null),
    ];
  }

  /**
   * Generate a realistic text with at least $minWords words (not lorem ipsum).
   */
  public static function getRealisticText($minWords = 2000)
  {
    $text = '';
    while (str_word_count($text) < $minWords) {
      $text .= fake()->realTextBetween(800, 1200) . "\n\n";
    }
    // Optionally, you could use a static sample or API for more realism
    return $text;
  }
}