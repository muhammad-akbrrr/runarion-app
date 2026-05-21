<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Concerns\HasUlids;

class ContentNode extends Model
{
    use HasUlids;

    protected $fillable = [
        'project_id',
        'chapter_order',
        'parent_node_id',
        'parent_version_index',
        'content',
        'generation_settings',
        'is_user_generated',
    ];

    protected $casts = [
        'generation_settings' => 'array',
        'is_user_generated' => 'boolean',
        'created_at' => 'datetime',
    ];

    public $timestamps = false;

    public function versions()
    {
        return $this->hasMany(ContentVersion::class, 'node_id')->orderBy('version_index');
    }

    public function parentNode()
    {
        return $this->belongsTo(ContentNode::class, 'parent_node_id');
    }

    public function childNodes()
    {
        return $this->hasMany(ContentNode::class, 'parent_node_id');
    }

    public function project()
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    protected static function boot()
    {
        parent::boot();
        
        static::creating(function ($model) {
            $model->created_at = now();
        });
    }
}
