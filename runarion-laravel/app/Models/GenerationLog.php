<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Concerns\HasUuids;

class GenerationLog extends Model
{
    use HasFactory, HasUuids;

    protected $primaryKey = 'request_id';
    public $incrementing = false;
    protected $keyType = 'string';

    protected $fillable = [
        'request_id',
        'provider_request_id',
        'user_id',
        'workspace_id',
        'project_id',
        'provider',
        'model_used',
        'key_used',
        'prompt',
        'instruction',
        'generated_text',
        'success',
        'finish_reason',
        'input_tokens',
        'output_tokens',
        'total_tokens',
        'processing_time_ms',
        'error_message',
        'created_at',
    ];

    protected $casts = [
        'success' => 'boolean',
        'input_tokens' => 'integer',
        'output_tokens' => 'integer',
        'total_tokens' => 'integer',
        'processing_time_ms' => 'integer',
        'created_at' => 'datetime',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function workspace()
    {
        return $this->belongsTo(Workspace::class, 'workspace_id');
    }

    public function project()
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    public static function rules(): array
    {
        return [
            'request_id' => ['required', 'uuid'],
            'user_id' => ['required', 'exists:users,id'],
            'workspace_id' => ['nullable', 'ulid', 'exists:workspaces,id'],
            'project_id' => ['nullable', 'ulid', 'exists:projects,id'],
            'provider_request_id' => ['nullable', 'string'],
            'provider' => ['nullable', 'string'],
            'model_used' => ['nullable', 'string'],
            'key_used' => ['nullable', 'string'],
            'prompt' => ['nullable', 'string'],
            'instruction' => ['nullable', 'string'],
            'generated_text' => ['nullable', 'string'],
            'success' => ['required', 'boolean'],
            'finish_reason' => ['nullable', 'string'],
            'input_tokens' => ['nullable', 'integer'],
            'output_tokens' => ['nullable', 'integer'],
            'total_tokens' => ['nullable', 'integer'],
            'processing_time_ms' => ['nullable', 'integer'],
            'error_message' => ['nullable', 'string'],
        ];
    }
}
