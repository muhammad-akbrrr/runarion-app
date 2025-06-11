<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class ProjectLog extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $fillable = [
    'date',
    'user_id',
    'event',
    'project_id',
    'workspace_id',
    'metadata',
    'ip_address',
    'user_agent',
    'severity',
    'related_entity_id',
    'related_entity_type',
    'changes',
  ];

  protected $casts = [
    'date' => 'datetime',
    'metadata' => 'array',
    'related_entity_id' => 'array',
    'related_entity_type' => 'array',
    'changes' => 'array',
  ];

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'date' => ['required', 'date'],
      'user_id' => ['required', 'exists:users,id'],
      'event' => ['required', 'string'],
      'project_id' => ['required', 'ulid', 'exists:projects,id'],
      'workspace_id' => ['required', 'ulid', 'exists:workspaces,id'],
      'metadata' => ['nullable', 'array'],
      'ip_address' => ['nullable', 'string', 'ip'],
      'user_agent' => ['nullable', 'string'],
      'severity' => ['required', 'string', 'in:info,warning,error,critical'],
      'related_entity_id' => ['nullable', 'array'],
      'related_entity_type' => ['nullable', 'array'],
      'changes' => ['nullable', 'array'],
    ];
  }

  /**
   * Get the user that created the log.
   */
  public function user()
  {
    return $this->belongsTo(User::class);
  }

  /**
   * Get the project that owns the log.
   */
  public function project()
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the workspace that owns the log.
   */
  public function workspace()
  {
    return $this->belongsTo(Workspace::class, 'workspace_id');
  }
}