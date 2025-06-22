<?php

namespace App\Http\Controllers;

use App\Models\GenerationLog;
use App\Models\Workspace;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

class DashboardController extends Controller
{
    public function show(Request $request, string $workspace_id): Response
    {
        $workspace = Workspace::findOrFail($workspace_id);

        $generationLogs = GenerationLog::with(['user', 'project'])
            ->where('workspace_id', $workspace_id)
            ->latest('created_at')
            ->take(10)
            ->get()
            ->map(function ($log) {
                return [
                    'request_id' => $log->request_id,
                    'provider' => $log->provider,
                    'model_used' => $log->model_used,
                    'total_tokens' => $log->total_tokens ?? 0,
                    'processing_time_ms' => $log->processing_time_ms ?? 0,
                    'success' => $log->success,
                    'created_at' => $log->created_at->toDateTimeString(),
                    'user' => [
                        'name' => optional($log->user)->name ?? 'Unknown',
                    ],
                    'project' => [
                        'name' => optional($log->project)->name ?? 'N/A',
                    ],
                ];
            });

        $quotaManager = [
            'remaining' => $workspace->quota,
            'limit' => $workspace->monthly_quota,
            'usage' => max(0, $workspace->monthly_quota - $workspace->quota)
        ];

        return Inertia::render('Dashboard', [
            'workspaceId' => $workspace_id,
            'generationLogs' => $generationLogs,
            'quotaManager' => $quotaManager
        ]);
    }
}