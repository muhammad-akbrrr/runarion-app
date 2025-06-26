<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Http;
use Google\Client as GoogleClient;

class CloudStorageController extends Controller
{
    private function canUpdate(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
        if ($userRole !== 'owner' && $userRole !== 'admin') {
            abort(403, 'You are not authorized to update this workspace.');
        }
    }

    public function googleRedirect(Request $request, string $workspace_id)
    {
        $this->canUpdate($request);

        $client = new GoogleClient();
        $client->setClientId(config('services.google.drive.client_id'));
        $client->setClientSecret(config('services.google.drive.client_secret'));
        $client->setRedirectUri(config('services.google.drive.redirect_uri'));
        $client->setScopes(config('services.google.drive.scopes'));
        $client->setAccessType('offline');
        $client->setPrompt('consent');
        $client->setState(json_encode(['workspace_id' => $workspace_id]));

        return redirect()->away($client->createAuthUrl());
    }

    public function dropboxRedirect(Request $request, string $workspace_id)
    {
        $this->canUpdate($request);

        $query = http_build_query([
            'client_id' => config('services.dropbox.client_id'),
            'response_type' => 'code',
            'redirect_uri' => config('services.dropbox.redirect_uri'),
            'state' => json_encode(['workspace_id' => $workspace_id]),
            'token_access_type' => 'offline',
        ]);

        return redirect()->away("https://www.dropbox.com/oauth2/authorize?{$query}");
    }

    public function googleCallback(Request $request)
    {
        if ($request->has('error')) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => json_decode($request->state)->workspace_id
            ])->with('error', 'Google Drive authorization was cancelled.');
        }

        $state = json_decode($request->state);
        $workspace_id = $state->workspace_id;

        // Verify user permission
        $userRole = DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
            ->where('user_id', $request->user()->id)
            ->value('role');

        if (!in_array($userRole, ['owner', 'admin'])) {
            abort(403, 'You are not authorized to update this workspace.');
        }

        $client = new GoogleClient();
        $client->setClientId(config('services.google.drive.client_id'));
        $client->setClientSecret(config('services.google.drive.client_secret'));
        $client->setRedirectUri(config('services.google.drive.redirect_uri'));

        $token = $client->fetchAccessTokenWithAuthCode($request->code);

        if (!isset($token['refresh_token'])) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspace_id
            ])->with('error', 'Failed to get refresh token. Please try again.');
        }

        $cloudStorage = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('cloud_storage');

        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        $cloudStorage['google_drive'] = [
            'enabled' => true,
            'connected_at' => now()->toIso8601String(),
            'token' => Crypt::encryptString($token['refresh_token']),
        ];

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update([
                'cloud_storage' => json_encode($cloudStorage),
            ]);

        return redirect()->route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspace_id
        ])->with('success', 'Google Drive connected successfully.');
    }

    public function dropboxCallback(Request $request)
    {
        if ($request->has('error')) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => json_decode($request->state)->workspace_id
            ])->with('error', 'Dropbox authorization was cancelled.');
        }

        $state = json_decode($request->state);
        $workspace_id = $state->workspace_id;

        $userRole = DB::table('workspace_members')
            ->where('workspace_id', $workspace_id)
            ->where('user_id', $request->user()->id)
            ->value('role');

        if (!in_array($userRole, ['owner', 'admin'])) {
            abort(403, 'You are not authorized to update this workspace.');
        }

        $response = Http::asForm()->post('https://api.dropboxapi.com/oauth2/token', [
            'code' => $request->code,
            'grant_type' => 'authorization_code',
            'client_id' => config('services.dropbox.client_id'),
            'client_secret' => config('services.dropbox.client_secret'),
            'redirect_uri' => config('services.dropbox.redirect_uri'),
        ]);

        $accessToken = $response['access_token'] ?? null;
        if (!$accessToken) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspace_id
            ])->with('error', 'Failed to retrieve access token.');
        }

        $cloudStorage = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('cloud_storage');

        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        $cloudStorage['dropbox'] = [
            'enabled' => true,
            'connected_at' => now()->toIso8601String(),
            'token' => Crypt::encryptString($accessToken),
        ];

        DB::table('workspaces')->where('id', $workspace_id)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return redirect()->route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspace_id
        ])->with('success', 'Dropbox connected successfully.');
    }

    public function googleDisconnect(Request $request, string $workspace_id)
    {
        $this->canUpdate($request);

        $cloudStorage = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('cloud_storage');

        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        if (!isset($cloudStorage['google_drive']) || !$cloudStorage['google_drive']['enabled']) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspace_id
            ])->with('info', 'Google Drive is not connected.');
        }

        // Try revoking token
        try {
            if (isset($cloudStorage['google_drive']['token'])) {
                $refreshToken = Crypt::decryptString($cloudStorage['google_drive']['token']);

                $client = new GoogleClient();
                $client->setClientId(config('services.google.drive.client_id'));
                $client->setClientSecret(config('services.google.drive.client_secret'));
                $client->revokeToken($refreshToken);
            }
        } catch (\Exception $e) {
            // Silent fail
        }

        // Clear google_drive settings
        unset($cloudStorage['google_drive']);

        DB::table('workspaces')
            ->where('id', $workspace_id)
            ->update([
                'cloud_storage' => json_encode($cloudStorage),
            ]);

        return redirect()->route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspace_id
        ])->with('success', 'Google Drive disconnected successfully.');
    }

    public function dropboxDisconnect(Request $request, string $workspace_id)
    {
        $this->canUpdate($request);

        $cloudStorage = DB::table('workspaces')
            ->where('id', $workspace_id)
            ->value('cloud_storage');

        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        if (!isset($cloudStorage['dropbox']) || !$cloudStorage['dropbox']['enabled']) {
            return redirect()->route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspace_id
            ])->with('info', 'Dropbox is not connected.');
        }

        unset($cloudStorage['dropbox']);

        DB::table('workspaces')->where('id', $workspace_id)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return redirect()->route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspace_id
        ])->with('success', 'Dropbox disconnected successfully.');
    }
}
