<?php

namespace App\Http\Middleware;

use App\Services\ProjectOperationStateService;
use Closure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class RejectLockedProjectMutations
{
    public function __construct(
        private readonly ProjectOperationStateService $operationStateService,
    ) {}

    public function handle(Request $request, Closure $next): Response
    {
        if (in_array($request->method(), ['GET', 'HEAD', 'OPTIONS'], true)) {
            return $next($request);
        }

        $workspaceId = $request->route('workspace_id');
        $projectId = $request->route('project_id');

        if (! $workspaceId || ! $projectId) {
            return $next($request);
        }

        $lock = $this->operationStateService->getProjectLock($workspaceId, $projectId);
        if (! $lock) {
            return $next($request);
        }

        $message = $lock['message'] ?? 'This project is locked by an active operation. Please wait for it to finish before making changes.';

        if ($request->expectsJson() || $request->wantsJson() || $request->ajax()) {
            return new JsonResponse([
                'message' => $message,
                'error' => $message,
                'lock' => $lock,
            ], 423);
        }

        return back()->withErrors([
            'project_lock' => $message,
        ]);
    }
}
