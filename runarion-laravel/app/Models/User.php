<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    /** @use HasFactory<\Database\Factories\UserFactory> */
    use HasApiTokens, HasFactory, Notifiable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'name',
        'email',
        'password',
        'avatar_url',
        'settings',
    ];

    /**
     * The attributes that should be hidden for serialization.
     *
     * @var list<string>
     */
    protected $hidden = [
        'password',
        'remember_token',
    ];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
            'settings' => 'array',
        ];
    }

    public function workspaces(): BelongsToMany
    {
        return $this->belongsToMany(Workspace::class, 'workspace_members');
    }

    public function workspaceMemberships(): HasMany
    {
        return $this->hasMany(WorkspaceMember::class);
    }

    public function ownedWorkspaces(): HasMany
    {
        return $this->workspaceMemberships()->where('role', 'owner');
    }

    public function isWorkspaceOwner(Workspace $workspace): bool
    {
        return $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->where('role', 'owner')
            ->exists();
    }

    public function isWorkspaceAdmin(Workspace $workspace): bool
    {
        return $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->where('role', 'admin')
            ->exists();
    }

    public function getWorkspaceRole(Workspace $workspace): ?string
    {
        $membership = $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->first();

        return $membership ? $membership->role : null;
    }

    public function hasWorkspacePermission(Workspace $workspace, string $permission): bool
    {
        $userRole = $this->workspaces()
            ->where('workspace_id', $workspace->id)
            ->first()
            ->pivot
            ->role;

        if ($userRole === 'owner') {
            return true;
        }

        $permissions = $this->workspaces()
            ->where('workspace_id', $workspace->id)
            ->first()
            ->pivot
            ->permissions;

        return in_array($permission, $permissions ?? []);
    }
}
