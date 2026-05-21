<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AdvisorChat extends Model
{
    use HasFactory, HasUlids;

    protected $fillable = [
        'project_id',
        'title',
        'system_instructions',
        'model',
    ];

    protected $casts = [
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * Get the project that owns this chat.
     */
    public function project(): BelongsTo
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    /**
     * Get all messages in this chat.
     */
    public function messages(): HasMany
    {
        return $this->hasMany(AdvisorMessage::class, 'chat_id')->orderBy('created_at', 'asc');
    }

    /**
     * Get the most recent message in this chat.
     */
    public function latestMessage()
    {
        return $this->hasOne(AdvisorMessage::class, 'chat_id')->latestOfMany();
    }

    /**
     * Get message count for this chat.
     */
    public function getMessageCountAttribute(): int
    {
        return $this->messages()->count();
    }
}

