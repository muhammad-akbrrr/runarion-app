<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class ProjectSnapshot extends Model
{
    use HasUlids, SoftDeletes;

    public const KIND_ANCHOR = 'anchor';

    public const KIND_MANUAL = 'manual';

    public const KIND_AUTOSAVE = 'autosave';

    public const KIND_PRE_RESTORE = 'pre_restore';

    public const KIND_PIPELINE_IMPORT = 'pipeline_import';

    protected $fillable = [
        'project_id',
        'name',
        'description',
        'snapshot_kind',
        'is_immutable',
        'source_snapshot_id',
        'schema_version',
        'state_hash',
        'snapshot_data',
        'created_by',
    ];

    protected $casts = [
        'is_immutable' => 'boolean',
        'schema_version' => 'integer',
        'snapshot_data' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
        'deleted_at' => 'datetime',
    ];

    public function project()
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    public function creator()
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function sourceSnapshot()
    {
        return $this->belongsTo(self::class, 'source_snapshot_id');
    }
}
