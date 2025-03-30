<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * WorkspaceMember Model
 * 
 * mewakili hubungan antara user dan workspace, termasuk informasi role
 * ini adalah model pivot yang mengelola hubungan many-to-many antara user dan workspace
 */
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

  /**
   * load modelnya.
   * menambahkan constraint unik untuk mencegah beberapa owner pada workspace.
   */
  protected static function boot()
  {
    parent::boot();

    static::saving(function ($member) {
      if ($member->role === 'owner') {
        // Check if there's already an owner for this workspace
        $existingOwner = static::where('workspace_id', $member->workspace_id)
          ->where('role', 'owner')
          ->where('id', '!=', $member->id)
          ->exists();

        if ($existingOwner) {
          throw new \RuntimeException('A workspace can only have one owner.');
        }
      }
    });
  }

  /**
   * Get the workspace associated with this membership
   * 
   * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
   */
  public function workspace(): BelongsTo
  {
    return $this->belongsTo(Workspace::class);
  }

  /**
   * ambil user yang terkait dengan membership ini
   * 
   * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
   */
  public function user(): BelongsTo
  {
    return $this->belongsTo(User::class);
  }

  /**
   * cek apakah member memiliki role owner
   * 
   * @return bool True jika member adalah owner, false jika tidak
   */
  public function isOwner(): bool
  {
    return $this->role === 'owner';
  }

  /**
   * cek apakah member memiliki role admin
   * 
   * @return bool True jika member adalah admin, false jika tidak
   */
  public function isAdmin(): bool
  {
    return $this->role === 'admin';
  }

  /**
   * cek apakah member memiliki role member
   * 
   * @return bool True jika member adalah member, false jika tidak
   */
  public function isMember(): bool
  {
    return $this->role === 'member';
  }
}