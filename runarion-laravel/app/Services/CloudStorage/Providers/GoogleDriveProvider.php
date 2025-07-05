<?php

namespace App\Services\CloudStorage\Providers;

use App\Services\CloudStorage\CloudStorageProviderInterface;
use App\Models\Workspace;
use Google\Client as GoogleClient;
use Google\Service\Drive;
use Google\Service\Drive\DriveFile;
use Masbug\Flysystem\GoogleDriveAdapter;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Log;
use League\Flysystem\Filesystem;

class GoogleDriveProvider implements CloudStorageProviderInterface
{
    const FOLDER_NAME = 'runarion-drive-folder';

    public function redirect(Request $request, string $workspaceId)
    {
        $client = new GoogleClient();
        $client->setClientId(config('services.google.drive.client_id'));
        $client->setClientSecret(config('services.google.drive.client_secret'));
        $client->setRedirectUri(config('services.google.drive.redirect_uri'));
        $client->setScopes(config('services.google.drive.scopes'));
        $client->setAccessType('offline');
        $client->setPrompt('consent');
        $client->setState(json_encode(['workspace_id' => $workspaceId]));

        return redirect()->away($client->createAuthUrl());
    }

    public function callback(Request $request)
    {
        if ($request->has('error')) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => json_decode($request->state)->workspace_id,
            ])->with('error', 'Google Drive authorization was cancelled.');
        }

        $state       = json_decode($request->state);
        $workspaceId = $state->workspace_id;

        // Permission check
        $userRole = DB::table('workspace_members')
            ->where('workspace_id', $workspaceId)
            ->where('user_id', $request->user()->id)
            ->value('role');

        if (!in_array($userRole, ['owner', 'admin'])) {
            abort(403, 'You are not authorized to update this workspace.');
        }

        // Get access token
        $client = new GoogleClient();
        $client->setClientId(config('services.google.drive.client_id'));
        $client->setClientSecret(config('services.google.drive.client_secret'));
        $client->setRedirectUri(config('services.google.drive.redirect_uri'));

        $token = $client->fetchAccessTokenWithAuthCode($request->code);

        if (empty($token['refresh_token'])) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspaceId,
            ])->with('error', 'Failed to get refresh token. Please try again.');
        }

        // Setup Drive service
        $client->setAccessType('offline');
        $client->setPrompt('consent');
        $client->refreshToken($token['refresh_token']);
        $driveService = new Drive($client);

        // Check if folder already exists
        $query = "name = '" . self::FOLDER_NAME . "' and mimeType = 'application/vnd.google-apps.folder' and trashed = false";
        $results = $driveService->files->listFiles([
            'q' => $query,
            'spaces' => 'drive',
            'fields' => 'files(id, name)',
        ]);

        if (count($results->getFiles()) > 0) {
            $folderId = $results->getFiles()[0]->getId();
        } else {
            // Create the folder
            $folderMetadata = new DriveFile([
                'name' => self::FOLDER_NAME,
                'mimeType' => 'application/vnd.google-apps.folder',
            ]);

            $createdFolder = $driveService->files->create($folderMetadata, [
                'fields' => 'id',
            ]);

            $folderId = $createdFolder->id;
        }

        // Save only refresh token, not folder ID (since it's global)
        $cloudStorage = DB::table('workspaces')
            ->where('id', $workspaceId)
            ->value('cloud_storage');

        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];
        $cloudStorage['google_drive'] = [
            'enabled'        => true,
            'connected_at'   => now()->toIso8601String(),
            'refresh_token'  => Crypt::encryptString($token['refresh_token']),
            'folder_id'      => $folderId, // Store the folder ID for reference
        ];

        DB::table('workspaces')->where('id', $workspaceId)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return Redirect::route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspaceId,
        ])->with('success', 'Google Drive connected successfully.');
    }

    public function disconnect(Request $request, string $workspaceId)
    {
        $cloudStorage = DB::table('workspaces')->where('id', $workspaceId)->value('cloud_storage');
        $cloudStorage = $cloudStorage ? json_decode($cloudStorage, true) : [];

        if (!isset($cloudStorage['google_drive']) || !$cloudStorage['google_drive']['enabled']) {
            return Redirect::route('workspace.edit.cloud-storage', [
                'workspace_id' => $workspaceId
            ])->with('info', 'Google Drive is not connected.');
        }

        try {
            $refreshToken = Crypt::decryptString($cloudStorage['google_drive']['refresh_token']);
            $client = new GoogleClient();
            $client->setClientId(config('services.google.drive.client_id'));
            $client->setClientSecret(config('services.google.drive.client_secret'));
            $client->revokeToken($refreshToken);
        } catch (\Exception $e) {
            // Silent fail
        }

        unset($cloudStorage['google_drive']);

        DB::table('workspaces')->where('id', $workspaceId)->update([
            'cloud_storage' => json_encode($cloudStorage),
        ]);

        return Redirect::route('workspace.edit.cloud-storage', [
            'workspace_id' => $workspaceId
        ])->with('success', 'Google Drive disconnected successfully.');
    }

    public function filesystem(string $workspaceId): Filesystem
    {
        $workspace = Workspace::findOrFail($workspaceId);

        $data = $workspace->cloud_storage['google_drive'] ?? null;
        if (! $data['enabled'] ?? false) {
            throw new \RuntimeException("Google Drive not connected on workspace {$workspaceId}");
        }

        $refreshToken = Crypt::decryptString($data['refresh_token']);

        $client = new GoogleClient();
        $client->setClientId(config('services.google.drive.client_id'));
        $client->setClientSecret(config('services.google.drive.client_secret'));
        $client->setAccessType('offline');
        $client->setPrompt('consent');
        $client->refreshToken($refreshToken);

        $service = new Drive($client);

        // Fetch the shared folder ID - first check if we have it stored
        $folderId = $data['folder_id'] ?? null;
        
        if (!$folderId) {
            // If not stored, try to find it
            $query = "name = '" . self::FOLDER_NAME . "' and mimeType = 'application/vnd.google-apps.folder' and trashed = false";
            $results = $service->files->listFiles([
                'q' => $query,
                'spaces' => 'drive',
                'fields' => 'files(id, name)',
            ]);

            if (count($results->getFiles()) === 0) {
                // Create the folder if it doesn't exist
                $folderMetadata = new DriveFile([
                    'name' => self::FOLDER_NAME,
                    'mimeType' => 'application/vnd.google-apps.folder',
                ]);

                $createdFolder = $service->files->create($folderMetadata, [
                    'fields' => 'id',
                ]);

                $folderId = $createdFolder->id;
                
                // Store the folder ID for future use
                $cloudStorage = $workspace->cloud_storage;
                $cloudStorage['google_drive']['folder_id'] = $folderId;
                $workspace->cloud_storage = $cloudStorage;
                $workspace->save();
                
                Log::info("Created Google Drive folder with ID: {$folderId}");
            } else {
                $folderId = $results->getFiles()[0]->getId();
                
                // Store the folder ID for future use
                $cloudStorage = $workspace->cloud_storage;
                $cloudStorage['google_drive']['folder_id'] = $folderId;
                $workspace->cloud_storage = $cloudStorage;
                $workspace->save();
                
                Log::info("Found existing Google Drive folder with ID: {$folderId}");
            }
        }

        // Debug log to check what files are in the folder
        try {
            $filesList = $service->files->listFiles([
                'q' => "'{$folderId}' in parents and trashed = false",
                'spaces' => 'drive',
                'fields' => 'files(id, name, mimeType)',
            ]);
            
            Log::info("Files in Google Drive folder:", [
                'folder_id' => $folderId,
                'file_count' => count($filesList->getFiles()),
                'files' => array_map(function($file) {
                    return [
                        'id' => $file->getId(),
                        'name' => $file->getName(),
                        'mimeType' => $file->getMimeType(),
                    ];
                }, $filesList->getFiles())
            ]);
        } catch (\Exception $e) {
            Log::error("Error listing Google Drive files: " . $e->getMessage());
        }

        // Configure the adapter with proper options
        $adapter = new GoogleDriveAdapter($service, $folderId);

        return new Filesystem($adapter);
    }
}
