<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Redirect;
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
}
