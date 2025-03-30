<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class WorkspaceMember extends Model
{
  use HasFactory;

  protected $fillable = [
    'workspace_id',
    'user_id',
    'role',
  ];

  protected $casts = [
    'role' => 'string',
  ];

  public function workspace(): BelongsTo
  {
    return $this->belongsTo(Workspace::class);
  }

  public function user(): BelongsTo
  {
    return $this->belongsTo(User::class);
  }

  public function isOwner(): bool
  {
    return $this->role === 'owner';
  }

  public function isAdmin(): bool
  {
    return $this->role === 'admin';
  }

  public function isMember(): bool
  {
    return $this->role === 'member';
  }
}