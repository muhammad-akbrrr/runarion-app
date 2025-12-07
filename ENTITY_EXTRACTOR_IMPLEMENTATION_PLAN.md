# Entity Extractor Implementation Plan

## Overview
Entity Extractor automatically extracts entities from manuscript content using the same logic as deconstructor's Stage 4B, but adapted for proactive writing (manuscript chapters instead of scenes).

## Key Features

### 1. Category Selection
- **All Categories**: Process all system + custom categories sequentially
- **Select Categories**: Choose specific categories to extract
- **Exclude Record Keeper**: Record Keeper is NOT a category for extraction

### 2. Dynamic Field Support
- **System Categories**: Use predefined baseline fields (character, location, item, theme, plot_point)
- **Custom Categories**: Use field schemas from `record_entity_types.field_schema`
- **LLM Extraction**: LLM extracts information based on field schemas dynamically

### 3. Extraction Process
- **Input**: All chapters from manuscript (combined or progressive)
- **Output**: Entities created/updated in graph database with properties
- **Conflict Resolution**: Ask user (merge/skip/replace) - future feature

### 4. Implementation Details

#### Backend (Python)
1. **Get Collection Types**: Query `record_entity_types` table for categories + field schemas
2. **Build Dynamic Prompt**: 
   - Use deconstructor's `get_graph_analysis_prompt()` as base
   - Add field schema information for each category
   - Instruct LLM to extract based on field schemas
3. **Extract Entities**: 
   - Combine all chapters (or use progressive approach)
   - Run LLM extraction for each category
   - Parse JSON response using `parse_graph_analysis_response()`
4. **Store Entities**:
   - Use `RecordsManager.create_entity()` or `update_entity()`
   - Map extracted properties to entity properties
   - Handle custom fields dynamically

#### Frontend (React)
1. **UI Component**: Similar to SummarizerTab
   - Category selection (All Categories or select specific)
   - Chapter selection (optional - usually all)
   - Start extraction button
2. **API Integration**: Call `/api/auditor/extract` endpoint

#### API Endpoint
- `POST /api/auditor/extract`
- Parameters:
  - `project_id`: Required
  - `workspace_id`: Required (for content retrieval)
  - `categories`: Array of category names or "all_categories"
  - `chapter_orders`: Optional (default: all chapters)
  - `model`: AI model to use
  - `provider`: AI provider

## Flow

1. User selects categories (All or specific)
2. System gets collection types + field schemas from database
3. System combines all chapters into manuscript text
4. For each category:
   - Build extraction prompt with field schema
   - Run LLM extraction
   - Parse response
   - Create/update entities in graph
5. Return results (entities created/updated per category)

## Dynamic Field Schema Example

For custom category "Faction" with fields:
```json
[
  {"name": "leader", "type": "text", "label": "Leader"},
  {"name": "members", "type": "array", "label": "Members"},
  {"name": "territory", "type": "text", "label": "Territory"}
]
```

The LLM will extract:
```json
{
  "factions": [
    {
      "name": "The Red Guard",
      "leader": "Commander Thorne",
      "members": ["Soldier A", "Soldier B"],
      "territory": "Northern Wastelands"
    }
  ]
}
```

## Next Steps After Entity Extractor

1. **Category Summaries**: Once entities are extracted, can summarize them chapter-by-chapter
2. **Sentiment Analyzer**: Extract relationships and calculate sentiment scores
3. **Conflict Resolution UI**: Handle merge/skip/replace when entities already exist

