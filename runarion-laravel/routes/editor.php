<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProjectEditor\MainEditorController;
use App\Http\Controllers\ProjectEditor\ProjectDatabaseController;
use App\Http\Controllers\ProjectEditor\MultiPromptController;
use App\Http\Controllers\ProjectEditor\ImageGeneratorController;

Route::middleware(['auth', 'project-editor'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'editor'])->name('workspace.projects.editor');
    Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->name('editor.project.updateName');
    Route::post('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'projectOnboarding'])->name('editor.project.onboarding');
    Route::post('/{workspace_id}/projects/{project_id}/editor/chapter', [MainEditorController::class, 'storeProjectChapter'])->name('editor.project.chapter');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/data', [MainEditorController::class, 'updateProjectData'])->name('editor.project.updateData');
    Route::patch('/{workspace_id}/projects/{project_id}/editor/settings', [MainEditorController::class, 'updateProjectSettings'])->name('editor.project.updateSettings');
    Route::post('/{workspace_id}/projects/{project_id}/editor/generate', [MainEditorController::class, 'generateText'])->name('editor.project.generate');
    Route::post('/{workspace_id}/projects/{project_id}/editor/cancel-generation', [MainEditorController::class, 'cancelGeneration'])->name('editor.project.cancel-generation');

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
