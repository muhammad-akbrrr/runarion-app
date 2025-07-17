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
        'techniques_json',
        'examples_json',
        'status',
        'error_message',
        'started_at',
        'total_time_ms',
    ];

    protected $casts = [
        'user_id' => 'integer',
        'techniques_json' => 'array',
        'examples_json' => 'array',
        'status' => 'string',
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
            'techniques_json' => ['nullable', 'array'],
            'examples_json' => ['nullable', 'array'],
            'status' => ['required', 'string', Rule::in([
                'init_completed', 
                'sampling_completed', 
                'sampling_failed', 
                'profiling_completed', 
            ])],
            'error_message' => ['nullable', 'string'],
            'started_at' => ['required', 'datetime'],
            'total_time_ms' => ['nullable', 'integer'],
        ];
    }
}
