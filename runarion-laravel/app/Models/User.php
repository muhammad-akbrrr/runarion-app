<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Facades\DB;
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
        'last_workspace_id',
        'last_project_id',
        'settings',
        'notifications',
        'highlighted_projects'
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
            'notifications' => 'array',
            'highlighted_projects' => 'array',
        ];
    }

    public function getActiveWorkspaceId(): string
    {
        if ($this->last_workspace_id) {
            return $this->last_workspace_id;
        }

        $ownedWorkspaceId = DB::table('workspace_members')
            ->where('user_id', $this->id)
            ->where('role', 'owner')
            ->value('workspace_id');

        $this->last_workspace_id = $ownedWorkspaceId;
        $this->saveQuietly();

        return $ownedWorkspaceId;
    }

    public function getActiveProjectId(): ?string
    {
        return $this->last_project_id;
    }
}
