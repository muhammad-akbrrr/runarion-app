<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Concerns\HasUlids;

class ContentVersion extends Model
{
    use HasUlids;

    protected $fillable = [
        'node_id',
        'version_index',
        'content',
    ];

    protected $casts = [
        'created_at' => 'datetime',
    ];

    public $timestamps = false;

    public function node()
    {
        return $this->belongsTo(ContentNode::class, 'node_id');
    }

    protected static function boot()
    {
        parent::boot();
        
        static::creating(function ($model) {
            $model->created_at = now();
        });
    }
}
