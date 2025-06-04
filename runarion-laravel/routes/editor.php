<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProjectEditor\MainEditorController;

Route::middleware(['auth', 'workspace'])->group(function () {
  Route::patch('/{workspace_id}/projects/{project_id}/editor', [MainEditorController::class, 'updateProjectName'])->name('editor.project.updateName');
});