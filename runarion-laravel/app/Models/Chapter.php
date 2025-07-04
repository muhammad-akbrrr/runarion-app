<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class Chapter extends Model
{
    use HasFactory, HasUuids, SoftDeletes;

    protected $fillable = [
        'draft_id',
        'chapter_number',
        'title',
        'content',
    ];

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }
}