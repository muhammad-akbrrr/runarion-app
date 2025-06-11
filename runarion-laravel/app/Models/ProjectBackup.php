<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class ProjectBackup extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $fillable = [
    'project_id',
    'workspace_id',
    'date',
    'frequency',
    'backup_type',
    'size',
    'checksum',
    'status',
    'error_details',
    'storage_path',
    'storage_metadata',
    'version',
  ];

  protected $casts = [
    'date' => 'datetime',
    'storage_metadata' => 'array',
    'size' => 'integer',
  ];

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'project_id' => ['required', 'ulid', 'exists:projects,id'],
      'workspace_id' => ['required', 'ulid', 'exists:workspaces,id'],
      'date' => ['required', 'date'],
      'frequency' => ['required', 'string', 'in:daily,weekly,manual'],
      'backup_type' => ['required', 'string', 'in:automatic,manual,pre-restore'],
      'size' => ['required', 'integer', 'min:0'],
      'checksum' => ['required', 'string'],
      'status' => ['required', 'string', 'in:pending,completed,failed'],
      'error_details' => ['nullable', 'string'],
      'storage_path' => ['required', 'string'],
      'storage_metadata' => ['nullable', 'array'],
      'version' => ['nullable', 'string'],
    ];
  }

  /**
   * Get the project that owns the backup.
   */
  public function project()
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the workspace that owns the backup.
   */
  public function workspace()
  {
    return $this->belongsTo(Workspace::class, 'workspace_id');
  }
}