<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Str;

/**
 * Folder Model
 * 
 * sistem folder pada workspace yang bisa diisi dengan project
 * setiap folder akan memiliki setting & konfigurasi tersendiri
 */
class Folder extends Model
{
  use HasFactory, SoftDeletes;

  protected $fillable = [
    'workspace_id',
    'name',
    'slug',
    'description',
    'settings',
    'is_public',
    'is_active',
  ];

  protected $casts = [
    'settings' => 'array',
    'is_public' => 'boolean',
    'is_active' => 'boolean',
  ];

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

  /**
   * ambil workspace yang memiliki folder ini
   * 
   * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
   */
  public function workspace(): BelongsTo
  {
    return $this->belongsTo(Workspace::class);
  }

  /**
   * ambil semua project yang ada di folder ini
   * 
   * @return \Illuminate\Database\Eloquent\Relations\HasMany
   */
  public function projects(): HasMany
  {
    return $this->hasMany(Projects::class);
  }

  /**
   * ambil value setting tertentu dari array setting folder
   * 
   * @param string $key The setting key to retrieve
   * @param mixed $default The default value if setting doesn't exist
   * @return mixed The setting value or default if not found
   */
  public function getSetting(string $key, $default = null)
  {
    return $this->settings[$key] ?? $default;
  }

  /**
   * set value setting tertentu dari array setting folder
   * 
   * @param string $key The setting key to set
   * @param mixed $value The value to set
   * @return void
   */
  public function setSetting(string $key, $value): void
  {
    $settings = $this->settings ?? [];
    $settings[$key] = $value;
    $this->settings = $settings;
  }
}