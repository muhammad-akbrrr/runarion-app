<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

/**
 * ProjectNodeEditor Model
 * 
 * Stores node editor data for projects with one-to-one relationship to projects
 */
class ProjectNodeEditor extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $table = 'project_node_editor';

  protected $fillable = [
    'project_id',
  ];

  /**
   * Get the project that owns the node editor.
   */
  public function project()
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'project_id' => ['required', 'ulid', 'exists:projects,id', 'unique:project_node_editor,project_id'],
    ];
  }
}