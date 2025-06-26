<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use App\Models\Workspace;
use App\Services\CloudStorage\CloudStorageProviderFactory;

class DashboardController extends Controller
{
    public function show(Request $request, string $workspace_id): Response
    {
        $workspace = Workspace::findOrFail($workspace_id);

        // determine enabled providers
        $storages = ['local'];
        foreach (['google_drive','dropbox'] as $provider) {
            if ($workspace->isCloudConnected($provider)) {
                $storages[] = $provider;
            }
        }

        return Inertia::render('Dashboard', [
            'workspaceId'      => $workspace_id,
            'storages'         => $storages,
            'filesByProvider'  => [],          // empty initially
        ]);
    }

    public function loadFiles(Request $request, string $workspace_id, string $provider): Response
    {
        $workspace = Workspace::findOrFail($workspace_id);

        // recompute enabled storage providers
        $storages = ['local'];
        foreach (['google_drive','dropbox'] as $prov) {
            if ($workspace->isCloudConnected($prov)) {
                $storages[] = $prov;
            }
        }

        // fetch files from the provider's filesystem
        try {
            $svc = CloudStorageProviderFactory::make($provider);
            $fs = $svc->filesystem($workspace_id);
            
            if ($provider === 'google_drive') {
                $contents = $fs->listContents('', false);
                $files = collect($contents)
                    ->filter(fn($e) => $e->type() === 'file')
                    ->map(function($e) {
                        return $e->path();
                    })
                    ->values()
                    ->toArray();
                
            } else {
                // For other providers, use the original approach
                $files = collect($fs->listContents('', true))
                    ->filter(fn($e) => $e->type() === 'file')
                    ->map(fn($e) => $e->path())
                    ->values()
                    ->toArray();
            }
        } catch (\Exception $e) {
            $files = [];
        }

        return Inertia::render('Dashboard', [
            'workspaceId'     => $workspace_id,
            'storages'        => $storages,
            'filesByProvider' => [ $provider => $files ],
        ]);
    }
}
