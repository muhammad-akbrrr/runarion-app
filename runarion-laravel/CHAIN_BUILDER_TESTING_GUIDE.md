# Multi-Node Chain Builder - Testing Guide

## ✅ **SYSTEM STATUS: READY FOR TESTING**

All core features have been implemented. The system is ready for comprehensive testing.

---

## 🏗️ **WHAT WAS BUILT**

### **Core Components:**
1. ✅ **ChainBuilder** - Main graph canvas with pan/zoom
2. ✅ **Node Component** - Prompt/Context/Logic nodes with connectors
3. ✅ **Edge Component** - Visual connections between nodes (fixed for pan/zoom)
4. ✅ **RecordsDrawer** - Left sidebar showing all entities (system + custom types)
5. ✅ **Toolbar** - Full-width toolbar below main nav
6. ✅ **Zoom Controls** - Bottom-right zoom controls

### **AI Features:**
1. ✅ **Magic Wand** - Auto-generate instructions for prompt nodes
2. ✅ **Auto-Build** - Generate entire graph from description
3. ✅ **Refine Selection** - Enhance selected nodes with AI
4. ✅ **Graph Execution** - Run full flow (Final-Only or Sequence mode)

### **Backend Integration:**
1. ✅ **ChainBuilderController** - Laravel controller for AI operations
2. ✅ **Python Service Integration** - Calls to `/generate` endpoint
3. ✅ **Records API Integration** - Fetches entities and collection types
4. ✅ **Story Context** - Aggregates chapters for AI context

### **Data Management:**
1. ✅ **LocalStorage Persistence** - Saves graph state automatically
2. ✅ **Entity Formatting** - Converts Runarion entities to AI context
3. ✅ **Custom Collection Types** - Supports user-created entity types

---

## 🧪 **HOW TO TEST**

### **1. Basic UI & Layout**

**Test Steps:**
1. Navigate to `/projects/{project_id}/editor/multi-prompt`
2. Verify layout structure:
   - ✅ Toolbar is full-width below main nav
   - ✅ Records drawer is full-height on left (256px width)
   - ✅ Canvas takes remaining space on right
   - ✅ Zoom controls visible in bottom-right

**Expected Results:**
- Clean, organized layout
- No overlapping elements
- Responsive to window resize

---

### **2. Records Drawer**

**Test Steps:**
1. Check Records drawer shows:
   - ✅ "All Types" filter button
   - ✅ System types (Character, Location, Item, Theme, Plot Point)
   - ✅ **Custom collection types** (e.g., Faction, Record Keeper)
2. Click each filter button
3. Verify entities filter correctly
4. Use search bar to filter entities

**Expected Results:**
- All collection types visible (system + custom)
- Filtering works correctly
- Search works
- Entities display with proper formatting

---

### **3. Node Creation & Manipulation**

**Test Steps:**
1. Click "Prompt" button → Verify node appears
2. Click "Context" button → Verify node appears
3. Click "Logic" button → Verify node appears
4. Drag nodes around canvas
5. Click node to select (should highlight)
6. Click "Trash" icon → Verify node deletes

**Expected Results:**
- Nodes appear at reasonable positions
- Dragging is smooth
- Selection works (blue border)
- Deletion works

---

### **4. Node Connections**

**Test Steps:**
1. Create two nodes (e.g., Prompt → Prompt)
2. Click and drag from **right connector** (output) of first node
3. Drag to **left connector** (input) of second node
4. Release mouse → Verify edge appears
5. Verify edge line properly connects nodes (not offset)
6. Pan/zoom canvas → Verify edges stay connected
7. Delete source or target node → Verify edge disappears

**Expected Results:**
- ✅ **Edge lines properly connect node centers**
- ✅ **Edges scale correctly with zoom**
- ✅ **Edges pan correctly with canvas**
- ✅ **No visual glitches or offsets**

---

### **5. Node Editing**

**Test Steps:**
1. Click on a node's textarea
2. Type/edit content
3. Click outside → Verify content saves
4. Refresh page → Verify content persists (localStorage)

**Expected Results:**
- Text editing works
- Content persists on refresh
- No data loss

---

### **6. Magic Wand (Auto-Write Instructions)**

**Test Steps:**
1. Create a "Prompt" node
2. Click the **sparkles icon** (Magic Wand) in node header
3. Enter seed text (optional)
4. Click "Generate" → Wait for AI generation
5. Verify instruction appears in textarea

**Expected Results:**
- ✅ **Magic Wand button is clickable**
- ✅ **Modal opens**
- ✅ **AI generates instruction**
- ✅ **Instruction populates node content**

---

### **7. Auto-Build Graph**

**Test Steps:**
1. Click "Auto-Build" button in toolbar
2. Enter description: "Create a scene where the hero meets a mysterious stranger"
3. Select mode: "Sequence" or "Final Only"
4. Click "Generate Graph"
5. Wait for AI to generate graph
6. Verify nodes and edges appear

**Expected Results:**
- Modal opens
- AI generates logical graph structure
- Nodes positioned correctly
- Edges connect properly
- Graph makes sense for the description

---

### **8. Refine Selection**

**Test Steps:**
1. Create 2-3 connected nodes
2. Select multiple nodes (click while holding Shift/Cmd)
3. Click "Refine" button (should show count)
4. Enter refinement prompt: "Make the prompts more dramatic"
5. Click "Refine"
6. Verify nodes update

**Expected Results:**
- Refine button appears when nodes selected
- Modal opens with selected node count
- AI refines selected nodes
- Updates preserve connections

---

### **9. Graph Execution - Final-Only Mode**

**Test Steps:**
1. Create graph:
   - Context node: "The hero is a warrior"
   - Prompt node: "Write a scene where the hero fights"
   - Connect Context → Prompt
2. Set mode to "Final Only"
3. Click "Run & Write Final"
4. Wait for execution
5. Verify:
   - Context node shows "completed" status
   - Prompt node shows "completed" status
   - Prompt node has output text

**Expected Results:**
- Execution runs without errors
- Status indicators update (green checkmark)
- Output appears in prompt nodes
- Only final prompt nodes show output

---

### **10. Graph Execution - Sequence Mode**

**Test Steps:**
1. Create graph:
   - Prompt 1: "Write opening paragraph"
   - Prompt 2: "Write middle paragraph"
   - Prompt 3: "Write closing paragraph"
   - Connect: Prompt 1 → Prompt 2 → Prompt 3
2. Set mode to "Sequence"
3. Click "Run & Write All"
4. Wait for execution
5. Verify all prompt nodes have output

**Expected Results:**
- All prompt nodes execute
- Outputs appear in sequence
- Each node shows "completed" status

---

### **11. Entity Drag & Drop**

**Test Steps:**
1. Open Records drawer
2. Filter to "Character" type
3. Drag an entity (e.g., "Kael") onto canvas
4. Release → Verify Context node created
5. Verify node content includes entity data

**Expected Results:**
- Context node created at drop position
- Node label = entity name
- Node content = formatted entity data
- Entity data properly formatted for AI

---

### **12. Pan & Zoom**

**Test Steps:**
1. Scroll mouse wheel → Verify zoom changes
2. Click zoom controls (+/-) → Verify zoom changes
3. Click "Maximize" → Verify reset to 100%
4. Click and drag empty canvas → Verify panning
5. Pan while zoomed → Verify smooth movement

**Expected Results:**
- Zoom works smoothly
- Pan works smoothly
- Grid scales with zoom
- Nodes/edges scale correctly

---

### **13. Cycle Detection**

**Test Steps:**
1. Create circular connection:
   - Node A → Node B → Node A
2. Click "Run & Write Final"
3. Verify error message appears

**Expected Results:**
- Error: "Cannot run flow: Infinite loop detected!"
- Execution prevented
- No partial execution

---

### **14. Persistence**

**Test Steps:**
1. Create graph with multiple nodes and connections
2. Edit node content
3. Refresh page
4. Verify graph state restored

**Expected Results:**
- Graph structure persists
- Node positions persist
- Node content persists
- Edges persist

---

### **15. Inspector**

**Test Steps:**
1. Create a node with inputs
2. Click "Eye" icon on node
3. Verify inspector modal opens
4. Check "Inputs" section shows connected node outputs

**Expected Results:**
- Inspector shows node details
- Inputs properly formatted
- Output visible
- Status visible

---

## 🐛 **KNOWN ISSUES / LIMITATIONS**

1. **Apply to Editor**: The `onApplyResult` callback exists but isn't connected to the main editor. Results can be copied manually or we can add a "Copy to Clipboard" button.

2. **Node Width**: Nodes have fixed width (300px). May need dynamic sizing for long content.

3. **Edge Arrowheads**: Arrowheads may need adjustment for different zoom levels.

---

## ✅ **TESTING CHECKLIST**

- [ ] Layout structure correct
- [ ] Records drawer shows all types (system + custom)
- [ ] Node creation works (Prompt/Context/Logic)
- [ ] Node dragging works
- [ ] Node deletion works
- [ ] **Edge connections properly render**
- [ ] **Magic Wand button clickable**
- [ ] Auto-Build generates graphs
- [ ] Refine Selection works
- [ ] Final-Only execution works
- [ ] Sequence execution works
- [ ] Entity drag & drop works
- [ ] Pan & zoom work
- [ ] Cycle detection works
- [ ] Persistence works
- [ ] Inspector works

---

## 🚀 **NEXT STEPS AFTER TESTING**

1. **If all tests pass**: System is production-ready!
2. **If issues found**: Report specific issues for fixes
3. **Enhancements to consider**:
   - Copy result to clipboard button
   - Export graph as image
   - Save graph as template
   - Undo/Redo functionality
   - Node templates library

---

## 📝 **NOTES**

- Graph state saves automatically to `localStorage` with key: `chainbuilder_${projectId}`
- AI calls go through Laravel backend → Python Flask service
- Story context includes all chapters (up to 500k chars)
- Entity data formatted as JSON for AI consumption

---

**Happy Testing! 🎉**

