<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class ProjectOperation extends Model
{
    use HasUlids, SoftDeletes;

    public const TYPE_SNAPSHOT_RESTORE = 'snapshot_restore';

    public const STATUS_PENDING = 'pending';

    public const STATUS_RUNNING = 'running';

    public const STATUS_COMPLETED = 'completed';

    public const STATUS_FAILED = 'failed';

    protected $fillable = [
        'workspace_id',
        'project_id',
        'operation_type',
        'status',
        'phase',
        'message',
        'metadata',
        'created_by',
        'started_at',
        'completed_at',
    ];

    protected $casts = [
        'metadata' => 'array',
        'created_by' => 'integer',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
        'deleted_at' => 'datetime',
    ];

    public function isLocked(): bool
    {
        return in_array($this->status, [
            self::STATUS_PENDING,
            self::STATUS_RUNNING,
        ], true);
    }
}
