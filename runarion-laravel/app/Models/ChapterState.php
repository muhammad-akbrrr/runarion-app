<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;

class ChapterState extends Model
{
    use HasUlids;

    protected $fillable = [
        'project_id',
        'chapter_order',
        'current_node_id',
        'current_version_index',
    ];

    protected $casts = [
        'updated_at' => 'datetime',
    ];

    public $timestamps = false;

    public function project()
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    public function currentNode()
    {
        return $this->belongsTo(ContentNode::class, 'current_node_id');
    }

    protected static function boot()
    {
        parent::boot();

        static::creating(function ($model) {
            $model->updated_at = now();
        });

        static::updating(function ($model) {
            $model->updated_at = now();
        });
    }
}
