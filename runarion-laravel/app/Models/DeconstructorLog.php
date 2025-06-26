<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DeconstructorLog extends Model
{
  protected $table = 'deconstructor_logs';

  protected $fillable = [
    'id',
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
    return $this->hasOne(DeconstructorResponse::class, 'request_id', 'id');
  }

  /**
   * Get the user that owns this log.
   */
  public function user(): BelongsTo
  {
    return $this->belongsTo(User::class, 'user_id');
  }

  /**
   * Get the workspace that owns this log.
   */
  public function workspace(): BelongsTo
  {
    return $this->belongsTo(Workspace::class, 'workspace_id');
  }

  /**
   * Get the project that owns this log.
   */
  public function project(): BelongsTo
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the author style associated with this log.
   */
  public function authorStyle(): BelongsTo
  {
    return $this->belongsTo(StructuredAuthorStyle::class, 'author_style_id');
  }

  /**
   * Scope a query to only include pending logs.
   */
  public function scopePending($query)
  {
    return $query->where('status', 'pending');
  }


  /**
   * Scope a query to only include completed logs.
   */
  public function scopeCompleted($query)
  {
    return $query->where('status', 'completed');
  }

  /**
   * Scope a query to only include failed logs.
   */
  public function scopeFailed($query)
  {
    return $query->where('status', 'failed');
  }

  /**
   * Check if the log is in a final state (completed or failed).
   */
  public function isFinal(): bool
  {
    return in_array($this->status, ['completed', 'failed']);
  }

  /**
   * Check if the log is still processing.
   */
  public function isProcessing(): bool
  {
    return in_array($this->status, ['pending', 'processing']);
  }
}