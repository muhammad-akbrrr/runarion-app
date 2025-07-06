<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use App\Services\GraphConstants;

class NovelGraphEdge extends Model
{
    use HasFactory;

    protected $table = 'novel_graph_edges';

    protected $fillable = [
        'draft_id',
        'scene_id',
        'source_vertex_id',
        'target_vertex_id',
        'edge_id',
        'edge_label',
        'properties',
    ];

    protected $casts = [
        'properties' => 'array',
    ];

    public const LABEL_APPEARS_IN = GraphConstants::EDGE_APPEARS_IN;
    public const LABEL_INTERACTS_WITH = GraphConstants::EDGE_INTERACTS_WITH;
    public const LABEL_LOCATED_IN = GraphConstants::EDGE_LOCATED_IN;
    public const LABEL_OWNS = GraphConstants::EDGE_OWNS;
    public const LABEL_USES = GraphConstants::EDGE_USES;
    public const LABEL_KNOWS = GraphConstants::EDGE_KNOWS;
    public const LABEL_LOVES = GraphConstants::EDGE_LOVES;
    public const LABEL_HATES = GraphConstants::EDGE_HATES;
    public const LABEL_CAUSES = GraphConstants::EDGE_CAUSES;
    public const LABEL_LEADS_TO = GraphConstants::EDGE_LEADS_TO;

    public static function getLabelOptions(): array
    {
        $labels = GraphConstants::getEdgeLabels();
        $options = [];
        
        foreach ($labels as $label) {
            $options[$label] = ucwords(str_replace('_', ' ', strtolower($label)));
        }
        
        return $options;
    }

    public function draft(): BelongsTo
    {
        return $this->belongsTo(Draft::class);
    }

    public function scene(): BelongsTo
    {
        return $this->belongsTo(Scene::class);
    }

    public function sourceVertex(): BelongsTo
    {
        return $this->belongsTo(NovelGraphVertex::class, 'source_vertex_id', 'vertex_id');
    }

    public function targetVertex(): BelongsTo
    {
        return $this->belongsTo(NovelGraphVertex::class, 'target_vertex_id', 'vertex_id');
    }
}