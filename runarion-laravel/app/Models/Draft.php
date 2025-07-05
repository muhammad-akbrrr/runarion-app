<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Draft extends Model
{
    use HasFactory, HasUuids, SoftDeletes;

    protected $fillable = [
        'workspace_id',
        'original_filename',
        'file_path',
        'file_size',
        'status',
        'processing_started_at',
        'processing_completed_at',
        'error_message',
        'metadata',
    ];

    protected $casts = [
        'metadata' => 'array',
        'processing_started_at' => 'datetime',
        'processing_completed_at' => 'datetime',
    ];

    public const STATUS_PENDING = 'pending';
    public const STATUS_PROCESSING = 'processing';
    public const STATUS_FAILED = 'failed';
    public const STATUS_COMPLETED = 'completed';

    public static function getStatusOptions(): array
    {
        return [
            self::STATUS_PENDING => 'Pending',
            self::STATUS_PROCESSING => 'Processing',
            self::STATUS_FAILED => 'Failed',
            self::STATUS_COMPLETED => 'Completed',
        ];
    }

    public function workspace(): BelongsTo
    {
        return $this->belongsTo(Workspace::class);
    }

    public function chunks(): HasMany
    {
        return $this->hasMany(DraftChunk::class);
    }

    public function scenes(): HasMany
    {
        return $this->hasMany(Scene::class);
    }

    public function plotIssues(): HasMany
    {
        return $this->hasMany(PlotIssue::class);
    }

    public function chapters(): HasMany
    {
        return $this->hasMany(Chapter::class);
    }

    public function finalManuscripts(): HasMany
    {
        return $this->hasMany(FinalManuscript::class);
    }

    public function analysisReports(): HasMany
    {
        return $this->hasMany(AnalysisReport::class);
    }
}