<?php

namespace App\Services;

use App\Models\Workspace;
use Illuminate\Support\Facades\Storage;
use Illuminate\Contracts\Filesystem\Filesystem;

class DropboxService
{
    protected string $provider = 'dropbox';

    public function getDisk(string $workspaceId): ?Filesystem
    {
        $workspace = Workspace::find($workspaceId);

        if (!$workspace || !$workspace->isCloudConnected($this->provider)) {
            return null;
        }

        try {
            $accessToken = $workspace->getCloudToken($this->provider);

            $config = [
                'driver' => 'dropbox',
                'token' => $accessToken,
            ];

            return Storage::build($config);
        } catch (\Exception $e) {
            report($e);
            return null;
        }
    }

    public function isConnected(string $workspaceId): bool
    {
        $workspace = Workspace::find($workspaceId);
        return $workspace?->isCloudConnected($this->provider) ?? false;
    }
}
