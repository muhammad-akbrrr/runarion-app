<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProjectEditor\MainEditorController;
use App\Http\Controllers\ProjectEditor\ProjectDatabaseController;
use App\Http\Controllers\ProjectEditor\MultiPromptController;
use App\Http\Controllers\ProjectEditor\ImageGeneratorController;
use App\Http\Controllers\ProjectEditor\RecordsController;
use App\Http\Controllers\ProjectEditor\AdvisorController;

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'editor'])->name('workspace.projects.editor');
    Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->name('editor.project.updateName');
    Route::post('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'projectOnboarding'])->name('editor.project.onboarding');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chapter', [MainEditorController::class, 'storeProjectChapter'])->name('editor.project.chapter');
    Route::get('/{workspace_id}/projects/{project_id}/editor/chapters', [MainEditorController::class, 'getChapters'])->name('editor.project.chapters');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/chapter/{order}', [MainEditorController::class, 'updateChapter'])->name('editor.project.updateChapter');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/chapter/{order}', [MainEditorController::class, 'deleteChapter'])->name('editor.project.deleteChapter');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/data', [MainEditorController::class, 'updateProjectData'])->name('editor.project.updateData');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/settings', [MainEditorController::class, 'updateProjectSettings'])->name('editor.project.updateSettings');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/unified', [MainEditorController::class, 'updateProjectUnified'])->name('editor.project.updateUnified');
    Route::post('/{workspace_id}/projects/{project_id}/editor/initialize-history', [MainEditorController::class, 'initializeChapterHistory'])->name('editor.project.initialize-history');
    Route::post('/{workspace_id}/projects/{project_id}/editor/generate', [MainEditorController::class, 'generateText'])->name('editor.project.generate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/regenerate', [MainEditorController::class, 'regenerateText'])->name('editor.project.regenerate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/rewrite-selection', [MainEditorController::class, 'rewriteSelection'])->name('editor.project.rewrite-selection');
    Route::post('/{workspace_id}/projects/{project_id}/editor/enhance-text', [MainEditorController::class, 'enhanceText'])->name('editor.project.enhance-text');
    Route::post('/{workspace_id}/projects/{project_id}/editor/cancel-generation', [MainEditorController::class, 'cancelGeneration'])->name('editor.project.cancel-generation');
    Route::post('/{workspace_id}/projects/{project_id}/editor/switch-version', [MainEditorController::class, 'switchVersion'])->name('editor.project.switch-version');
    Route::post('/{workspace_id}/projects/{project_id}/editor/undo-step', [MainEditorController::class, 'undoStep'])->name('editor.project.undo-step');
    Route::post('/{workspace_id}/projects/{project_id}/editor/redo-step', [MainEditorController::class, 'redoStep'])->name('editor.project.redo-step');
    Route::get('/{workspace_id}/projects/{project_id}/editor/version-info', [MainEditorController::class, 'getVersionControlInfo'])->name('editor.project.version-info');

    Route::get('/projects/{project_id}/editor', fn() => '')->name('raw.workspace.projects.editor');
});

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/database', [ProjectDatabaseController::class, 'database'])->name('workspace.projects.editor.database');

    Route::get('/projects/{project_id}/editor/database', fn() => '')->name('raw.workspace.projects.editor.database');
});

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/multi-prompt', [MultiPromptController::class, 'multiPrompt'])->name('workspace.projects.editor.multiprompt');

    Route::get('/projects/{project_id}/editor/multi-prompt', fn() => '')->name('raw.workspace.projects.editor.multiprompt');
});

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor/image', [ImageGeneratorController::class, 'imageGenerator'])->name('workspace.projects.editor.image');

    Route::get('/projects/{project_id}/editor/image', fn() => '')->name('raw.workspace.projects.editor.image');
});

// Records System Routes
Route::middleware(['auth', 'project-editor'])->group(function () {
    // Entity CRUD
    Route::post('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'createEntity'])->name('records.entities.create');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'listEntities'])->name('records.entities.list');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'getEntity'])->name('records.entities.get');
    Route::put('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'updateEntity'])->name('records.entities.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/records/entities/{vertex_id}', [RecordsController::class, 'deleteEntity'])->name('records.entities.delete');
    
            // Relationship CRUD
            Route::post('/{workspace_id}/projects/{project_id}/editor/records/relationships', [RecordsController::class, 'createRelationship'])->name('records.relationships.create');
            Route::get('/{workspace_id}/projects/{project_id}/editor/records/relationships', [RecordsController::class, 'listRelationships'])->name('records.relationships.list');
            Route::put('/{workspace_id}/projects/{project_id}/editor/records/relationships/{edge_id}', [RecordsController::class, 'updateRelationship'])->name('records.relationships.update');
            Route::delete('/{workspace_id}/projects/{project_id}/editor/records/relationships/{edge_id}', [RecordsController::class, 'deleteRelationship'])->name('records.relationships.delete');
    
    // Collection Type (Entity Type) CRUD
    Route::post('/{workspace_id}/projects/{project_id}/editor/records/collection-types', [RecordsController::class, 'createCollectionType'])->name('records.collection-types.create');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/collection-types', [RecordsController::class, 'listCollectionTypes'])->name('records.collection-types.list');
    Route::put('/{workspace_id}/projects/{project_id}/editor/records/collection-types/{type_id}', [RecordsController::class, 'updateCollectionType'])->name('records.collection-types.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/records/collection-types/{type_id}', [RecordsController::class, 'deleteCollectionType'])->name('records.collection-types.delete');
    
    // Auditor/Summarization
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/summarize', [RecordsController::class, 'summarize'])->name('auditor.summarize');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/extract', [RecordsController::class, 'extractEntities'])->name('auditor.extract');
    
    // Categories and entities for selection UI
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/categories', [RecordsController::class, 'getCategories'])->name('records.categories');
    Route::get('/{workspace_id}/projects/{project_id}/editor/records/entities', [RecordsController::class, 'getEntitiesByCategory'])->name('records.entities');
    
    // Auditor Tools (scan status, consistency checking, optimization)
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/scan-status', [RecordsController::class, 'getScanStatus'])->name('auditor.scan-status');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/check-consistency/records', [RecordsController::class, 'checkRecordConsistency'])->name('auditor.check-consistency.records');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/check-consistency/story', [RecordsController::class, 'checkStoryConsistency'])->name('auditor.check-consistency.story');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/find-duplicates', [RecordsController::class, 'findDuplicates'])->name('auditor.find-duplicates');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/merge-entities', [RecordsController::class, 'mergeEntities'])->name('auditor.merge-entities');
    
    // Property refresh (arc-aware updates)
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/refresh-properties', [RecordsController::class, 'refreshEntityProperties'])->name('auditor.refresh-properties');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/refresh-all-properties', [RecordsController::class, 'refreshAllProperties'])->name('auditor.refresh-all-properties');
    
    // Apply fixes from consistency checks
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/apply-fix', [RecordsController::class, 'applyConsistencyFix'])->name('auditor.apply-fix');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/fix-story-text', [RecordsController::class, 'fixStoryText'])->name('auditor.fix-story-text');
    
    // Sentiment Analyzer
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/extract-relationships', [RecordsController::class, 'extractRelationships'])->name('auditor.extract-relationships');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/scan-relationship-changes', [RecordsController::class, 'scanRelationshipChanges'])->name('auditor.scan-relationship-changes');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/apply-relationship-changes', [RecordsController::class, 'applyRelationshipChanges'])->name('auditor.apply-relationship-changes');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/delete-all-interactions', [RecordsController::class, 'deleteAllInteractions'])->name('auditor.delete-all-interactions');
    
    // Interaction Records
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/interactions', [RecordsController::class, 'getInteractions'])->name('auditor.interactions');
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/aggregate', [RecordsController::class, 'aggregateInteractions'])->name('auditor.interactions.aggregate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/interactions', [RecordsController::class, 'createInteraction'])->name('auditor.interactions.create');
    Route::put('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/{vertex_id}', [RecordsController::class, 'updateInteraction'])->name('auditor.interactions.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/interactions/{vertex_id}', [RecordsController::class, 'deleteInteraction'])->name('auditor.interactions.delete');
    
    // Relationship Synthesis & Recalculation
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/synthesize', [RecordsController::class, 'synthesizeRelationship'])->name('auditor.relationships.synthesize');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/recalculate', [RecordsController::class, 'recalculateRelationshipSentiment'])->name('auditor.relationships.recalculate');
    
    // Chapter Analyses Management
    Route::put('/{workspace_id}/projects/{project_id}/editor/auditor/relationships/{edge_id}/chapter-analyses', [RecordsController::class, 'updateChapterAnalyses'])->name('auditor.relationships.chapter-analyses.update');
    
    // Custom Emotional Tones
    Route::get('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones', [RecordsController::class, 'getEmotionalTones'])->name('auditor.emotional-tones.list');
    Route::post('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones', [RecordsController::class, 'createEmotionalTone'])->name('auditor.emotional-tones.create');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/auditor/emotional-tones/{tone_id}', [RecordsController::class, 'deleteEmotionalTone'])->name('auditor.emotional-tones.delete');
});

// Advisor Routes - AI Writing Assistant with full story context
Route::middleware(['auth', 'project-editor'])->group(function () {
    // Chat CRUD
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/chats', [AdvisorController::class, 'listChats'])->name('advisor.chats.list');
    Route::post('/{workspace_id}/projects/{project_id}/editor/advisor/chats', [AdvisorController::class, 'createChat'])->name('advisor.chats.create');
    Route::put('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}', [AdvisorController::class, 'updateChat'])->name('advisor.chats.update');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}', [AdvisorController::class, 'deleteChat'])->name('advisor.chats.delete');
    
    // Messages
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'getMessages'])->name('advisor.messages.get');
    Route::post('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'sendMessage'])->name('advisor.messages.send');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages', [AdvisorController::class, 'clearMessages'])->name('advisor.messages.clear');
    Route::delete('/{workspace_id}/projects/{project_id}/editor/advisor/chats/{chat_id}/messages/{message_id}', [AdvisorController::class, 'deleteMessage'])->name('advisor.messages.delete');
    
    // Story context
    Route::get('/{workspace_id}/projects/{project_id}/editor/advisor/story-context', [AdvisorController::class, 'getStoryContext'])->name('advisor.story-context');
});
