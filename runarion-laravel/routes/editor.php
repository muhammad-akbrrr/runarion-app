<?php

use App\Http\Controllers\ProjectEditor\AdvisorController;
use App\Http\Controllers\ProjectEditor\ChainBuilderController;
use App\Http\Controllers\ProjectEditor\MainEditorController;
use App\Http\Controllers\ProjectEditor\MultiPromptController;
use App\Http\Controllers\ProjectEditor\ProjectDatabaseController;
use App\Http\Controllers\ProjectEditor\RecordsController;
use App\Http\Controllers\ProjectEditor\VersionHistoryController;
use Illuminate\Support\Facades\Route;

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'editor'])->name('workspace.projects.editor');
    Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->middleware('project-unlocked')->name('editor.project.updateName');
    Route::post('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'projectOnboarding'])->middleware('project-unlocked')->name('editor.project.onboarding');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chapter', [MainEditorController::class, 'storeProjectChapter'])->middleware('project-unlocked')->name('editor.project.chapter');
    Route::get('/{workspace_id}/projects/{project_id}/editor/chapters', [MainEditorController::class, 'getChapters'])->name('editor.project.chapters');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/chapter/{order}', [MainEditorController::class, 'updateChapter'])->middleware('project-unlocked')->name('editor.project.updateChapter');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/chapter/{order}', [MainEditorController::class, 'deleteChapter'])->middleware('project-unlocked')->name('editor.project.deleteChapter');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/data', [MainEditorController::class, 'updateProjectData'])->middleware('project-unlocked')->name('editor.project.updateData');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/settings', [MainEditorController::class, 'updateProjectSettings'])->middleware('project-unlocked')->name('editor.project.updateSettings');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/unified', [MainEditorController::class, 'updateProjectUnified'])->middleware('project-unlocked')->name('editor.project.updateUnified');
    Route::post('/{workspace_id}/projects/{project_id}/editor/initialize-history', [MainEditorController::class, 'initializeChapterHistory'])->middleware('project-unlocked')->name('editor.project.initialize-history');
    Route::post('/{workspace_id}/projects/{project_id}/editor/generate', [MainEditorController::class, 'generateText'])->middleware('project-unlocked')->name('editor.project.generate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/regenerate', [MainEditorController::class, 'regenerateText'])->middleware('project-unlocked')->name('editor.project.regenerate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/rewrite-selection', [MainEditorController::class, 'rewriteSelection'])->middleware('project-unlocked')->name('editor.project.rewrite-selection');
    Route::post('/{workspace_id}/projects/{project_id}/editor/enhance-text', [MainEditorController::class, 'enhanceText'])->middleware('project-unlocked')->name('editor.project.enhance-text');
    Route::post('/{workspace_id}/projects/{project_id}/editor/cancel-generation', [MainEditorController::class, 'cancelGeneration'])->middleware('project-unlocked')->name('editor.project.cancel-generation');
    Route::post('/{workspace_id}/projects/{project_id}/editor/switch-version', [MainEditorController::class, 'switchVersion'])->middleware('project-unlocked')->name('editor.project.switch-version');
    Route::post('/{workspace_id}/projects/{project_id}/editor/undo-step', [MainEditorController::class, 'undoStep'])->middleware('project-unlocked')->name('editor.project.undo-step');
    Route::post('/{workspace_id}/projects/{project_id}/editor/redo-step', [MainEditorController::class, 'redoStep'])->middleware('project-unlocked')->name('editor.project.redo-step');
    Route::get('/{workspace_id}/projects/{project_id}/editor/version-info', [MainEditorController::class, 'getVersionControlInfo'])->name('editor.project.version-info');

    Route::get('/projects/{project_id}/editor', fn () => '')->name('raw.workspace.projects.editor');
});

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/database', [ProjectDatabaseController::class, 'database'])->name('workspace.projects.editor.database');

    Route::get('/projects/{project_id}/editor/database', fn () => '')->name('raw.workspace.projects.editor.database');
});

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/multi-prompt', [MultiPromptController::class, 'multiPrompt'])->name('workspace.projects.editor.multiprompt');

    Route::get('/projects/{project_id}/editor/multi-prompt', fn () => '')->name('raw.workspace.projects.editor.multiprompt');
});

// Version History Routes
Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/version-history', [VersionHistoryController::class, 'index'])->name('workspace.projects.editor.version-history');
    Route::post('/{workspace_id}/projects/{project_id}/editor/version-history/snapshots', [VersionHistoryController::class, 'createSnapshot'])->middleware('project-unlocked')->name('version-history.snapshots.create');
    Route::post('/{workspace_id}/projects/{project_id}/editor/version-history/snapshots/{snapshot_id}/load', [VersionHistoryController::class, 'loadSnapshot'])->middleware('project-unlocked')->name('version-history.snapshots.load');
    Route::put('/{workspace_id}/projects/{project_id}/editor/version-history/snapshots/{snapshot_id}', [VersionHistoryController::class, 'updateSnapshot'])->middleware('project-unlocked')->name('version-history.snapshots.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/version-history/snapshots/{snapshot_id}', [VersionHistoryController::class, 'deleteSnapshot'])->middleware('project-unlocked')->name('version-history.snapshots.delete');
    Route::get('/{workspace_id}/projects/{project_id}/editor/version-history/chapters/{chapter_order}/tree', [VersionHistoryController::class, 'getChapterVersionTree'])->name('version-history.chapters.tree');

    Route::get('/projects/{project_id}/editor/version-history', fn () => '')->name('raw.workspace.projects.editor.version-history');
});

// Records System Routes
Route::middleware(['auth', 'project-editor'])->group(function () {
    // Entity CRUD
    Route::post('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'createEntity'])->middleware('project-unlocked')->name('records.entities.create');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'listEntities'])->name('records.entities.list');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'getEntity'])->name('records.entities.get');
    Route::put('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'updateEntity'])->middleware('project-unlocked')->name('records.entities.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'deleteEntity'])->middleware('project-unlocked')->name('records.entities.delete');

    // Relationship CRUD
    Route::post('/{workspace_id}/projects/{project_id}/editor/records/relationships', [RecordsController::class, 'createRelationship'])->middleware('project-unlocked')->name('records.relationships.create');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/relationships', [RecordsController::class, 'listRelationships'])->name('records.relationships.list');
    Route::put('/{workspace_id}/projects/{project_id}/editor/records/relationships/{edge_id}', [RecordsController::class, 'updateRelationship'])->middleware('project-unlocked')->name('records.relationships.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/records/relationships/{edge_id}', [RecordsController::class, 'deleteRelationship'])->middleware('project-unlocked')->name('records.relationships.delete');

    // Collection Type (Entity Type) CRUD
    Route::post('/{workspace_id}/projects/{project_id}/editor/records/collection-types', [RecordsController::class, 'createCollectionType'])->middleware('project-unlocked')->name('records.collection-types.create');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/collection-types', [RecordsController::class, 'listCollectionTypes'])->name('records.collection-types.list');
    Route::put('/{workspace_id}/projects/{project_id}/editor/records/collection-types/{type_id}', [RecordsController::class, 'updateCollectionType'])->middleware('project-unlocked')->name('records.collection-types.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/records/collection-types/{type_id}', [RecordsController::class, 'deleteCollectionType'])->middleware('project-unlocked')->name('records.collection-types.delete');

    // Auditor/Summarization
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/summarize', [RecordsController::class, 'summarize'])->middleware('project-unlocked')->name('auditor.summarize');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/extract', [RecordsController::class, 'extractEntities'])->middleware('project-unlocked')->name('auditor.extract');

    // Categories and entities for selection UI
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/categories', [RecordsController::class, 'getCategories'])->name('records.categories');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'getEntitiesByCategory'])->name('records.entities');

    // Auditor Tools (scan status, consistency checking, optimization)
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/scan-status', [RecordsController::class, 'getScanStatus'])->name('auditor.scan-status');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/check-consistency/records', [RecordsController::class, 'checkRecordConsistency'])->middleware('project-unlocked')->name('auditor.check-consistency.records');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/check-consistency/story', [RecordsController::class, 'checkStoryConsistency'])->middleware('project-unlocked')->name('auditor.check-consistency.story');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/find-duplicates', [RecordsController::class, 'findDuplicates'])->middleware('project-unlocked')->name('auditor.find-duplicates');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/merge-entities', [RecordsController::class, 'mergeEntities'])->middleware('project-unlocked')->name('auditor.merge-entities');

    // Property refresh (arc-aware updates)
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/refresh-properties', [RecordsController::class, 'refreshEntityProperties'])->middleware('project-unlocked')->name('auditor.refresh-properties');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/refresh-all-properties', [RecordsController::class, 'refreshAllProperties'])->middleware('project-unlocked')->name('auditor.refresh-all-properties');

    // Apply fixes from consistency checks
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/apply-fix', [RecordsController::class, 'applyConsistencyFix'])->middleware('project-unlocked')->name('auditor.apply-fix');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/fix-story-text', [RecordsController::class, 'fixStoryText'])->middleware('project-unlocked')->name('auditor.fix-story-text');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/batch-fix-story-text', [RecordsController::class, 'batchFixStoryText'])->middleware('project-unlocked')->name('auditor.batch-fix-story-text');

    // Sentiment Analyzer
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/extract-relationships', [RecordsController::class, 'extractRelationships'])->middleware('project-unlocked')->name('auditor.extract-relationships');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/scan-relationship-changes', [RecordsController::class, 'scanRelationshipChanges'])->middleware('project-unlocked')->name('auditor.scan-relationship-changes');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/apply-relationship-changes', [RecordsController::class, 'applyRelationshipChanges'])->middleware('project-unlocked')->name('auditor.apply-relationship-changes');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/delete-all-interactions', [RecordsController::class, 'deleteAllInteractions'])->middleware('project-unlocked')->name('auditor.delete-all-interactions');

    // Interaction Records
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/interactions', [RecordsController::class, 'getInteractions'])->name('auditor.interactions');
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/aggregate', [RecordsController::class, 'aggregateInteractions'])->name('auditor.interactions.aggregate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/interactions', [RecordsController::class, 'createInteraction'])->middleware('project-unlocked')->name('auditor.interactions.create');
    Route::put('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/{vertex_id}', [RecordsController::class, 'updateInteraction'])->middleware('project-unlocked')->name('auditor.interactions.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/{vertex_id}', [RecordsController::class, 'deleteInteraction'])->middleware('project-unlocked')->name('auditor.interactions.delete');

    // Relationship Synthesis & Recalculation
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/synthesize', [RecordsController::class, 'synthesizeRelationship'])->middleware('project-unlocked')->name('auditor.relationships.synthesize');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/recalculate', [RecordsController::class, 'recalculateRelationshipSentiment'])->middleware('project-unlocked')->name('auditor.relationships.recalculate');

    // Chapter Analyses Management
    Route::put('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/{edge_id}/chapter-analyses', [RecordsController::class, 'updateChapterAnalyses'])->middleware('project-unlocked')->name('auditor.relationships.chapter-analyses.update');

    // Custom Emotional Tones
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones', [RecordsController::class, 'getEmotionalTones'])->name('auditor.emotional-tones.list');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones', [RecordsController::class, 'createEmotionalTone'])->middleware('project-unlocked')->name('auditor.emotional-tones.create');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones/{tone_id}', [RecordsController::class, 'deleteEmotionalTone'])->middleware('project-unlocked')->name('auditor.emotional-tones.delete');
});

// Advisor Routes - AI Writing Assistant with full story context
Route::middleware(['auth', 'project-editor'])->group(function () {
    // Chat CRUD
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/chats', [AdvisorController::class, 'listChats'])->name('advisor.chats.list');
    Route::post('/{workspace_id}/projects/{project_id}/editor/advisor/chats', [AdvisorController::class, 'createChat'])->middleware('project-unlocked')->name('advisor.chats.create');
    Route::put('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}', [AdvisorController::class, 'updateChat'])->middleware('project-unlocked')->name('advisor.chats.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}', [AdvisorController::class, 'deleteChat'])->middleware('project-unlocked')->name('advisor.chats.delete');

    // Messages
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'getMessages'])->name('advisor.messages.get');
    Route::post('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'sendMessage'])->middleware('project-unlocked')->name('advisor.messages.send');
    Route::post('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages/cancel', [AdvisorController::class, 'cancelMessageStream'])->middleware('project-unlocked')->name('advisor.messages.cancel');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'clearMessages'])->middleware('project-unlocked')->name('advisor.messages.clear');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages/{message_id}', [AdvisorController::class, 'deleteMessage'])->middleware('project-unlocked')->name('advisor.messages.delete');

    // Story context
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/story-context', [AdvisorController::class, 'getStoryContext'])->name('advisor.story-context');
});

// Chain Builder Routes - Multi-Node Prompt System
Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::post('/{workspace_id}/projects/{project_id}/editor/chain-builder/execute-node', [ChainBuilderController::class, 'executeNode'])->middleware('project-unlocked')->name('chain-builder.execute-node');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chain-builder/generate-layout', [ChainBuilderController::class, 'generateGraphLayout'])->middleware('project-unlocked')->name('chain-builder.generate-layout');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chain-builder/generate-instruction', [ChainBuilderController::class, 'generateInstruction'])->middleware('project-unlocked')->name('chain-builder.generate-instruction');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chain-builder/refine-selection', [ChainBuilderController::class, 'refineSelection'])->middleware('project-unlocked')->name('chain-builder.refine-selection');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chain-builder/apply-to-story', [ChainBuilderController::class, 'applyToStory'])->middleware('project-unlocked')->name('chain-builder.apply-to-story');
    Route::post('/{workspace_id}/projects/{project_id}/editor/enhance-auto-build-prompt', [ChainBuilderController::class, 'enhanceAutoBuildPrompt'])->middleware('project-unlocked')->name('chain-builder.enhance-auto-build-prompt');
});
