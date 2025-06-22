<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasOne;

class DeconstructorLog extends Model
{
  protected $table = 'deconstructor_logs';

  protected $fillable = [
    'request_id',
    'user_id',
    'workspace_id',
    'project_id',
    'rough_draft_path',
    'author_style_info',
    'author_style_id',
    'writing_perspective',
    'caller_info',
    'requested_at',
    'completed_at',
    'duration_ms',
    'response_metadata',
    'status',
    'error_message',
  ];

  protected $casts = [
    'user_id' => 'integer',
    'workspace_id' => 'string',
    'project_id' => 'string',
    'author_style_id' => 'string',
    'author_style_info' => 'array',
    'writing_perspective' => 'array',
    'caller_info' => 'array',
    'response_metadata' => 'array',
    'requested_at' => 'datetime',
    'completed_at' => 'datetime',
  ];

  /**
   * Get the deconstructor response associated with this log.
   */
  public function deconstructorResponse(): HasOne
  {
    return $this->hasOne(DeconstructorResponse::class, 'request_id', 'request_id');
  }
}