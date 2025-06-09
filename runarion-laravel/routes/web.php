<?php

use Inertia\Inertia;
use Illuminate\Support\Facades\Route;
use Illuminate\Foundation\Application;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\WorkspaceController;
use App\Http\Controllers\WorkspaceMemberController;
use App\Http\Controllers\ProjectController;

Route::get('/', function () {
    return Inertia::render('Welcome', [
        'canLogin' => Route::has('login'),
        'canRegister' => Route::has('register'),
        'laravelVersion' => Application::VERSION,
        'phpVersion' => PHP_VERSION,
    ]);
});

// Dashboard Routes
Route::middleware(['auth', 'workspace'])->group(function () {
    Route::get('/{workspace_id}/dashboard', [DashboardController::class, 'show'])->name('workspace.dashboard');

    Route::get('/dashboard', fn() => '')->name('raw.workspace.dashboard');
});

// Projects Routes
Route::middleware(['auth', 'workspace'])->group(function () {
    Route::get('/{workspace_id}/projects', [ProjectController::class, 'show'])->name('workspace.projects');
    Route::post('/{workspace_id}/projects/folder', [ProjectController::class, 'storeFolder'])->name('workspace.folders.store');
    Route::post('/{workspace_id}/projects', [ProjectController::class, 'storeProject'])->name('workspace.projects.store');
    Route::get('/{workspace_id}/projects/folder/{folder_id}', [ProjectController::class, 'openFolder'])->name('workspace.folders.open');
    Route::delete('/{workspace_id}/projects/{project_id}', [ProjectController::class, 'destroyProject'])->name('workspace.projects.destroy');
    Route::delete('/{workspace_id}/projects/folder/{folder_id}', [ProjectController::class, 'destroyFolder'])->name('workspace.folders.destroy');

    Route::get('/projects', fn() => '')->name('raw.workspace.projects');
    Route::get('/projects/folder/{folder_id}', fn() => '')->name('raw.workspace.folders.open');
});

// Project Settings Routes
Route::middleware(['auth', 'workspace'])->group(function () {
    Route::get('/{workspace_id}/projects/{project_id}/settings', [ProjectController::class, 'settings'])->name('workspace.projects.edit');
    Route::patch('/{workspace_id}/projects/{project_id}/settings', [ProjectController::class, 'update'])->name('workspace.projects.update');
    Route::get('/{workspace_id}/projects/{project_id}/settings/access', [ProjectController::class, 'access'])->name('workspace.projects.edit.access');
    Route::patch('/{workspace_id}/projects/{project_id}/settings/access', [ProjectController::class, 'updateMemberRole'])->name('workspace.projects.update.member.role');
    Route::delete('/{workspace_id}/projects/{project_id}/settings/access', [ProjectController::class, 'removeMember'])->name('workspace.projects.remove.member');
    Route::get('/{workspace_id}/projects/{project_id}/settings/backups', [ProjectController::class, 'backups'])->name('workspace.projects.edit.backups');
    Route::get('/{workspace_id}/projects/{project_id}/settings/activity', [ProjectController::class, 'activity'])->name('workspace.projects.edit.activity');

    Route::get('/projects/{project_id}/settings', fn() => '')->name('raw.workspace.projects.edit');
    Route::get('/projects/{project_id}/settings/access', fn() => '')->name('raw.workspace.projects.edit.access');
    Route::get('/projects/{project_id}/settings/backups', fn() => '')->name('raw.workspace.projects.edit.backups');
    Route::get('/projects/{project_id}/settings/activity', fn() => '')->name('raw.workspace.projects.edit.activity');
});

// User Settings Routes
Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::post('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');

    Route::get('/workspaces', [WorkspaceController::class, 'index'])->name('workspace.index');
    Route::post('/workspaces', [WorkspaceController::class, 'store'])->name('workspace.store');
});

// Workspace Settings Routes
Route::middleware(['auth', 'workspace'])->group(function () {
    Route::get('/{workspace_id}/settings', [WorkspaceController::class, 'edit'])->name('workspace.edit');
    Route::post('/{workspace_id}/settings', [WorkspaceController::class, 'update'])->name('workspace.update');
    Route::get('/{workspace_id}/settings/cloud-storage', [WorkspaceController::class, 'editCloudStorage'])->name('workspace.edit.cloud-storage');
    Route::patch('/{workspace_id}/settings/cloud-storage', [WorkspaceController::class, 'updateCloudStorage'])->name('workspace.update.cloud-storage');
    Route::get('/{workspace_id}/settings/llm', [WorkspaceController::class, 'editLLM'])->name('workspace.edit.llm');
    Route::patch('/{workspace_id}/settings/llm', [WorkspaceController::class, 'updateLLM'])->name('workspace.update.llm');
    Route::get('/{workspace_id}/settings/billing', [WorkspaceController::class, 'editBilling'])->name('workspace.edit.billing');
    Route::delete('/{workspace_id}', [WorkspaceController::class, 'destroy'])->name('workspace.destroy');

    Route::get('/settings', fn() => '')->name('raw.workspace.edit');
    Route::get('/settings/cloud-storage', fn() => '')->name('raw.workspace.edit.cloud-storage');
    Route::get('/settings/llm', fn() => '')->name('raw.workspace.edit.llm');
    Route::get('/settings/billing', fn() => '')->name('raw.workspace.edit.billing');
});

// Workspace Members Routes
Route::middleware(['auth', 'workspace'])->group(function () {
    Route::get('/{workspace_id}/settings/members', [WorkspaceMemberController::class, 'edit'])->name('workspace.edit.member');
    Route::get('/{workspace_id}/settings/members/unassigned', [WorkspaceMemberController::class, 'unassigned'])->name('workspace.index.member.unassigned');
    Route::post('/{workspace_id}/settings/members', [WorkspaceMemberController::class, 'assign'])->name('workspace.assign.member');
    Route::patch('/{workspace_id}/settings/members', [WorkspaceMemberController::class, 'update'])->name('workspace.update.member');
    Route::delete('/{workspace_id}/settings/members', [WorkspaceMemberController::class, 'remove'])->name('workspace.remove.member');
    Route::delete('/{workspace_id}/leave', [WorkspaceMemberController::class, 'leave'])->name('workspace.leave');

    Route::get('/settings/members', fn() => '')->name('raw.workspace.edit.member');
});

// Workspace invitation accept route (no auth required)
Route::get('/workspace-invitation/{token}', [WorkspaceMemberController::class, 'accept'])->name('workspace-invitation.accept');

require __DIR__ . '/auth.php';
require __DIR__ . '/editor.php';
