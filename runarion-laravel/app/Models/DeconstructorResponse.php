<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DeconstructorResponse extends Model
{
  protected $table = 'deconstructor_responses';

  protected $fillable = [
    'request_id',
    'session_id',
    'author_style_id',
    'project_id',
    'original_story',
    'rewritten_story',
    'metadata',
  ];

  protected $casts = [
    'request_id' => 'string', // ULID
    'session_id' => 'string', // ULID
    'author_style_id' => 'string', // ULID
    'project_id' => 'string', // ULID
    'metadata' => 'array',
  ];

  /**
   * Get the deconstructor log that owns this response.
   */
  public function deconstructorLog(): BelongsTo
  {
    return $this->belongsTo(DeconstructorLog::class, 'request_id', 'id');
  }

  /**
   * Get the project associated with this response.
   */
  public function project(): BelongsTo
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the author style associated with this response.
   */
  public function authorStyle(): BelongsTo
  {
    return $this->belongsTo(StructuredAuthorStyle::class, 'author_style_id');
  }

  /**
   * Get the total word count from the rewritten story.
   */
  public function getTotalWordCountAttribute(): int
  {
    if (!$this->rewritten_story) {
      return 0;
    }
    return str_word_count($this->rewritten_story);
  }

  /**
   * Get the total character count from the rewritten story.
   */
  public function getTotalCharacterCountAttribute(): int
  {
    if (!$this->rewritten_story) {
      return 0;
    }
    return strlen($this->rewritten_story);
  }

  /**
   * Get the total word count from the original story.
   */
  public function getOriginalWordCountAttribute(): int
  {
    if (!$this->original_story) {
      return 0;
    }
    return str_word_count($this->original_story);
  }

  /**
   * Get the processing time from metadata.
   */
  public function getProcessingTimeMsAttribute(): ?int
  {
    return $this->metadata['processing_time_ms'] ?? null;
  }

  /**
   * Get the total tokens from metadata.
   */
  public function getTotalTokensAttribute(): ?int
  {
    return $this->metadata['total_tokens'] ?? null;
  }

  /**
   * Get the number of chapters from metadata.
   */
  public function getTotalChaptersAttribute(): ?int
  {
    return $this->metadata['total_chapters'] ?? null;
  }

  /**
   * Get the chapters array from metadata.
   */
  public function getChaptersAttribute(): array
  {
    return $this->metadata['chapters'] ?? [];
  }
}