<?php

namespace App\Services;

use App\Models\Workspace;
use Illuminate\Support\Facades\Storage;
use Illuminate\Contracts\Filesystem\Filesystem;

class WorkspaceDiskManager
{
    /**
     * Define available providers and their service classes.
     * Add DropboxService, OneDriveService, etc. here later.
     */
    protected array $providers = [
        'google_drive' => \App\Services\GoogleDriveService::class,
        // 'dropbox' => \App\Services\DropboxService::class,
        // 'onedrive' => \App\Services\OneDriveService::class,
    ];

    /**
     * Return the connected cloud disk for a workspace.
     */
    public function getDisk(string $workspaceId): Filesystem
    {
        $workspace = Workspace::find($workspaceId);

        if (!$workspace || !is_array($workspace->cloud_storage)) {
            return Storage::disk('local');
        }

        foreach ($this->providers as $provider => $serviceClass) {
            if (!empty($workspace->cloud_storage[$provider]['enabled'])) {
                $service = app($serviceClass);
                $disk = $service->getDisk($workspaceId);
                if ($disk) {
                    return $disk;
                }
            }
        }

        return Storage::disk('local');
    }

    /**
     * Return the disk based on project ID's workspace.
     */
    public function getProjectDisk(string $projectId): Filesystem
    {
        $workspaceId = \DB::table('projects')
            ->where('id', $projectId)
            ->value('workspace_id');

        return $workspaceId
            ? $this->getDisk($workspaceId)
            : Storage::disk('local');
    }

    /**
     * Returns the folder prefix used inside the disk for a project.
     */
    public function getProjectBasePath(string $projectId): string
    {
        return "projects/{$projectId}";
    }
}

