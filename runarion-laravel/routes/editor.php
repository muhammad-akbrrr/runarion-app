<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProjectEditor\MainEditorController;

Route::middleware(['auth', 'workspace'])->group(function () {
	Route::get('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'editor'])->name('workspace.projects.editor');
	Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->name('editor.project.updateName');

	Route::get('/projects/{project_id}/editor', fn() => '')->name('raw.workspace.projects.editor');
});