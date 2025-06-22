<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProjectEditor\MainEditorController;
use App\Http\Controllers\ProjectEditor\ProjectDatabaseController;
use App\Http\Controllers\ProjectEditor\MultiPromptController;
use App\Http\Controllers\ProjectEditor\ImageGeneratorController;

Route::middleware(['auth', 'project-editor'])->group(function () {
    // Main editor routes
    Route::get('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'editor'])->name('workspace.projects.editor');
    Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->name('editor.project.updateName');
    Route::post('/{workspace_id}/projects/{project_id}/editor/generate', [MainEditorController::class, 'generate'])->name('workspace.projects.editor.generate');
    
    // Content management routes
    Route::post('/{workspace_id}/projects/{project_id}/editor/save', [MainEditorController::class, 'saveContent'])->name('workspace.projects.editor.save');
    Route::get('/{workspace_id}/projects/{project_id}/editor/content', [MainEditorController::class, 'loadContent'])->name('workspace.projects.editor.content');

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