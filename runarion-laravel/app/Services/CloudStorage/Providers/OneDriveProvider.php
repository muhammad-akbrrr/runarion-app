<?php

namespace App\Services\CloudStorage\Providers;

use App\Services\CloudStorage\CloudStorageProviderInterface;
use App\Models\Workspace;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Http;
use Justus\FlysystemOneDrive\OneDriveAdapter;
use League\Flysystem\Filesystem;

class OneDriveProvider implements CloudStorageProviderInterface
{
    public function redirect(Request $request, string $workspaceId)
    {
        $query = http_build_query([
            'client_id' => config('services.onedrive.client_id'),
            'response_type' => 'code',
            'redirect_uri' => config('services.onedrive.redirect_uri'),
            'scope' => implode(' ', config('services.onedrive.scopes')),
            'state' => json_encode(['workspace_id' => $workspaceId]),
        ]);

        return redirect()->away("https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{$query}");
    }

    public function callback(Request $request)
    {
        if ($request->has('error')) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => json_decode($request->state)->workspace_id,
            ])->with('error', 'OneDrive authorization was cancelled.');
        }

        $state = json_decode($request->state);
        $workspaceId = $state->workspace_id;

        // Check user permission
        $userRole = DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $request->user()->id)
            ->value('role');

        if (!in_array($userRole, ['owner', 'admin'])) {
            abort(403, 'You are not authorized to update this workspace.');
        }

        $response = Http::asForm()->post('https://login.microsoftonline.com/common/oauth2/v2.0/token', [
            'code' => $request->code,
            'grant_type' => 'authorization_code',
            'client_id' => config('services.onedrive.client_id'),
            'client_secret' => config('services.onedrive.client_secret'),
            'redirect_uri' => config('services.onedrive.redirect_uri'),
            'scope' => implode(' ', config('services.onedrive.scopes')),
        ]);

        $accessToken = $response['access_token'] ?? null;
        if (!$accessToken) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspaceId
            ])->with('error', 'Failed to retrieve access token.');
        }

        $cloudStorage = DB::table('workspaces')->where('id', $workspaceId)->value('cloud_storage');
        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        $cloudStorage['onedrive'] = [
            'enabled' => true,
            'connected_at' => now()->toIso8601String(),
            'token' => Crypt::encryptString($accessToken),
        ];

        DB::table('workspaces')->where('id', $workspaceId)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return Redirect::route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspaceId
        ])->with('success', 'OneDrive connected successfully.');
    }

    public function disconnect(Request $request, string $workspaceId)
    {
        $cloudStorage = DB::table('workspaces')->where('id', $workspaceId)->value('cloud_storage');
        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        if (!isset($cloudStorage['onedrive']) || !$cloudStorage['onedrive']['enabled']) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspaceId
            ])->with('info', 'OneDrive is not connected.');
        }

        unset($cloudStorage['onedrive']);

        DB::table('workspaces')->where('id', $workspaceId)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return Redirect::route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspaceId
        ])->with('success', 'OneDrive disconnected successfully.');
    }

    public function filesystem(string $workspaceId): Filesystem
    {
        $workspace = Workspace::findOrFail($workspaceId);

        $data = $workspace->cloud_storage['onedrive'] ?? null;
        if (! $data['enabled'] ?? false) {
            throw new \RuntimeException("OneDrive not connected on workspace {$workspaceId}");
        }

        $token = Crypt::decryptString($data['token']);
        $adapter = new OneDriveAdapter($token);

        return new Filesystem($adapter);
    }
}
