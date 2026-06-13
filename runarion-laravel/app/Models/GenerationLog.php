<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

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
        'usecase',
        'feature',
        'token_basis',
        'workspace_usage_period_id',
        'quota_mode',
        'workflow_id',
        'prompt',
        'instruction',
        'generated_text',
        'success',
        'finish_reason',
        'input_tokens',
        'output_tokens',
        'reasoning_tokens',
        'total_tokens',
        'billable_input_tokens',
        'billable_output_tokens',
        'billable_reasoning_tokens',
        'billable_total_tokens',
        'reserved_tokens',
        'usage_source',
        'processing_time_ms',
        'error_message',
        'created_at',
    ];

    protected $casts = [
        'success' => 'boolean',
        'input_tokens' => 'integer',
        'output_tokens' => 'integer',
        'reasoning_tokens' => 'integer',
        'total_tokens' => 'integer',
        'billable_input_tokens' => 'integer',
        'billable_output_tokens' => 'integer',
        'billable_reasoning_tokens' => 'integer',
        'billable_total_tokens' => 'integer',
        'reserved_tokens' => 'integer',
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
            'usecase' => ['nullable', 'string'],
            'feature' => ['nullable', 'string'],
            'token_basis' => ['nullable', 'string'],
            'workspace_usage_period_id' => ['nullable', 'uuid'],
            'quota_mode' => ['nullable', 'string'],
            'workflow_id' => ['nullable', 'string'],
            'prompt' => ['nullable', 'string'],
            'instruction' => ['nullable', 'string'],
            'generated_text' => ['nullable', 'string'],
            'success' => ['required', 'boolean'],
            'finish_reason' => ['nullable', 'string'],
            'input_tokens' => ['nullable', 'integer'],
            'output_tokens' => ['nullable', 'integer'],
            'reasoning_tokens' => ['nullable', 'integer'],
            'total_tokens' => ['nullable', 'integer'],
            'billable_input_tokens' => ['nullable', 'integer'],
            'billable_output_tokens' => ['nullable', 'integer'],
            'billable_reasoning_tokens' => ['nullable', 'integer'],
            'billable_total_tokens' => ['nullable', 'integer'],
            'reserved_tokens' => ['nullable', 'integer'],
            'usage_source' => ['nullable', 'string'],
            'processing_time_ms' => ['nullable', 'integer'],
            'error_message' => ['nullable', 'string'],
        ];
    }
}
