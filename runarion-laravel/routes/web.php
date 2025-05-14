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
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::patch('/profile/settings', [ProfileController::class, 'updateSettings'])->name('profile.update.settings');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

Route::middleware('auth')->group(function () {
    Route::get('/workspaces/{workspace_id}', [WorkspaceController::class, 'edit'])->name('workspaces.edit');
    Route::patch('/workspaces/{workspace_id}', [WorkspaceController::class, 'update'])->name('workspaces.update');
    Route::patch('/workspaces/{workspace_id}/settings', [WorkspaceController::class, 'updateSettings'])->name('workspaces.update.settings');
    Route::patch('/workspaces/{workspace_id}/billing', [WorkspaceController::class, 'updateBilling'])->name('workspaces.update.billing');
    Route::delete('/workspaces/{workspace_id}', [WorkspaceController::class, 'destroy'])->name('workspaces.destroy');
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
