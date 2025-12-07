# Quick Test Guide - Conversation History System

## ✅ Your Environment Status
- ✅ Laravel app running (port 8000)
- ✅ Python app running (port 5000)
- ✅ PostgreSQL running (port 5432)
- ✅ Redis running (port 6379)

## Step 1: Run Database Migration

First, let's create the `project_conversations` table:

```bash
# In Docker Desktop, open terminal for laravel-app container, or run:
docker exec -it runarion-app-laravel-app-1 php artisan migrate
```

**What to look for:**
- ✅ Should see: `2025_12_20_120000_create_project_conversations_table ... DONE`
- ❌ If error: Check database connection

## Step 2: Verify Migration Success

Check the table was created:

```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "\d project_conversations"
```

**Expected output:**
- Table name: `project_conversations`
- Columns: `project_id` (primary key), `messages` (jsonb), `created_at`, `updated_at`

## Step 3: Test in Laravel UI

### Test 1: New Project - First Generation

1. **Open Laravel app:**
   - Go to: `http://localhost:8000` (or check Docker logs for exact URL)

2. **Create a new project:**
   - Create workspace if needed
   - Create new project (any name)

3. **Navigate to editor:**
   - Open the project editor
   - You should see an empty editor

4. **Generate first chapter:**
   - Enter prompt: `"Write the opening scene of a fantasy story about a dragon"`
   - Click generate
   - Wait for generation to complete

5. **Check Python logs:**
   ```bash
   docker logs runarion-app-python-app-1 --tail 50
   ```
   
   **Look for:**
   - ✅ `"Set conversation history for project [project-id] with X messages"`
   - ✅ `"Initialized conversation for project [project-id]"`
   - ✅ `"Saved assistant response to conversation history"`

6. **Check database:**
   ```bash
   docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT project_id, jsonb_array_length(messages) as message_count FROM project_conversations;"
   ```
   
   **Expected:**
   - Should see 1 row with message_count = 2 (user message + assistant response)

### Test 2: Continuity - Second Chapter

1. **In the same project, generate Chapter 2:**
   - Enter prompt: `"Continue to Chapter 2, the hero meets the dragon"`
   - Click generate

2. **Check Python logs again:**
   ```bash
   docker logs runarion-app-python-app-1 --tail 20
   ```
   
   **Look for:**
   - ✅ `"Set conversation history for project [project-id] with 3 messages"` (or more)
   - This means Chapter 1 context was loaded!

3. **Verify context awareness:**
   - Read the generated Chapter 2
   - ✅ Should reference characters/events from Chapter 1
   - ✅ Should maintain story continuity

4. **Check database:**
   ```bash
   docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT jsonb_pretty(messages) FROM project_conversations WHERE project_id = '[your-project-id]';"
   ```
   
   **Expected:**
   - Should see 3-4 messages:
     - User: Chapter 1 prompt
     - Assistant: Chapter 1 response
     - User: Chapter 2 prompt
     - Assistant: Chapter 2 response

### Test 3: View Full Conversation History

```bash
# Get your project ID from Laravel UI or database
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "
SELECT 
    project_id,
    jsonb_array_length(messages) as total_messages,
    jsonb_array_elements(messages)->>'role' as role,
    jsonb_array_elements(messages)->>'chapter_order' as chapter_order,
    LEFT(jsonb_array_elements(messages)->>'content', 50) as content_preview
FROM project_conversations
WHERE project_id = '[your-project-id]';
"
```

## Step 4: What to Look For (Success Indicators)

### ✅ Success Signs:

1. **Python Logs:**
   ```
   INFO: Set conversation history for project [id] with 2 messages
   INFO: Saved assistant response to conversation history
   ```

2. **Database:**
   - `project_conversations` table has rows
   - `messages` JSONB array grows with each generation
   - Each message has: `role`, `content`, `timestamp`, `message_index`

3. **Generation Quality:**
   - Chapter 2 references Chapter 1
   - Story maintains continuity
   - Characters/plot points carry over

### ❌ Warning Signs:

1. **Python Logs:**
   ```
   WARNING: Failed to load conversation history... Using prompt-only mode
   ```
   - This is OK! System falls back gracefully
   - But investigate why history failed to load

2. **Database:**
   - No rows in `project_conversations` after generation
   - Messages array is empty
   - Check Python logs for errors

3. **Generation Quality:**
   - Chapter 2 doesn't reference Chapter 1
   - Story seems disconnected
   - May indicate conversation history not being used

## Step 5: Error Handling Test (Optional)

Test graceful degradation:

1. **Temporarily stop PostgreSQL:**
   ```bash
   docker stop runarion-app-postgres-db-1
   ```

2. **Try generating:**
   - Should still work! (falls back to prompt-only mode)
   - Check logs for warning (not error)

3. **Restart PostgreSQL:**
   ```bash
   docker start runarion-app-postgres-db-1
   ```

## Quick Verification Commands

### Check if migration ran:
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "\dt project_conversations"
```

### View all conversations:
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT project_id, jsonb_array_length(messages) as msg_count, updated_at FROM project_conversations;"
```

### View Python logs in real-time:
```bash
docker logs -f runarion-app-python-app-1
```

### View Laravel logs:
```bash
docker logs -f runarion-app-laravel-app-1
```

## Troubleshooting

### Issue: Migration fails
**Solution:** Check database connection in Laravel container
```bash
docker exec -it runarion-app-laravel-app-1 php artisan migrate:status
```

### Issue: No conversation history saved
**Check:**
1. Python logs for errors
2. Database connection from Python container
3. Project ID is being passed correctly

### Issue: Chapter 2 doesn't show context
**Check:**
1. Python logs show "Set conversation history with X messages" (X > 1)
2. Database has messages from Chapter 1
3. Provider is Gemini (not OpenAI)

## Expected Test Results

After completing all tests, you should have:

1. ✅ `project_conversations` table created
2. ✅ At least one project with conversation history
3. ✅ Multiple messages per project (user + assistant pairs)
4. ✅ Chapter 2 generation shows awareness of Chapter 1
5. ✅ Python logs show conversation history being used
6. ✅ Database queries return conversation data

## Next Steps After Testing

If all tests pass:
- ✅ System is working correctly!
- ✅ Ready for production use
- ✅ Monitor logs for any edge cases

If issues found:
- Check Python logs for specific errors
- Verify database connectivity
- Review error messages in TEST_RESULTS.md








