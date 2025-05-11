<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * WorkspaceInvitation Model
 * 
 * Represents an invitation to join a workspace sent to a user via email
 */
class WorkspaceInvitation extends Model
{
    protected $fillable = [
        'workspace_id',
        'user_email',
        'role',
        'token',
        'expired_at',
    ];

    protected $casts = [
        'role' => 'string',
        'expired_at' => 'datetime',
    ];

    /**
     * Get the workspace that owns the invitation
     */
    public function workspace(): BelongsTo
    {
        return $this->belongsTo(Workspace::class);
    }

    /**
     * Check if the invitation has expired
     */
    public function isExpired(): bool
    {
        return $this->expired_at->isPast();
    }
}
