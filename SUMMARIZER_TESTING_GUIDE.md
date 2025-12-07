# Summarizer Testing Guide

## Overview

The Summarizer feature has two main components:
1. **Record Keeper Summaries** - Chapter-by-chapter summaries stored as Record Keeper entities
2. **Category Summaries** - Entity-specific summaries that update entity properties with `_summaries` array

## What Was Fixed

### Content Retrieval
- **Fixed**: Python service now uses Laravel endpoint as PRIMARY method when `workspace_id` is available
- **Why**: Laravel endpoint properly handles version control and returns current editor content
- **Fallback**: Database queries only used if Laravel endpoint unavailable

### UI Improvements
- **Record Keeper Toggle**: Can now enable/disable Record Keeper independently
- **All Categories Option**: Can process all categories sequentially
- **Flexible Selection**: Can do Record Keeper only, Category only, or both

## Test 1: Record Keeper Summaries

### Purpose
Verify that Record Keeper entries are created correctly with chapter summaries.

### Prerequisites
- Project with at least 2-3 chapters
- Chapters have content written in the editor (not just empty)
- Content should be substantial (> 100 characters per chapter)

### Steps

1. **Open Project Editor**
   - Navigate to a project with chapters
   - Click "Auditor" tab in sidebar
   - Click "Summarizer" tab

2. **Configure Record Keeper Only**
   - ✅ Enable "Record Keeper Summary" toggle (should be enabled by default)
   - Select "None (Record Keeper only)" from Category dropdown
   - Select "All Chapters" or specific chapters
   - Click "Start Summarization"

3. **Verify Results**
   - Wait for completion (check browser console for errors)
   - Should see success message with:
     - Number of Record Keeper entries created
     - Number of entries updated (if re-running)
   - Go to "Database" → "Records Panel"
   - Select "Record Keeper" from type dropdown
   - Verify entries exist for each processed chapter

4. **Check Record Keeper Entry Content**
   - Click on a Record Keeper entry
   - Verify it has:
     - `chapter_number` - Chapter number
     - `chapter_title` - Chapter name
     - `summary` - Comprehensive chapter summary
     - `character_activity` - Array of character actions
     - `key_events` - Array of key events
     - `themes_mentioned` - Array of themes
     - `locations_mentioned` - Array of locations

5. **Test Re-running**
   - Run summarization again on same chapters
   - Should see "Updated" count instead of "Created"
   - Verify content is refreshed/updated

### Expected Results
- ✅ Record Keeper entries created for all selected chapters
- ✅ Each entry contains comprehensive chapter analysis
- ✅ Entries visible in Records Panel
- ✅ Re-running updates existing entries

### Troubleshooting
- **"No content" errors**: Check that chapters have content in editor (not just in database)
- **"Content too short"**: Ensure chapters have > 100 characters
- **No entries created**: Check Python logs for LLM errors or API key issues

---

## Test 2: Category Summaries

### Purpose
Verify that entity-specific summaries are generated and stored in entity properties.

### Prerequisites
- Project with chapters containing entities (Characters, Locations, Items, etc.)
- At least some entities already exist in Records System (or will be created)
- Chapters reference these entities

### Steps

#### Test 2A: Single Category - All Entities

1. **Configure Category Summarization**
   - Enable/disable Record Keeper as desired
   - Select a category (e.g., "Character")
   - Select "All [Category]s" mode
   - Select chapters to process
   - Click "Start Summarization"

2. **Verify Results**
   - Wait for completion
   - Go to "Database" → "Records Panel"
   - Select the category (e.g., "Character")
   - Open an entity that appears in the processed chapters
   - Click "Summary" tab
   - Verify chapter-by-chapter activity summaries appear

3. **Check Entity Properties**
   - In entity Details tab, check properties
   - Should see `_summaries` array property
   - Each entry should have:
     - `chapter_number`
     - `chapter_title`
     - `activity` - What the entity did in that chapter
     - `significance` - Entity's role/importance in chapter

#### Test 2B: Single Category - Focused (Selected Entities)

1. **Configure Focused Mode**
   - Select a category
   - Select "Focused (Select Specific)" mode
   - Check specific entities to analyze
   - Select chapters
   - Click "Start Summarization"

2. **Verify Results**
   - Only selected entities should have summaries updated
   - Other entities in same category should be unchanged

#### Test 2C: All Categories

1. **Configure All Categories**
   - Enable/disable Record Keeper as desired
   - Select "All Categories" from Category dropdown
   - Select chapters
   - Click "Start Summarization"

2. **Verify Results**
   - All categories should be processed sequentially
   - Check entities from different categories:
     - Characters
     - Locations
     - Items
     - Custom categories (if any)
   - Each should have summaries updated

#### Test 2D: Custom Categories (Dynamic)

1. **Create Custom Category**
   - Go to "Database" → "Records Panel"
   - Create a custom collection type (e.g., "Faction")
   - Add custom fields to the category schema

2. **Create Entities**
   - Create entities of the custom type
   - Or let summarization create them automatically

3. **Run Summarization**
   - Select the custom category (e.g., "Faction")
   - Run summarization
   - Verify:
     - Custom entities are created/updated
     - Custom fields are populated
     - Summaries work the same as system categories

### Expected Results
- ✅ Entity summaries created/updated in `_summaries` property
- ✅ Summary tab displays chapter-by-chapter activity
- ✅ Works with all system categories
- ✅ Works with custom categories dynamically
- ✅ Focused mode only updates selected entities
- ✅ All Categories mode processes all categories

### Troubleshooting
- **No summaries appearing**: Check that entities actually appear in chapters
- **Custom category not working**: Verify category name matches exactly (case-insensitive)
- **Summary tab empty**: Check that `_summaries` property exists on entity

---

## Test 3: Combined Mode

### Purpose
Test Record Keeper + Category summaries running together.

### Steps

1. **Enable Both**
   - ✅ Enable Record Keeper toggle
   - Select a category (e.g., "Character")
   - Select "All Characters" mode
   - Run summarization

2. **Verify Both**
   - Check Record Keeper entries created
   - Check Character entity summaries updated
   - Both should work independently

---

## Test 4: Edge Cases

### Test 4A: Record Keeper Disabled, Category Only
- Disable Record Keeper
- Select a category
- Verify only category summaries are created

### Test 4B: No Options Selected
- Disable Record Keeper
- Select "None" category
- Should show error: "Please enable at least one option"

### Test 4C: Empty Chapters
- Select chapters with no content
- Should show errors for those chapters
- Other chapters should still process

### Test 4D: Very Long Chapters
- Test with chapters > 10,000 words
- Should process successfully (may take longer)

---

## What Gets Summarized

### Record Keeper
For each chapter:
- **Summary**: Comprehensive overview of chapter events
- **Character Activity**: What each character did/said/experienced
- **Key Events**: Major plot developments
- **Themes Mentioned**: Thematic elements
- **Locations Mentioned**: Places referenced

### Category Summaries
For each entity in selected category:
- **Chapter-by-chapter activity**: How entity appears in each chapter
- **Significance**: Entity's role/importance per chapter
- **Properties**: Any relevant entity properties extracted from text
- **Custom Fields**: If custom category, custom fields are populated dynamically

### Dynamic Custom Categories
- System automatically detects custom categories
- LLM extracts information based on category schema
- Works with any custom fields you define
- No code changes needed for new categories

---

## Success Criteria

### Record Keeper Test
- ✅ Entries created for all selected chapters
- ✅ Content is comprehensive and accurate
- ✅ Visible in Records Panel
- ✅ Re-running updates existing entries

### Category Summaries Test
- ✅ Entity summaries created/updated
- ✅ Summary tab displays data
- ✅ Works with all categories (system + custom)
- ✅ Focused mode works correctly
- ✅ All Categories mode processes sequentially

---

## Next Steps After Testing

If tests pass:
1. ✅ Content retrieval is fixed
2. ✅ Record Keeper works independently
3. ✅ Category summaries work (when implemented)
4. ✅ UI supports all modes

If tests fail:
- Check Python logs: `docker compose logs python-app --tail=100`
- Check Laravel logs: `docker compose logs laravel-app --tail=100`
- Check browser console for errors
- Verify chapters have content in editor
- Verify API keys are set correctly

---

## Notes

- **Content Retrieval**: Now uses Laravel endpoint first (more reliable)
- **Record Keeper**: Can be toggled on/off independently
- **Categories**: Support single category, all categories, or none
- **Dynamic**: Custom categories work automatically without code changes
- **Progressive**: Uses progressive summaries across chapters (like deconstructor)

