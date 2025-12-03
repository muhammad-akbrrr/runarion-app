# 🧪 Testing Checklist - Conversation History System

## ✅ Pre-Testing Setup (COMPLETED)

- [x] Migration run successfully
- [x] `project_conversations` table created
- [x] All Docker services running

## 📋 Step-by-Step Testing

### Test 1: First Generation (New Project)

**Steps:**
1. Open Laravel app: `http://localhost:8000` (or check Docker logs)
2. Create a new project
3. Navigate to editor
4. Enter prompt: `"Write the opening scene of a fantasy story about a dragon"`
5. Click Generate

**What to Check:**

**A. Python Logs:**
```bash
docker logs runarion-app-python-app-1 --tail 30 | grep -i "conversation"
```

**Look for:**
- ✅ `"Initialized conversation for project [id]"`
- ✅ `"Set conversation history for project [id] with X messages"`
- ✅ `"Saved assistant response to conversation history"`

**B. Database:**
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT project_id, jsonb_array_length(messages) as msg_count FROM project_conversations;"
```

**Expected:**
- ✅ 1 row with `msg_count = 2` (user message + assistant response)

**C. Generated Content:**
- ✅ Chapter 1 was generated successfully
- ✅ Content appears in editor

---

### Test 2: Continuity Test (Second Chapter)

**Steps:**
1. In the **same project**, generate Chapter 2
2. Enter prompt: `"Continue to Chapter 2, the hero meets the dragon"`
3. Click Generate

**What to Check:**

**A. Python Logs:**
```bash
docker logs runarion-app-python-app-1 --tail 20 | grep -i "conversation"
```

**Look for:**
- ✅ `"Set conversation history for project [id] with 3 messages"` (or 4)
- This confirms Chapter 1 was loaded!

**B. Database:**
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT jsonb_array_length(messages) as msg_count FROM project_conversations WHERE project_id = '[your-project-id]';"
```

**Expected:**
- ✅ `msg_count = 4` (2 messages from Chapter 1 + 2 from Chapter 2)

**C. Generated Content Quality:**
- ✅ Chapter 2 references characters/events from Chapter 1
- ✅ Story maintains continuity
- ✅ No disconnected narrative

**D. View Full Conversation:**
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT jsonb_pretty(messages) FROM project_conversations WHERE project_id = '[your-project-id]';"
```

**Expected:**
- ✅ 4 messages total
- ✅ Alternating user/assistant roles
- ✅ Each has `chapter_order`, `timestamp`, `message_index`

---

### Test 3: Multiple Chapters (Optional)

**Steps:**
1. Generate Chapter 3 in same project
2. Prompt: `"Continue to Chapter 3, the climax of the story"`

**What to Check:**
- ✅ Conversation history grows: 6 messages total
- ✅ Chapter 3 shows awareness of Chapters 1 & 2
- ✅ Python logs show: `"with 5 messages"` or more

---

## 🔍 What to Look For

### ✅ Success Indicators:

1. **Python Logs Show:**
   ```
   INFO: Initialized conversation for project [id]
   INFO: Set conversation history for project [id] with X messages
   INFO: Saved assistant response to conversation history
   ```

2. **Database Has:**
   - Rows in `project_conversations` table
   - `messages` JSONB array with multiple entries
   - Each message has proper structure

3. **Generation Quality:**
   - Later chapters reference earlier ones
   - Story maintains continuity
   - Characters/plot points carry over

### ⚠️ Warning Signs (Still OK - Graceful Fallback):

1. **Python Logs Show:**
   ```
   WARNING: Failed to load conversation history... Using prompt-only mode
   ```
   - System still works!
   - But investigate why history failed

2. **Database Empty:**
   - No rows after generation
   - Check Python logs for errors
   - Verify database connection

### ❌ Error Signs (Needs Investigation):

1. **Python Errors:**
   ```
   ERROR: Failed to initialize conversation
   ERROR: Database connection failed
   ```

2. **Generation Fails:**
   - No content generated
   - API errors
   - Check provider (must be Gemini for conversation history)

---

## 🛠️ Quick Verification Commands

### Check Migration Status:
```bash
docker exec -it runarion-app-laravel-app-1 php artisan migrate:status | grep project_conversations
```

### View All Conversations:
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT project_id, jsonb_array_length(messages) as msg_count, updated_at FROM project_conversations ORDER BY updated_at DESC;"
```

### View Python Logs (Real-time):
```bash
docker logs -f runarion-app-python-app-1
```

### View Specific Project Conversation:
```bash
# Replace [project-id] with your actual project ID
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "SELECT jsonb_pretty(messages) FROM project_conversations WHERE project_id = '[project-id]';"
```

### Check Message Structure:
```bash
docker exec -it runarion-app-postgres-db-1 psql -U postgres -d runarion -c "
SELECT 
    jsonb_array_elements(messages)->>'role' as role,
    jsonb_array_elements(messages)->>'chapter_order' as chapter_order,
    LEFT(jsonb_array_elements(messages)->>'content', 100) as content_preview
FROM project_conversations
WHERE project_id = '[project-id]';
"
```

---

## 📊 Expected Results Summary

After completing tests, you should see:

| Test | Expected Result |
|------|----------------|
| Migration | ✅ Table created |
| First Generation | ✅ 2 messages in database |
| Second Generation | ✅ 4 messages in database |
| Python Logs | ✅ Shows conversation history usage |
| Generation Quality | ✅ Chapter 2 references Chapter 1 |
| Database Queries | ✅ Returns conversation data |

---

## 🎯 Success Criteria

**System is working correctly if:**
- ✅ Migration completed
- ✅ Database has conversation records
- ✅ Python logs show history being used
- ✅ Chapter 2 shows context awareness
- ✅ No critical errors in logs

**Ready for production if all above pass!** 🚀

