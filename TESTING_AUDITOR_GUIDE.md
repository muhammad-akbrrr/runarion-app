# Testing Guide: Auditor/Summarizer Feature

## ✅ What's Built

### Backend (Python)
- ✅ `AuditorService` - Analyzes chapters and creates Record Keeper entries
- ✅ API endpoint: `POST /api/auditor/summarize`
- ✅ Fetches chapters with version control support
- ✅ Creates Record Keeper entries in Apache AGE graph database
- ✅ Handles custom fields/categories dynamically (LLM extracts any relevant info)

### Frontend (Laravel/React)
- ✅ Auditor Tab UI with model selection
- ✅ Summarizer Tab with Record Keeper as primary feature
- ✅ Category selection (optional, supplementary)
- ✅ Chapter selection (all or specific)
- ✅ Summary Tab in Entity Detail Sidebar
- ✅ Integration with Records System

## 🧪 Testing Steps

### 1. **Prerequisites Check**
```bash
# Ensure services are running
docker compose ps

# Check Python service is accessible
curl http://localhost:5000/health

# Check Laravel service
curl http://localhost:8000/health
```

### 2. **Test Basic Flow**

#### Step 1: Open Project Editor
1. Navigate to a project with chapters
2. Click on "Database" tab in the sidebar
3. Verify you can see the Records Panel

#### Step 2: Open Auditor Tab
1. Click on "Auditor" tab in the sidebar
2. **FIXED**: Should no longer show white screen
3. Verify you see:
   - Model selection dropdown (Gemini models)
   - Three tabs: Summarizer, Entity Extractor, Sentiment Analyzer

#### Step 3: Test Summarizer
1. Click "Summarizer" tab
2. Verify you see:
   - Record Keeper Summary section (highlighted in blue)
   - Category dropdown (optional)
   - Chapter selection
   - "Start Summarization" button

#### Step 4: Run Summarization
1. Select chapters (or leave "All Chapters" checked)
2. Optionally select a category (Character, Location, etc.)
3. Click "Start Summarization"
4. Confirm the dialog
5. Wait for completion (check browser console for errors)

#### Step 5: Verify Record Keeper Entries
1. Go to Database → Records Panel
2. Select "Record Keeper" from the type dropdown
3. Verify you see entries for each chapter:
   - Chapter number
   - Chapter title
   - Summary
   - Character activity
   - Key events
   - Themes mentioned
   - Locations mentioned

#### Step 6: Test Custom Categories
1. Create a custom category (e.g., "Faction")
2. Add custom fields to that category
3. Run summarization
4. Verify the LLM extracts information about your custom category
5. Check if custom entities are created in the graph

### 3. **Test Custom Fields Handling**

#### Custom Category Test
1. Create a custom category "Faction" with fields:
   - `leader` (text)
   - `members` (array)
   - `territory` (text)
2. Write content in your manuscript mentioning factions
3. Run summarization
4. Verify:
   - Record Keeper entries are created (always)
   - If you selected "Faction" category, entities are extracted
   - Custom fields are populated correctly

#### Custom Fields in Standard Categories
1. Create a Character entity manually
2. Add custom fields (e.g., `magic_power`, `faction_allegiance`)
3. Run summarization for "Character" category
4. Verify custom fields are preserved and updated

### 4. **Test Graph Database Integration**

#### Verify Apache AGE Connection
```sql
-- Connect to PostgreSQL
docker compose exec postgres psql -U runarion_user -d runarion_db

-- Check if Record Keeper entries exist
SELECT * FROM ag_catalog.cypher('novel_pipeline_graph', $$
  MATCH (n:RecordKeeper)
  RETURN n.name, n.properties
  LIMIT 5
$$) AS (result agtype);
```

#### Verify Metadata Tables
```sql
-- Check novel_graph_vertices
SELECT entity_type, entity_name, vertex_id 
FROM novel_graph_vertices 
WHERE entity_type = 'record_keeper' 
LIMIT 5;
```

### 5. **Test Error Handling**

#### Test Empty Chapters
1. Create a project with no chapters
2. Try to run summarization
3. Should show error: "No chapters found for this project"

#### Test Invalid Model
1. Try to use an invalid model (should be prevented by UI)
2. Verify error handling

#### Test Network Errors
1. Stop Python service
2. Try to run summarization
3. Should show error message

### 6. **Test Summary Tab**

1. Open an entity (Character, Location, etc.)
2. Click "Summary" tab
3. If summaries exist, verify chapter-by-chapter activity
4. If no summaries, verify helpful message appears

## 🔍 Debugging

### Check Python Logs
```bash
docker compose logs python-app --tail=100
```

### Check Laravel Logs
```bash
docker compose logs laravel-app --tail=100
```

### Check Browser Console
- Open DevTools (F12)
- Check Console tab for errors
- Check Network tab for failed API calls

### Common Issues

#### White Screen in Auditor Tab
- ✅ **FIXED**: Added missing `allEntities` prop to EntityDetailSidebarProps

#### "No chapters found"
- Verify project has chapters in `project_content` table
- Check chapter structure: `[{order: 0, chapter_name: "...", content: "..."}]`

#### "Failed to analyze chapter"
- Check Python logs for LLM errors
- Verify Gemini API key is set
- Check chapter content length (needs > 100 chars)

#### Record Keeper entries not appearing
- Check if entries were created in graph database
- Verify `novel_graph_vertices` table has entries
- Check entity type filter in Records Panel

## 📝 Expected Behavior

### Record Keeper (Primary Feature)
- ✅ Always created for all selected chapters
- ✅ Contains: summary, character_activity, key_events, themes_mentioned, locations_mentioned
- ✅ Stored in Apache AGE graph database
- ✅ Visible in Database → Record Keeper collection type

### Entity Summaries (Supplementary)
- ⏳ TODO: Not yet implemented
- Will update entity properties with `_summaries` array
- Visible in Summary tab when opening an entity

### Custom Categories/Fields
- ✅ LLM extracts any relevant information
- ✅ Custom entities can be created
- ✅ Custom fields are preserved in properties
- ✅ Works with both system and custom categories

## ✅ Success Criteria

1. ✅ Auditor tab opens without white screen
2. ✅ Summarizer UI displays correctly
3. ✅ Can select chapters and categories
4. ✅ Summarization completes successfully
5. ✅ Record Keeper entries are created in graph
6. ✅ Entries are visible in Records Panel
7. ✅ Custom categories/fields are handled correctly
8. ✅ All data stored in Apache AGE graph database

## 🚀 Next Steps (After Testing)

1. Implement entity-specific summarization (Summary tab content)
2. Add background job processing with progress tracking
3. Add Entity Extractor feature
4. Add Sentiment Analyzer feature
5. Add conflict resolution UI

