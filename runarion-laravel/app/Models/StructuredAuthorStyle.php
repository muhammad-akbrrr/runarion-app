<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\Rule;

class StructuredAuthorStyle extends Model
{
    use HasUlids;

    protected $fillable = [
        'workspace_id',
        'project_id',
        'user_id',
        'author_name',
        'style',
        'sources',
        'started_at',
        'total_time_ms',
    ];

    protected $casts = [
        'user_id' => 'integer',
        'style' => 'array',
        'started_at' => 'datetime',
        'total_time_ms' => 'integer',
    ];

    public static function rules(): array
    {
        return [
            'workspace_id' => ['required', 'ulid'],
            'project_id' => ['required', 'ulid'],
            'user_id' => ['required', 'integer'],
            'author_name' => ['required', 'string', Rule::unique('structured_author_styles')->where(function ($query) {
                return $query->where('workspace_id', request()->input('workspace_id'));
            })],
            'style' => ['required', 'array'],
            'sources' => ['required', 'string'],
            'started_at' => ['required', 'datetime'],
            'total_time_ms' => ['required', 'integer'],
        ];
    }
}
