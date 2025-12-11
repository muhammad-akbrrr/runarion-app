<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;
use App\Services\GraphConstants;

class NovelGraphVertex extends Model
{
    use HasFactory, SoftDeletes;

    protected $table = 'novel_graph_vertices';

    protected $fillable = [
        'draft_id',
        'project_id',
        'entity_type',
        'entity_name',
        'vertex_id',
        'vertex_label',
        'properties',
    ];

    protected $casts = [
        'properties' => 'array',
    ];

    public const TYPE_CHARACTER = GraphConstants::ENTITY_CHARACTER;
    public const TYPE_LOCATION = GraphConstants::ENTITY_LOCATION;
    public const TYPE_ITEM = GraphConstants::ENTITY_ITEM;
    public const TYPE_THEME = GraphConstants::ENTITY_THEME;
    public const TYPE_PLOT_POINT = GraphConstants::ENTITY_PLOT_POINT;

    public static function getTypeOptions(): array
    {
        return GraphConstants::getEntityTypes();
    }

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function outgoingEdges(): HasMany
    {
        return $this->hasMany(NovelGraphEdge::class, 'source_vertex_id', 'vertex_id');
    }

    public function incomingEdges(): HasMany
    {
        return $this->hasMany(NovelGraphEdge::class, 'target_vertex_id', 'vertex_id');
    }

    public function allEdges(): HasMany
    {
        return $this->hasMany(NovelGraphEdge::class, 'source_vertex_id', 'vertex_id')
            ->orWhere('target_vertex_id', $this->vertex_id);
    }
}