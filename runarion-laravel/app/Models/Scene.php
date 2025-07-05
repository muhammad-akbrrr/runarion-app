<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Scene extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'draft_id',
        'scene_number',
        'title',
        'summary',
        'setting',
        'characters',
        'original_content',
        'analysis_json',
        'enhanced_content',
    ];

    protected $casts = [
        'characters' => 'array',
        'analysis_json' => 'array',
    ];

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function plotIssues(): HasMany
    {
        return $this->hasMany(PlotIssue::class, 'affected_scene_id');
    }
}