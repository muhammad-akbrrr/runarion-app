<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class DraftChunk extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'draft_id',
        'chunk_number',
        'raw_text',
        'cleaned_text',
    ];

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }
}