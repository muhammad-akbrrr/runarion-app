<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Validation\Rule;

/**
 * Projects Model
 * 
 * mewakili project yang ada pada workspace, setiap project bisa disimpan di folder
 * memiliki setting & konfigurasi tersendiri
 */
class Projects extends Model
{
    use HasFactory, SoftDeletes, HasUlids;

    protected $fillable = [
        'workspace_id',
        'folder_id',
        'original_author',
        'name',
        'slug',
        'settings',
        'category',
        'saved_in',
        'description',
        'access',
        'is_active',
        'backup_frequency',
        'last_backup_at',
        'next_backup_at',
    ];

    protected $casts = [
        'settings' => 'array',
        'access' => 'array',
        'is_active' => 'boolean',
        'original_author' => 'integer',
        'last_backup_at' => 'datetime',
        'next_backup_at' => 'datetime',
    ];

    /**
     * Get the author of the project.
     */
    public function author()
    {
        return $this->belongsTo(User::class, 'original_author');
    }

    /**
     * Get the validation rules that apply to the model.
     *
     * @return array<string, mixed>
     */
    public static function rules(): array
    {
        return [
            'workspace_id' => ['required', 'ulid', 'exists:workspaces,id'],
            'folder_id' => ['nullable', 'ulid', 'exists:folders,id'],
            'original_author' => ['nullable', 'integer', 'exists:users,id'],
            'name' => ['required', 'string', 'max:255'],
            'slug' => [
                'required',
                'string',
                'max:255',
                Rule::unique('projects')->where(function ($query) {
                    return $query->where('workspace_id', request()->route('workspace_id'))
                        ->where('is_active', true);
                }),
            ],
            'settings' => ['nullable', 'array'],
            'category' => ['nullable', 'string', Rule::in(['horror', 'sci-fi', 'fantasy', 'romance', 'thriller', 'mystery', 'adventure', 'comedy', 'dystopian', 'crime', 'fiction', 'biography', 'historical'])],
            'saved_in' => ['required', 'string', 'size:2', Rule::in(['01', '02', '03', '04'])],
            'description' => ['nullable', 'string'],
            'access' => ['nullable', 'array'],
            'access.*.user.id' => ['required', 'integer', 'exists:users,id'],
            'access.*.user.name' => ['required', 'string'],
            'access.*.user.email' => ['required', 'email'],
            'access.*.user.avatar_url' => ['nullable', 'string', 'url'],
            'access.*.role' => ['required', 'string', Rule::in(['editor', 'manager', 'admin'])],
            'is_active' => ['boolean'],
        ];
    }

    /**
     * Validate that users in access array are members of the workspace
     * and that the original author's special status is maintained
     */
    public function validateAccess(): bool
    {
        if (!$this->access) {
            return true;
        }

        $workspaceMemberIds = WorkspaceMember::where('workspace_id', $this->workspace_id)
            ->pluck('user_id')
            ->toArray();

        // Check if original author exists in access array
        $originalAuthorExists = false;
        $originalAuthorHasAdminRole = false;

        foreach ($this->access as $access) {
            if (!in_array($access['user']['id'], $workspaceMemberIds)) {
                return false;
            }

            // Check original author's status
            if ((string) $access['user']['id'] === (string) $this->original_author) {
                $originalAuthorExists = true;
                $originalAuthorHasAdminRole = $access['role'] === 'admin';
            }
        }

        // Original author must exist in access array and have admin role
        if ($this->original_author && (!$originalAuthorExists || !$originalAuthorHasAdminRole)) {
            return false;
        }

        return true;
    }

    /**
     * Get the backups for the project.
     */
    public function backups()
    {
        return $this->hasMany(ProjectBackup::class, 'project_id');
    }

    /**
     * Get the logs for the project.
     */
    public function logs()
    {
        return $this->hasMany(ProjectLog::class, 'project_id');
    }
}
