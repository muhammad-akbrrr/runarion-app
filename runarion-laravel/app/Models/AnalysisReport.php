<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class AnalysisReport extends Model
{
    use HasFactory, HasUuids, SoftDeletes;

    protected $fillable = [
        'draft_id',
        'report_type',
        'report_subject',
        'content_json',
        'generated_at',
        'generated_by',
    ];

    protected $casts = [
        'content_json' => 'array',
        'generated_at' => 'datetime',
    ];

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function generatedBy(): BelongsTo
    {
        return $this->belongsTo(User::class, 'generated_by');
    }
}