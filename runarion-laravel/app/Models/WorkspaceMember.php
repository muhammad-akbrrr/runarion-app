<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\Rule;

/**
 * WorkspaceMember Model
 * 
 * mewakili hubungan antara user dan workspace, termasuk informasi role
 * ini adalah model pivot yang mengelola hubungan many-to-many antara user dan workspace
 */
class WorkspaceMember extends Model
{
  use HasFactory, HasUlids;

  protected $fillable = [
    'workspace_id',
    'user_id',
    'role',
  ];

  protected $casts = [
    'role' => 'string',
  ];

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'workspace_id' => ['required', 'ulid', 'exists:workspaces,id'],
      'user_id' => ['required', 'ulid', 'exists:users,id'],
      'role' => ['required', 'string', Rule::in(['owner', 'admin', 'member'])],
    ];
  }

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
   * Get the user that owns the workspace membership.
   */
  public function user()
  {
    return $this->belongsTo(User::class);
  }

  /**
   * Get the workspace that owns the membership.
   */
  public function workspace()
  {
    return $this->belongsTo(Workspace::class);
  }
}