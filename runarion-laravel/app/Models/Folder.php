<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
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
}