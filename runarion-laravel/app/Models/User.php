<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

/**
 * User Model
 * 
 * mewakili user pada sistem dengan fitur autentikasi dan manajemen workspace
 * meng extend class authenticatable laravel untuk fitur autentikasi
 */
class User extends Authenticatable 
    // implements MustVerifyEmail
{
    /** @use HasFactory<\Database\Factories\UserFactory> */
    use HasApiTokens, HasFactory, Notifiable;

    /**
     * attribute yang dapat diisi secara massal
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
     * attribute yang harus disembunyikan untuk serialisasi
     *
     * @var list<string>
     */
    protected $hidden = [
        'password',
        'remember_token',
    ];

    /**
     * ambil attribute akan menjadi cast
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

    /**
     * cek apakah email sudah diverifikasi
     * 
     * @return bool
     */
    public function isVerified(): bool
    {
        return $this->email_verified_at !== null;
    }

    /**
     * ambil semua workspace user
     * 
     * @return \Illuminate\Database\Eloquent\Relations\BelongsToMany
     */
    public function workspaces(): BelongsToMany
    {
        return $this->belongsToMany(Workspace::class, 'workspace_members');
    }

    /**
     * ambil semua membership workspace user
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function workspaceMemberships(): HasMany
    {
        return $this->hasMany(WorkspaceMember::class);
    }

    /**
     * ambil semua workspace dimana user sebagai owner
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function ownedWorkspaces(): HasMany
    {
        return $this->workspaceMemberships()->where('role', 'owner');
    }

    /**
     * cek apakah user sebagai owner dari workspace tertentu
     * 
     * @param Workspace $workspace The workspace to check
     * @return bool True if user is owner, false otherwise
     */
    public function isWorkspaceOwner(Workspace $workspace): bool
    {
        return $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->where('role', 'owner')
            ->exists();
    }

    /**
     * cek apakah user sebagai admin dari workspace tertentu
     * 
     * @param Workspace $workspace The workspace to check
     * @return bool True if user is admin, false otherwise
     */
    public function isWorkspaceAdmin(Workspace $workspace): bool
    {
        return $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->where('role', 'admin')
            ->exists();
    }

    /**
     * ambil role user di workspace tertentu
     * 
     * @param Workspace $workspace The workspace to check
     * @return string|null The user's role or null if not a member
     */
    public function getWorkspaceRole(Workspace $workspace): ?string
    {
        $membership = $this->workspaceMemberships()
            ->where('workspace_id', $workspace->id)
            ->first();

        return $membership ? $membership->role : null;
    }

    /**
     * cek apakah user memiliki permission tertentu pada suatu workspace
     * 
     * @param Workspace $workspace The workspace to check
     * @param string $permission The permission to check for
     * @return bool True if user has permission, false otherwise
     */
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
