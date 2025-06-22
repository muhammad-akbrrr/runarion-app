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
    'author_style_id' => 'string',
    'project_id' => 'string',
    'metadata' => 'array',
  ];

  /**
   * Get the deconstructor log that owns this response.
   */
  public function deconstructorLog(): BelongsTo
  {
    return $this->belongsTo(DeconstructorLog::class, 'request_id', 'request_id');
  }

  /**
   * Get the project associated with this response.
   */
  public function project(): BelongsTo
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }
}