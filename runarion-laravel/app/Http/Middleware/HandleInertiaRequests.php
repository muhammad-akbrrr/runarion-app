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

        $workspaces = $user ? DB::table('workspace_members')
            ->where('user_id', $user->id)
            ->join('workspaces', 'workspace_members.workspace_id', '=', 'workspaces.id')
            ->select('workspaces.id', 'workspaces.name', 'workspaces.slug')
            ->orderByRaw("CASE WHEN workspace_members.role = 'owner' THEN 1 ELSE 2 END")
            ->orderBy('workspaces.name')
            ->get() : [];

        $shared = array_merge(parent::share($request), [
            'auth' => [
                'user' => $user,
                'csrf_token' => csrf_token(),
            ],
            'workspaces' => $workspaces,
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
            \Log::error('Error loading Ziggy: ' . $e->getMessage());
        }

        return $shared;
    }

    /**
     * Handle an incoming request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Closure  $next
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
