<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

/**
 * Folder Model
 * 
 * sistem folder pada workspace yang bisa diisi dengan project
 * setiap folder akan memiliki setting & konfigurasi tersendiri
 */
class Folder extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $fillable = [
    'workspace_id',
    'name',
    'slug',
    'original_author',
    'is_active',
  ];

  protected $casts = [
    'is_active' => 'boolean',
    'original_author' => 'integer',
  ];

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'workspace_id' => ['required', 'ulid', 'exists:workspaces,id'],
      'name' => ['required', 'string', 'max:255'],
      'slug' => [
        'required',
        'string',
        'max:255',
        Rule::unique('folders')->where(function ($query) {
          return $query->where('workspace_id', request()->route('workspace_id'))
            ->where('is_active', true);
        }),
      ],
      'original_author' => ['nullable', 'integer', 'exists:users,id'],
      'is_active' => ['boolean'],
    ];
  }

  /**
   * Get the author of the folder.
   */
  public function author()
  {
    return $this->belongsTo(User::class, 'original_author');
  }

  /**
   * load modelnya.
   * secara automatis akan membuat slug dari nama folder jika tidak ada slug
   */
  protected static function boot()
  {
    parent::boot();

    static::creating(function ($folder) {
      if (empty($folder->slug)) {
        $folder->slug = Str::slug($folder->name);
      }
    });
  }
}