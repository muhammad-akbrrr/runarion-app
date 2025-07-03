<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Validation\Rule;

/**
 * ProjectContent Model
 * 
 * Stores consolidated project content in JSON format with one-to-one relationship to projects
 */
class ProjectContent extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $table = 'project_content';

  protected $fillable = [
    'project_id',
    'content',
    'metadata',
    'last_edited_at',
    'last_edited_by',
  ];

  protected $casts = [
    'content' => 'array',
    'metadata' => 'array',
    'last_edited_at' => 'datetime',
    'last_edited_by' => 'integer',
  ];

  /**
   * Get the project that owns the content.
   */
  public function project()
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the user who last edited the content.
   */
  public function lastEditor()
  {
    return $this->belongsTo(User::class, 'last_edited_by');
  }

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'project_id' => ['required', 'ulid', 'exists:projects,id', 'unique:project_content,project_id'],
      'content' => ['required', 'array'],
      'content.*.order' => ['required', 'integer', 'min:0'],
      'content.*.chapter_name' => ['required', 'string', 'max:255'],
      'content.*.content' => ['required', 'string'],
      'content.*.summary' => ['nullable', 'string'],
      'content.*.plot_points' => ['nullable', 'array'],
      'metadata' => ['nullable', 'array'],
      'last_edited_by' => ['nullable', 'integer', 'exists:users,id'],
    ];
  }

  /**
   * Get total word count from all chapters
   */
  public function getTotalWordCountAttribute()
  {
    if (!$this->content) {
      return 0;
    }

    $totalWords = 0;
    foreach ($this->content as $chapter) {
      $totalWords += str_word_count(strip_tags($chapter['content'] ?? ''));
    }

    return $totalWords;
  }

  /**
   * Get chapter count
   */
  public function getChapterCountAttribute()
  {
    return $this->content ? count($this->content) : 0;
  }

  /**
   * Get chapters ordered by their order field
   */
  public function getOrderedChaptersAttribute()
  {
    if (!$this->content) {
      return [];
    }

    $chapters = $this->content;
    usort($chapters, function ($a, $b) {
      return $a['order'] <=> $b['order'];
    });

    return $chapters;
  }

  /**
   * Get a specific chapter by order
   */
  public function getChapterByOrder($order)
  {
    if (!$this->content) {
      return null;
    }

    foreach ($this->content as $chapter) {
      if ($chapter['order'] == $order) {
        return $chapter;
      }
    }

    return null;
  }

  /**
   * Add a new chapter with automatic order
   */
  public function addChapter($chapterName, $content)
  {
    $chapters = $this->content ?? [];
    $newOrder = count($chapters);

    $chapters[] = [
      'order' => $newOrder,
      'chapter_name' => $chapterName,
      'content' => $content,
    ];

    $this->update(['content' => $chapters]);
    return $this;
  }

  /**
   * Update a chapter by order
   */
  public function updateChapter($order, $chapterName, $content)
  {
    if (!$this->content) {
      return false;
    }

    $chapters = $this->content;
    foreach ($chapters as &$chapter) {
      if ($chapter['order'] == $order) {
        $chapter['chapter_name'] = $chapterName;
        $chapter['content'] = $content;
        $this->update(['content' => $chapters]);
        return true;
      }
    }

    return false;
  }

  /**
   * Remove a chapter by order
   */
  public function removeChapter($order)
  {
    if (!$this->content) {
      return false;
    }

    $chapters = array_filter($this->content, function ($chapter) use ($order) {
      return $chapter['order'] != $order;
    });

    // Reorder remaining chapters
    $reorderedChapters = [];
    foreach (array_values($chapters) as $index => $chapter) {
      $chapter['order'] = $index;
      $reorderedChapters[] = $chapter;
    }

    $this->update(['content' => $reorderedChapters]);
    return true;
  }

  /**
   * Update the last edited timestamp and user
   */
  public function updateLastEdited($userId = null)
  {
    $this->update([
      'last_edited_at' => now(),
      'last_edited_by' => $userId ?? auth()->id(),
    ]);
  }
}