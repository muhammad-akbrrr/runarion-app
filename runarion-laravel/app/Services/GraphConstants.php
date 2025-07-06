<?php

namespace App\Services;

class GraphConstants
{
    // Vertex Labels
    public const VERTEX_CHARACTER = 'Character';
    public const VERTEX_LOCATION = 'Location';
    public const VERTEX_ITEM = 'Item';
    public const VERTEX_THEME = 'Theme';
    public const VERTEX_PLOT_POINT = 'PlotPoint';
    public const VERTEX_SCENE = 'Scene';
    public const VERTEX_DRAFT = 'Draft';

    // Edge Labels - Character Relationships
    public const EDGE_APPEARS_IN = 'APPEARS_IN';
    public const EDGE_INTERACTS_WITH = 'INTERACTS_WITH';
    public const EDGE_KNOWS = 'KNOWS';
    public const EDGE_LOVES = 'LOVES';
    public const EDGE_HATES = 'HATES';
    public const EDGE_FOLLOWS = 'FOLLOWS';
    public const EDGE_LEADS = 'LEADS';

    // Edge Labels - Location Relationships
    public const EDGE_LOCATED_IN = 'LOCATED_IN';
    public const EDGE_TRAVELS_TO = 'TRAVELS_TO';
    public const EDGE_CONTAINS = 'CONTAINS';

    // Edge Labels - Item Relationships
    public const EDGE_OWNS = 'OWNS';
    public const EDGE_USES = 'USES';
    public const EDGE_FINDS = 'FINDS';
    public const EDGE_LOSES = 'LOSES';
    public const EDGE_GIVES = 'GIVES';
    public const EDGE_TAKES = 'TAKES';

    // Edge Labels - Theme Relationships
    public const EDGE_REPRESENTS = 'REPRESENTS';
    public const EDGE_SYMBOLIZES = 'SYMBOLIZES';
    public const EDGE_EMBODIES = 'EMBODIES';

    // Edge Labels - Plot Relationships
    public const EDGE_CAUSES = 'CAUSES';
    public const EDGE_LEADS_TO = 'LEADS_TO';
    public const EDGE_PREVENTS = 'PREVENTS';
    public const EDGE_RESOLVES = 'RESOLVES';
    public const EDGE_CONFLICTS_WITH = 'CONFLICTS_WITH';

    // Edge Labels - Scene Relationships
    public const EDGE_HAPPENS_IN = 'HAPPENS_IN';
    public const EDGE_PRECEDES = 'PRECEDES';
    public const EDGE_FOLLOWS_FROM = 'FOLLOWS_FROM';

    // Edge Labels - Draft Relationships
    public const EDGE_BELONGS_TO = 'BELONGS_TO';
    public const EDGE_DERIVED_FROM = 'DERIVED_FROM';

    // Entity Types for Metadata
    public const ENTITY_CHARACTER = 'character';
    public const ENTITY_LOCATION = 'location';
    public const ENTITY_ITEM = 'item';
    public const ENTITY_THEME = 'theme';
    public const ENTITY_PLOT_POINT = 'plot_point';

    public static function getVertexLabels(): array
    {
        return [
            self::VERTEX_CHARACTER,
            self::VERTEX_LOCATION,
            self::VERTEX_ITEM,
            self::VERTEX_THEME,
            self::VERTEX_PLOT_POINT,
            self::VERTEX_SCENE,
            self::VERTEX_DRAFT,
        ];
    }

    public static function getEdgeLabels(): array
    {
        return [
            // Character relationships
            self::EDGE_APPEARS_IN,
            self::EDGE_INTERACTS_WITH,
            self::EDGE_KNOWS,
            self::EDGE_LOVES,
            self::EDGE_HATES,
            self::EDGE_FOLLOWS,
            self::EDGE_LEADS,

            // Location relationships
            self::EDGE_LOCATED_IN,
            self::EDGE_TRAVELS_TO,
            self::EDGE_CONTAINS,

            // Item relationships
            self::EDGE_OWNS,
            self::EDGE_USES,
            self::EDGE_FINDS,
            self::EDGE_LOSES,
            self::EDGE_GIVES,
            self::EDGE_TAKES,

            // Theme relationships
            self::EDGE_REPRESENTS,
            self::EDGE_SYMBOLIZES,
            self::EDGE_EMBODIES,

            // Plot relationships
            self::EDGE_CAUSES,
            self::EDGE_LEADS_TO,
            self::EDGE_PREVENTS,
            self::EDGE_RESOLVES,
            self::EDGE_CONFLICTS_WITH,

            // Scene relationships
            self::EDGE_HAPPENS_IN,
            self::EDGE_PRECEDES,
            self::EDGE_FOLLOWS_FROM,

            // Draft relationships
            self::EDGE_BELONGS_TO,
            self::EDGE_DERIVED_FROM,
        ];
    }

    public static function getEntityTypes(): array
    {
        return [
            self::ENTITY_CHARACTER => 'Character',
            self::ENTITY_LOCATION => 'Location',
            self::ENTITY_ITEM => 'Item',
            self::ENTITY_THEME => 'Theme',
            self::ENTITY_PLOT_POINT => 'Plot Point',
        ];
    }
}