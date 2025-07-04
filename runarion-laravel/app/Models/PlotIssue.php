<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class PlotIssue extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'draft_id',
        'affected_scene_id',
        'issue_type',
        'description',
    ];

    public const TYPE_PLOT_HOLE = '01';
    public const TYPE_INCONSISTENCY = '02';

    public static function getIssueTypeOptions(): array
    {
        return [
            self::TYPE_PLOT_HOLE => 'Plot Hole',
            self::TYPE_INCONSISTENCY => 'Inconsistency',
        ];
    }

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function affectedScene(): BelongsTo
    {
        return $this->belongsTo(Scene::class, 'affected_scene_id');
    }
}