<?php

namespace App\Http\Controllers;

use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

class WorkspaceController extends Controller
{
    private function canUpdate(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
        if ($userRole !== 'owner' && $userRole !== 'admin') {
            abort(403, 'You are not authorized to update this workspace.');
        }
    }

    private function canDestroy(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
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
            ->map(fn($workspace) => [
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
    public function edit(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $workspace = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->first(['id', 'name', 'slug', 'cover_image_url', 'timezone', 'permissions', 'is_active']);
        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $workspace->permissions = json_decode($workspace->permissions ?? '{}', true);

        return Inertia::render('Workspace/Edit', [
            'workspace' => $workspace,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Display form to update cloud storage of the workspace.
     */
    public function editCloudStorage(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $workspace = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->first(['id', 'cloud_storage']);

        if (!$workspace) {
            abort(401, 'Workspace not found.');
        }

        $cloudStorage = $workspace->cloud_storage ? json_decode($workspace->cloud_storage, true) : [];

        $cloudStorage = array_map(
            fn($m) => [
                'enabled' => $m['enabled'] ?? false,
                'connected_at' => $m['connected_at'] ?? null,
                'has_token' => isset($m['token']),
            ],
            $cloudStorage
        );

        return Inertia::render('Workspace/CloudStorage', [
            'workspaceId' => $workspace_id,
            'data' => $cloudStorage,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
            'flash' => [
                'success' => session('success'),
                'error' => session('error'),
                'info' => session('info'),
            ],
        ]);
    }

    /**
     * Display form to update LLM of the workspace.
     */
    public function editLLM(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        $llm = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('llm');

        $llm = $llm ? json_decode($llm, true) : [];

        foreach ($llm as $key => $value) {
            $apiKeyExists = isset($value['api_key']) && $value['api_key'] !== "";
            $llm[$key] = [
                'enabled' => $value['enabled'] && $apiKeyExists,
                'api_key_exists' => $apiKeyExists,
            ];
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
    public function editBilling(Request $request, string $workspace_id): RedirectResponse|Response
    {
        $userRole = $request->attributes->get('user_role');
        $isUserOwner = $userRole === 'owner';
        $isUserAdmin = $userRole === 'admin';

        return Inertia::render('Workspace/Billing', [
            'workspaceId' => $workspace_id,
            'isUserAdmin' => $isUserAdmin,
            'isUserOwner' => $isUserOwner,
        ]);
    }

    /**
     * Create a new workspace.
     */
    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'slug' => [
                'required',
                'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/',
                'max:255',
                'unique:workspaces,slug'
            ],
            'photo' => 'nullable|image|max:2048',
        ]);

        $workspaceId = Str::ulid()->toString();
        $validated['id'] = $workspaceId;

        $validated['cover_image_url'] = ($request->hasFile('photo')
            ? '/storage/' . Storage::disk('public')
                ->putFile('workspace_photos', $request->file('photo'))
            : 'https://ui-avatars.com/api/?' . http_build_query([
                'name' => $validated['name'],
                'background' => 'random',
            ]));
        unset($validated['photo']);


        DB::table('workspaces')->insert($validated);

        DB::table('workspace_members')->insert([
            'id' => Str::ulid()->toString(),
            'workspace_id' => $workspaceId,
            'user_id' => $request->user()->id,
            'role' => 'owner',
        ]);

        return Redirect::route('workspace.index');
    }

    /**
     * Update the workspace.
     */
    public function update(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'timezone' => 'nullable|string|max:255',
            'permissions' => 'array',
            'permissions.*' => 'array',
            'permissions.*.*' => 'in:admin,member,guest',
            'photo' => 'nullable|image|max:2048',
        ]);

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
    public function updateCloudStorage(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

        $validated = $request->validate([
            'cloud_storage' => 'array',
            'cloud_storage.*' => 'array',
        ]);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update($validated);

        return Redirect::route('workspace.edit.cloud-storage', ['workspace_id' => $workspace_id]);
    }

    /**
     * Update LLM of the workspace.
     */
    public function updateLLM(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

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

        $llm = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('llm');
        $llm = $llm ? json_decode($llm, true) : [];

        if ($deleteApiKey) {
            $llm[$llmKey] = [
                'enabled' => false,
                'api_key' => null,
            ];
        } elseif ($apiKey !== null && $apiKey !== '' && $enabled) {
            $llm[$llmKey] = [
                'enabled' => true,
                'api_key' => Crypt::encryptString($apiKey),
            ];
        } else {
            if (!isset($llm[$llmKey])) {
                $llm[$llmKey] = [
                    'enabled' => $enabled,
                    'api_key' => null,
                ];
            } else {
                $llm[$llmKey]['enabled'] = $enabled;
            }
        }

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update([
                'llm' => json_encode($llm),
            ]);

        return Redirect::route('workspace.edit.llm', ['workspace_id' => $workspace_id]);
    }

    /**
     * Delete the workspace.
     */
    public function destroy(Request $request, string $workspace_id): RedirectResponse
    {
        $this->canUpdate($request);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->delete();

        return Redirect::route('workspace.index');
    }
}
