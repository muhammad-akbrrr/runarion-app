<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

class PipelineRun extends Model
{
    use HasUlids, SoftDeletes;

    public const STATUS_PENDING = 'pending';

    public const STATUS_PHASE_1_2_RUNNING = 'phase_1_2_running';

    public const STATUS_PHASE_3_RUNNING = 'phase_3_running';

    public const STATUS_COMPLETED = 'completed';

    public const STATUS_FAILED = 'failed';

    public const IMPORT_STATUS_PENDING = 'pending';

    public const IMPORT_STATUS_RUNNING = 'running';

    public const IMPORT_STATUS_COMPLETED = 'completed';

    public const IMPORT_STATUS_FAILED = 'failed';

    public const IMPORT_STATUS_SKIPPED = 'skipped';

    protected $fillable = [
        'id',
        'draft_id',
        'workspace_id',
        'project_id',
        'user_id',
        'author_style_id',
        'author_name',
        'status',
        'current_phase',
        'phase_1_status',
        'phase_2_status',
        'phase_3_status',
        'config',
        'error_message',
        'failed_phase',
        'started_at',
        'completed_at',
        'metadata',
        'import_status',
        'import_error_message',
        'imported_at',
        'project_snapshot_id',
    ];

    protected $casts = [
        'user_id' => 'integer',
        'current_phase' => 'integer',
        'failed_phase' => 'integer',
        'config' => 'array',
        'metadata' => 'array',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
        'imported_at' => 'datetime',
    ];

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function workspace(): BelongsTo
    {
        return $this->belongsTo(Workspace::class);
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    public function authorStyle(): BelongsTo
    {
        return $this->belongsTo(AuthorStyle::class);
    }

    public function snapshot(): BelongsTo
    {
        return $this->belongsTo(ProjectSnapshot::class, 'project_snapshot_id');
    }

    public function isTerminal(): bool
    {
        return in_array($this->status, [
            self::STATUS_COMPLETED,
            self::STATUS_FAILED,
        ], true);
    }

    public function isImportPending(): bool
    {
        return $this->status === self::STATUS_COMPLETED
            && $this->import_status !== self::IMPORT_STATUS_COMPLETED;
    }
}
