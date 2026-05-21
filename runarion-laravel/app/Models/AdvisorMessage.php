<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AdvisorMessage extends Model
{
    use HasFactory, HasUlids;

    protected $fillable = [
        'chat_id',
        'role',
        'content',
        'metadata',
    ];

    protected $casts = [
        'metadata' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * Get the chat that owns this message.
     */
    public function chat(): BelongsTo
    {
        return $this->belongsTo(AdvisorChat::class, 'chat_id');
    }

    /**
     * Check if this message contains a pending edit suggestion.
     */
    public function hasPendingEdit(): bool
    {
        return isset($this->metadata['pending_edit']) && $this->metadata['pending_edit'] === true;
    }

    /**
     * Get the edit data if this message contains an edit suggestion.
     */
    public function getEditData(): ?array
    {
        return $this->metadata['edit_data'] ?? null;
    }
}

