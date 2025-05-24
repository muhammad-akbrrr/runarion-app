<?php

use App\Http\Controllers\ProfileController;
use App\Http\Controllers\WorkspaceController;
use App\Http\Controllers\WorkspaceMemberController;
use Illuminate\Foundation\Application;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::get('/', function () {
    return Inertia::render('Welcome', [
        'canLogin' => Route::has('login'),
        'canRegister' => Route::has('register'),
        'laravelVersion' => Application::VERSION,
        'phpVersion' => PHP_VERSION,
    ]);
});

Route::get('/dashboard', function () {
    return Inertia::render('Dashboard');
})->middleware(['auth', 'verified'])->name('dashboard');

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::post('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

Route::middleware('auth')->group(function () {
    Route::get('/workspaces', [WorkspaceController::class, 'index'])->name('workspace.index');
    Route::post('/workspaces', [WorkspaceController::class, 'store'])->name('workspace.store');
    Route::get('/workspaces/{workspace_id}', [WorkspaceController::class, 'edit'])->name('workspace.edit');
    Route::post('/workspaces/{workspace_id}', [WorkspaceController::class, 'update'])->name('workspace.update');
    Route::get('/workspaces/{workspace_id}/cloud-storage', [WorkspaceController::class, 'editCloudStorage'])->name('workspace.edit.cloud-storage');
    Route::patch('/workspaces/{workspace_id}/cloud-storage', [WorkspaceController::class, 'updateCloudStorage'])->name('workspace.update.cloud-storage');
    Route::get('/workspaces/{workspace_id}/llm', [WorkspaceController::class, 'editLLM'])->name('workspace.edit.llm');
    Route::patch('/workspaces/{workspace_id}/llm', [WorkspaceController::class, 'updateLLM'])->name('workspace.update.llm');
    Route::get('/workspaces/{workspace_id}/billing', [WorkspaceController::class, 'editBilling'])->name('workspace.edit.billing');
    Route::delete('/workspaces/{workspace_id}', [WorkspaceController::class, 'destroy'])->name('workspace.destroy');
});

Route::middleware('auth')->group(function () {
    Route::get('/workspace-members/{workspace_id}/unassigned', [WorkspaceMemberController::class, 'unassigned'])->name('workspace-members.unassigned');
    Route::post('/workspace-members', [WorkspaceMemberController::class, 'assign'])->name('workspace-members.assign');
    Route::patch('/workspace-members', [WorkspaceMemberController::class, 'update'])->name('workspace-members.update');
    Route::delete('/workspace-members', [WorkspaceMemberController::class, 'remove'])->name('workspace-members.remove');
    Route::delete('/workspace-members/{workspace_id}', [WorkspaceMemberController::class, 'leave'])->name('workspace-members.leave');
});

// Workspace invitation accept route (no auth required)
Route::get('/workspace-invitation/{token}', [WorkspaceMemberController::class, 'accept'])->name('workspace-invitation.accept');

require __DIR__.'/auth.php';
