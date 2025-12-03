# Conversation History System - Testing Plan

## Overview
This document outlines the comprehensive testing strategy for the conversation history system implementation.

## Pre-Testing Checklist

### 1. Database Migration
- [ ] Run Laravel migration: `php artisan migrate`
- [ ] Verify `project_conversations` table created with correct schema
- [ ] Check JSONB column is properly configured

### 2. Code Verification
- [ ] All Python imports resolve correctly
- [ ] No syntax errors in new files
- [ ] Database connection pool accessible from generation API

## Testing Scenarios

### Phase 1: Unit Tests (Manual/Exploratory)

#### 1.1 ConversationManager Service Tests

**Test: Load empty history**
```python
# New project with no conversation history
project_id = "01HZ..."
messages = conversation_manager.load_history(project_id)
assert messages == []
```

**Test: Initialize conversation for new project**
```python
# Project exists but no conversation history
result = conversation_manager.initialize_conversation(
    project_id=project_id,
    prompt_config=PromptConfig(genre="fantasy"),
    initial_prompt="Once upon a time..."
)
assert result == True
messages = conversation_manager.load_history(project_id)
assert len(messages) > 0
```

**Test: Append user message**
```python
conversation_manager.append_message(
    project_id=project_id,
    role="user",
    content="Continue the story",
    chapter_order=1
)
messages = conversation_manager.load_history(project_id)
assert messages[-1]["role"] == "user"
assert messages[-1]["content"] == "Continue the story"
```

**Test: Append assistant message**
```python
conversation_manager.append_message(
    project_id=project_id,
    role="assistant",
    content="The hero continued...",
    chapter_order=1
)
messages = conversation_manager.load_history(project_id)
assert messages[-1]["role"] == "assistant"
```

**Test: Update chapter content in-place**
```python
# Update existing chapter message
conversation_manager.update_chapter_content(
    project_id=project_id,
    chapter_id=1,
    new_content="Updated chapter content"
)
messages = conversation_manager.load_history(project_id)
chapter_messages = [m for m in messages if m.get("chapter_id") == 1]
for msg in chapter_messages:
    assert "Updated chapter content" in msg["content"]
```

**Test: Convert to Gemini format**
```python
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there"}
]
gemini_format = conversation_manager.to_gemini_format(messages)
assert gemini_format[0]["role"] == "user"
assert gemini_format[1]["role"] == "model"  # Gemini uses "model" not "assistant"
```

#### 1.2 Error Handling Tests

**Test: Database connection failure - graceful fallback**
- Simulate DB pool unavailable
- Verify generation still works with prompt-only mode
- Check logs show warning, not error

**Test: Invalid project_id - graceful handling**
- Pass non-existent project_id
- Verify returns empty list, doesn't crash

**Test: Malformed JSONB data - graceful handling**
- Manually corrupt messages JSONB
- Verify load_history returns empty list, logs warning

### Phase 2: Integration Tests

#### 2.1 New Project Flow

**Scenario: First generation for new project**
1. Create new project (no existing chapters)
2. Generate Chapter 1 with prompt: "Write the opening scene"
3. Verify:
   - Conversation initialized in DB
   - User message saved
   - Assistant response saved after generation
   - Generation succeeds

**Test Command:**
```bash
# Via Laravel UI or API
# Project ID: [new project]
# Chapter Order: 0
# Prompt: "Write the opening scene of a fantasy story"
```

#### 2.2 Existing Project Flow

**Scenario: Second generation (Chapter 2 after Chapter 1 exists)**
1. Project has Chapter 1 already generated
2. Generate Chapter 2
3. Verify:
   - Conversation history loads Chapter 1
   - Gemini receives full conversation (Chapter 1 + new prompt)
   - Chapter 2 generation shows context awareness
   - Both messages saved correctly

**Test Command:**
```bash
# Via Laravel UI
# Project ID: [existing project with Chapter 1]
# Chapter Order: 1
# Prompt: "Continue to Chapter 2"
```

#### 2.3 Edit Flow

**Scenario: Edit existing chapter**
1. Project has Chapters 1-3
2. Edit Chapter 2 content
3. Verify:
   - `update_chapter_content` updates messages in-place
   - Message index preserved
   - Timestamp updated
   - Next generation sees updated Chapter 2

**Test Steps:**
- Generate Chapter 2
- Edit Chapter 2 content in editor
- Generate Chapter 3
- Verify Chapter 3 references updated Chapter 2 content

### Phase 3: Compatibility Tests

#### 3.1 Non-Gemini Providers

**Test: OpenAI provider (should ignore conversation history)**
```python
# Set provider to "openai"
# Verify generation works with standard prompt flow
# Verify no conversation history operations attempted
```

**Test: Non-story usecase (should ignore conversation history)**
```python
# Set usecase to "mock"
# Verify generation works normally
# Verify no conversation history operations
```

#### 3.2 Edge Cases

**Test: Empty prompt**
- Pass empty string as prompt
- Verify conversation history still works
- Verify empty messages are skipped

**Test: Very long conversation history**
- Generate 10+ chapters
- Verify all messages load correctly
- Verify Gemini accepts full history (100k+ tokens)

**Test: Concurrent requests**
- Two users generate simultaneously for same project
- Verify no race conditions
- Verify both conversations saved correctly

### Phase 4: End-to-End Tests

#### 4.1 Full Story Generation

**Complete Flow:**
1. New project created
2. Generate Chapter 1: "Opening scene"
3. Generate Chapter 2: "Rising action"
4. Generate Chapter 3: "Climax"
5. Edit Chapter 2: Change some details
6. Generate Chapter 4: "Resolution"

**Verify:**
- Each chapter references previous chapters
- Chapter 4 shows awareness of edited Chapter 2
- All conversation history preserved
- Database queries perform well

#### 4.2 Multi-User Collaboration

**Test:**
- User A generates Chapter 1
- User B generates Chapter 2 (same project)
- User A generates Chapter 3
- Verify all users share same conversation thread
- Verify continuity maintained

## Test Execution Plan

### Step 1: Setup
```bash
# 1. Run migration
cd runarion-laravel
php artisan migrate

# 2. Verify Python service is running
curl http://localhost:5000/health

# 3. Check database connection
# Verify CONNECTION_POOL is initialized in app.py
```

### Step 2: Manual Testing (Recommended First)

**Test 1: Basic Generation (New Project)**
1. Open Laravel app: `http://localhost:8000`
2. Create new project
3. Navigate to editor
4. Generate first chapter with prompt
5. Check Python logs: Should see "Set conversation history"
6. Check database:
   ```sql
   SELECT messages FROM project_conversations WHERE project_id = '[your-project-id]';
   ```
7. Verify messages array has user + assistant messages

**Test 2: Continuity (Second Chapter)**
1. In same project, generate second chapter
2. Check database: Should have messages from Chapter 1 + Chapter 2
3. Check Python logs: Should show message count > 2
4. Verify generated text shows awareness of Chapter 1

**Test 3: Error Handling**
1. Stop PostgreSQL temporarily
2. Try generation
3. Verify:
   - Generation still works (falls back to prompt-only)
   - Logs show warning, not error
   - No crash

### Step 3: Database Verification

**Check Conversation Storage:**
```sql
-- View all conversations
SELECT project_id, jsonb_array_length(messages) as message_count, updated_at 
FROM project_conversations;

-- View messages for specific project
SELECT jsonb_pretty(messages) 
FROM project_conversations 
WHERE project_id = '[project-id]';

-- Check message structure
SELECT 
    project_id,
    jsonb_array_elements(messages)->>'role' as role,
    jsonb_array_elements(messages)->>'chapter_order' as chapter_order,
    length(jsonb_array_elements(messages)->>'content') as content_length
FROM project_conversations
WHERE project_id = '[project-id]';
```

### Step 4: Performance Testing

**Test: Large conversation history**
- Generate 20 chapters
- Measure:
  - Load time for conversation history
  - Generation time with full history
  - Database query performance

**Expected:**
- Load time: < 100ms
- Generation time: Should not significantly increase
- Database query: Should use index on project_id

## Success Criteria

### Must Pass:
- ✅ New project creates conversation history
- ✅ Existing project loads history correctly
- ✅ Chapter 2 sees Chapter 1 context
- ✅ Gemini receives full conversation array
- ✅ Assistant responses saved after generation
- ✅ Non-Gemini providers still work
- ✅ Errors gracefully degrade to prompt-only mode

### Nice to Have:
- Fast load times (< 100ms)
- No database connection leaks
- Efficient JSONB queries

## Rollback Plan

If issues found:
1. Feature can be disabled by changing `use_conversation_history` check
2. Database table can be ignored (doesn't break existing functionality)
3. All errors fall back to prompt-only mode

## Next Steps After Testing

1. **If all tests pass:**
   - Deploy to staging
   - Monitor for 24 hours
   - Check error logs
   - Deploy to production

2. **If issues found:**
   - Document issues
   - Fix critical bugs
   - Re-test affected scenarios

3. **Performance optimization (if needed):**
   - Add database indexes
   - Optimize JSONB queries
   - Consider pagination for very long histories

