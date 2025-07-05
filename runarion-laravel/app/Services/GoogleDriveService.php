<?php

namespace App\Services;

use App\Models\Workspace;
use Illuminate\Support\Facades\Storage;

class GoogleDriveService
{
    protected string $provider = 'google_drive';

    /**
     * Get a configured Google Drive disk for a workspace.
     */
    public function getDisk(string $workspaceId): ?\Illuminate\Contracts\Filesystem\Filesystem
    {
        $workspace = Workspace::find($workspaceId);

        if (!$workspace || !$workspace->isCloudConnected($this->provider)) {
            return null;
        }

        try {
            $refreshToken = $workspace->getCloudToken($this->provider);

            $config = [
                'driver'         => 'google_drive',
                'client_id'      => config('services.google.drive.client_id'),
                'client_secret'  => config('services.google.drive.client_secret'),
                'refresh_token'  => $refreshToken,
                'folder_id'      => $workspace->cloud_storage[$this->provider]['folder_id'] ?? null,
                'team_drive_id'  => $workspace->cloud_storage[$this->provider]['team_drive_id'] ?? null,
            ];

            return Storage::build($config);
        } catch (\Exception $e) {
            report($e);
            return null;
        }
    }

    /**
     * Check if Google Drive is connected for a workspace.
     */
    public function isConnected(string $workspaceId): bool
    {
        $workspace = Workspace::find($workspaceId);
        return $workspace?->isCloudConnected($this->provider) ?? false;
    }
}
