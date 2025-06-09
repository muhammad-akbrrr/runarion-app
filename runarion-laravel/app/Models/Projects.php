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
        'name',
        'slug',
        'settings',
        'category',
        'saved_in',
        'description',
        'access',
        'is_active',
    ];

    protected $casts = [
        'settings' => 'array',
        'access' => 'array',
        'is_active' => 'boolean',
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
            'folder_id' => ['nullable', 'ulid', 'exists:folders,id'],
            'name' => ['required', 'string', 'max:255'],
            'slug' => ['required', 'string', 'max:255', 'unique:projects,slug'],
            'settings' => ['nullable', 'array'],
            'category' => ['nullable', 'string', Rule::in(['horror', 'sci-fi', 'fantasy', 'romance', 'thriller', 'mystery', 'adventure', 'comedy', 'dystopian', 'crime', 'fiction', 'biography', 'historical'])],
            'saved_in' => ['required', 'string', 'size:2', Rule::in(['01', '02', '03', '04'])],
            'description' => ['nullable', 'string'],
            'access' => ['nullable', 'array'],
            'access.*.user.id' => ['required', 'ulid', 'exists:users,id'],
            'access.*.user.name' => ['required', 'string'],
            'access.*.user.email' => ['required', 'email'],
            'access.*.user.avatar_url' => ['nullable', 'string', 'url'],
            'access.*.role' => ['required', 'string', Rule::in(['editor', 'manager', 'admin'])],
            'is_active' => ['boolean'],
        ];
    }

    /**
     * Validate that users in access array are members of the workspace
     */
    public function validateAccess(): bool
    {
        if (!$this->access) {
            return true;
        }

        $workspaceMemberIds = WorkspaceMember::where('workspace_id', $this->workspace_id)
            ->pluck('user_id')
            ->toArray();

        foreach ($this->access as $access) {
            if (!in_array($access['user']['id'], $workspaceMemberIds)) {
                return false;
            }
        }

        return true;
    }
}
