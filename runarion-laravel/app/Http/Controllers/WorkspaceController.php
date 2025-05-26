<?php

namespace App\Http\Controllers;

use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Storage;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function getUserRole(int $workspaceId, int $userId): ?string
    {
        return DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $userId)
            ->value('role');
    }

    private function getUserRoleCanView(int $workspaceId, int $userId): string
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole === null) {
            abort(403, 'You are not authorized to view this workspace.');
        }
        return $userRole;
    }

    private function canUpdate(int $workspaceId, int $userId): void
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole === 'member') {
            abort(403, 'You are not authorized to update this workspace.');
        }
    }

    private function canDestroy(int $workspaceId, int $userId): void
    {
        $userRole = $this->getUserRole($workspaceId, $userId);
        if ($userRole !== 'owner') {
            abort(403, 'You are not authorized to delete this workspace.');
        }
    }

    /**
     * Display all workspaces for the authenticated user.
     */
    public function index(Request $request): Response
    {
        $workspaces = DB::table('workspaces')
            ->join('workspace_members', 'workspaces.id', '=', 'workspace_members.workspace_id')
            ->where('workspace_members.user_id', $request->user()->id)
            ->select('workspaces.*', 'workspace_members.role')
            ->get()
            ->map(fn ($workspace) => [
                'id' => $workspace->id,
                'name' => $workspace->name,
                'slug' => $workspace->slug,
                'cover_image_url' => $workspace->cover_image_url,
                'role' => $workspace->role,
            ]);

        return Inertia::render('Workspace/List', [
            'workspaces' => $workspaces,
        ]);
    }

    /**
     * Display form to update the workspace.
     */
    public function edit(Request $request, int $workspace_id): Response
    {
        $userRole = $this->getUserRoleCanView($workspace_id, $request->user()->id);
        $isUserOwner = $userRole == 'owner';
        $isUserAdmin = $userRole == 'admin';

        $workspace = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->first(['id', 'name', 'slug', 'description', 'cover_image_url', 'settings', 'is_active']);
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $workspace->settings = json_decode($workspace->settings, true);
        $workspace->settings = [
            'timezone' => $workspace->settings['timezone'] ?? null,
            'permissions' => $workspace->settings['permissions'] ?? [],
        ];

        return Inertia::render('Workspace/Edit', [
            'workspace' => $workspace,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Display form to update cloud storage of the workspace.
     */
    public function editCloudStorage(Request $request, int $workspace_id): Response
    {
        $userRole = $this->getUserRoleCanView($workspace_id, $request->user()->id);
        $isUserOwner = $userRole == 'owner';
        $isUserAdmin = $userRole == 'admin';

        $settings = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('settings');
        if ($settings) {
            $settings = json_decode($settings, true);
        }
        
        $cloudStorage = $settings
            ? array_map(
                fn($m) => [
                    'enabled' => $m['enabled'],
                ],
                $settings['cloud_storage'] ?? []
            )
            : [];

        return Inertia::render('Workspace/CloudStorage', [
            'workspaceId' => $workspace_id,
            'data' => $cloudStorage,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Display form to update LLM of the workspace.
     */
    public function editLLM(Request $request, int $workspace_id): Response
    {
        $userRole = $this->getUserRoleCanView($workspace_id, $request->user()->id);
        $isUserOwner = $userRole == 'owner';
        $isUserAdmin = $userRole == 'admin';

        $settings = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('settings');
        if ($settings) {
            $settings = json_decode($settings, true);
        }
        
        $llm = [];
        if ($settings) {
            foreach ($settings['llm'] ?? [] as $key => $value) {
                $apiKeyExists = isset($value['api_key']) && $value['api_key'] !== "";
                $llm[$key] = [
                    'enabled' => $value['enabled'] && $apiKeyExists,
                    'api_key_exists' => $apiKeyExists,
                ];
            }
        }

        return Inertia::render('Workspace/LLM', [
            'workspaceId' => $workspace_id,
            'data' => $llm,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Display form to update billing of the workspace.
     */
    public function editBilling(Request $request, int $workspace_id): Response
    {
        return Inertia::render('Workspace/Billing', []);
    }

    /**
     * Create a new workspace.
     */
    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'slug' => [
                'required',
                'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/',
                'max:255',
                'unique:workspaces,slug'
            ],
            'photo' => 'nullable|image|max:2048',
        ]);

        $validated['cover_image_url'] = ($request->hasFile('photo') 
        ?   '/storage/' . Storage::disk('public')
                ->putFile('workspace_photos', $request->file('photo'))
        :   'https://ui-avatars.com/api/?' . http_build_query([
                'name' => $validated['name'],
                'background' => 'random',
            ]));
        unset($validated['photo']);

        $workspaceId = DB::table('workspaces')->insertGetId($validated);

        DB::table('workspace_members')->insert([
            'workspace_id' => $workspaceId,
            'user_id' => $request->user()->id,
            'role' => 'owner',
        ]);

        return Redirect::route('workspace.index');
    }

    /**
     * Update the workspace.
     */
    public function update(Request $request, $workspace_id): RedirectResponse
    {
        $this->canUpdate($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'string',
            'settings' => 'array',
            'settings.timezone' => 'string|max:255',
            'settings.permissions' => 'array',
            'settings.permissions.create_projects' => 'array',
            'settings.permissions.delete_projects' => 'array',
            'photo' => 'nullable|image|max:2048',
        ]);

        $settings = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('settings');
        $settings = $settings ? json_decode($settings, true) : [];
        $settings['timezone'] = $validated['settings']['timezone'] ?? $settings['timezone'] ?? null;
        $settings['permissions'] = $validated['settings']['permissions'] ?? $settings['permissions'] ?? [];
        $validated['settings'] = $settings;

        if ($request->hasFile('photo')) {
            $prevPhotoUrl = DB::table('workspaces')
                ->where('id', $workspace_id)
                ->value('cover_image_url');
            if ($prevPhotoUrl) {
                $prevPhotoUrl = substr($prevPhotoUrl, strlen('/storage/'));
                Storage::disk('public')->delete($prevPhotoUrl);
            }
            $validated['cover_image_url'] = '/storage/' . Storage::disk('public')
                ->putFile('workspace_photos', $request->file('photo'));
        }
        unset($validated['photo']);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($validated);

        return Redirect::route('workspace.edit', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update cloud storage of the workspace.
     */
    public function updateCloudStorage(Request $request, $workspace_id): RedirectResponse
    {
        $this->canUpdate($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'cloud_storage' => 'array',
            'cloud_storage.*' => 'array',
        ]);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update(['settings->cloud_storage' => $validated['cloud_storage']]);

        return Redirect::route('workspace.edit.cloud-storage', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update LLM of the workspace.
     */
    public function updateLLM(Request $request, $workspace_id): RedirectResponse
    {
        $this->canUpdate($workspace_id, $request->user()->id);

        $validated = $request->validate([
            'llm_key' => 'required|string',
            'enabled' => 'required|boolean',
            'api_key' => 'nullable|string',
            'delete_api_key' => 'nullable|boolean',
        ]);

        $llmKey = $validated['llm_key'];
        $enabled = $validated['enabled'];
        $apiKey = $validated['api_key'] ?? null;
        $deleteApiKey = $validated['delete_api_key'] ?? null;

        if ($enabled && $deleteApiKey) {
            abort(400, 'Cannot enable LLM with deleted API key.');
        }

        if ($deleteApiKey) {
            $updates = [
                "settings->llm->{$llmKey}" => [
                    'enabled' => false,
                    'api_key' => null,
                ]
            ];
        } elseif ($apiKey !== null && $apiKey !== '' && $enabled) {
            $updates = [
                "settings->llm->{$llmKey}" => [
                    'enabled' => true,
                    'api_key' => Crypt::encryptString($apiKey),
                ]
            ];
        } else {
            $updates = [
                "settings->llm->{$llmKey}->enabled" => $enabled,
            ];
        }

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($updates);

        return Redirect::route('workspace.edit.llm', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, $workspace_id): RedirectResponse
    {
        $this->canDestroy($workspace_id, $request->user()->id);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->delete();

        return Redirect::route('workspace.index');
    }
}
