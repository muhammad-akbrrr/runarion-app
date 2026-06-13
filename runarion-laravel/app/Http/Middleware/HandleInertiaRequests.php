<?php

namespace App\Http\Middleware;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Inertia\Middleware;
use Tighten\Ziggy\Ziggy;

class HandleInertiaRequests extends Middleware
{
    /**
     * The root template that is loaded on the first page visit.
     *
     * @var string
     */
    protected $rootView = 'app';

    /**
     * Determine the current asset version.
     */
    public function version(Request $request): ?string
    {
        return parent::version($request);
    }

    /**
     * Define the props that are shared by default.
     *
     * @return array<string, mixed>
     */
    public function share(Request $request): array
    {
        $user = $request->user();
        $activeWorkspaceId = $request->route('workspace_id') ?: $user?->last_workspace_id;

        $workspaces = $user ? DB::table('workspace_members')
            ->where('user_id', $user->id)
            ->join('workspaces', 'workspace_members.workspace_id', '=', 'workspaces.id')
            ->select('workspaces.id', 'workspaces.name', 'workspaces.slug', 'workspaces.cover_image_url')
            ->orderByRaw("CASE WHEN workspace_members.role = 'owner' THEN 1 ELSE 2 END")
            ->orderBy('workspaces.name')
            ->get() : [];

        $shared = array_merge(parent::share($request), [
            'auth' => [
                'user' => $user,
                'csrf_token' => csrf_token(),
            ],
            'workspaces' => $workspaces,
            'favorite_projects' => $user && $activeWorkspaceId
                ? $this->resolveFavoriteProjects($user->highlighted_projects ?? [], $activeWorkspaceId)
                : [],
            'flash' => [
                'success' => fn () => $request->session()->get('success'),
                'error' => fn () => $request->session()->get('error'),
                'info' => fn () => $request->session()->get('info'),
                'warning' => fn () => $request->session()->get('warning'),
            ],
        ]);

        try {
            if (class_exists(Ziggy::class)) {
                $ziggy = new Ziggy;
                $shared['ziggy'] = [
                    'location' => $request->url(),
                    'query' => $request->query(),
                    'url' => $request->url(),
                    'port' => $request->getPort(),
                    'defaults' => [],
                    'routes' => $ziggy->toArray(),
                ];
            }
        } catch (\Exception $e) {
            // Log the error but don't break the application
            \Log::error('Error loading Ziggy: '.$e->getMessage());
        }

        return $shared;
    }

    /**
     * @param  array<int, array<string, mixed>>  $highlightedProjects
     * @return array<int, array{id: string, name: string, workspace_id: string}>
     */
    private function resolveFavoriteProjects(array $highlightedProjects, string $workspaceId): array
    {
        $workspaceFavorites = collect($highlightedProjects)
            ->filter(fn ($project) => ($project['workspace_id'] ?? null) === $workspaceId)
            ->values();

        if ($workspaceFavorites->isEmpty()) {
            return [];
        }

        $projectMap = DB::table('projects')
            ->where('workspace_id', $workspaceId)
            ->where('is_active', true)
            ->whereIn('id', $workspaceFavorites->pluck('project_id')->all())
            ->select('id', 'name', 'workspace_id')
            ->get()
            ->keyBy('id');

        return $workspaceFavorites
            ->map(function (array $favorite) use ($projectMap) {
                $project = $projectMap->get($favorite['project_id'] ?? null);

                if (! $project) {
                    return null;
                }

                return [
                    'id' => $project->id,
                    'name' => $project->name,
                    'workspace_id' => $project->workspace_id,
                ];
            })
            ->filter()
            ->values()
            ->all();
    }

    /**
     * Handle an incoming request.
     *
     * @return mixed
     */
    public function handle(Request $request, \Closure $next)
    {
        $response = parent::handle($request, $next);

        // Add CORS headers to the response
        $response->headers->set('Access-Control-Allow-Origin', 'http://localhost:5173');
        $response->headers->set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
        $response->headers->set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-TOKEN');
        $response->headers->set('Access-Control-Allow-Credentials', 'true');

        return $response;
    }
}
