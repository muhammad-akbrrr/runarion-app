<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;

/**
 * WorkspaceInvitation Model
 * 
 * Represents an invitation to join a workspace sent to a user via email
 */
class WorkspaceInvitation extends Model
{
    use HasUlids;

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
}
