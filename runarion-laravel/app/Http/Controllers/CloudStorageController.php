<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Response;
use App\Services\CloudStorage\CloudStorageProviderFactory;

class CloudStorageController extends Controller
{
    private function canUpdate(Request $request): void
    {
        $userRole = $request->attributes->get('user_role');
        if (! in_array($userRole, ['owner', 'admin'])) {
            abort(403, 'Unauthorized.');
        }
    }

    public function redirect(Request $request, string $workspaceId, string $provider)
    {
        $this->canUpdate($request);
        $service = CloudStorageProviderFactory::make($provider);
        return $service->redirect($request, $workspaceId);
    }

    public function callback(Request $request, string $provider)
    {
        // callback itself does its own auth check / DB update
        $service = CloudStorageProviderFactory::make($provider);
        return $service->callback($request);
    }

    public function disconnect(Request $request, string $workspaceId, string $provider)
    {
        $this->canUpdate($request);
        $service = CloudStorageProviderFactory::make($provider);
        return $service->disconnect($request, $workspaceId);
    }
    
    public function listFiles(Request $request, string $workspaceId, string $provider)
    {
        $this->canUpdate($request);

        $service = CloudStorageProviderFactory::make($provider);
        $fs = $service->filesystem($workspaceId);

        $items = collect($fs->listContents('', false))
            ->map(fn($i) => [
                'path'     => $i->path(),
                'type'     => $i->type(),
                'modified' => $i->lastModified(),
                'size'     => $i->fileSize() ?? null,
            ]);

        return inertia('Cloud/StorageBrowser', [
            'workspaceId' => $workspaceId,
            'provider'    => $provider,
            'items'       => $items,
        ]);
    }

    public function upload(Request $request, string $workspaceId, string $provider)
    {
        $this->canUpdate($request);
        $request->validate(['file' => 'required|file']);

        $service = CloudStorageProviderFactory::make($provider);
        $fs = $service->filesystem($workspaceId);

        $file = $request->file('file');
        $path = 'uploads/'.time().'_'.$file->getClientOriginalName();

        $fs->writeStream($path, fopen($file->getRealPath(), 'r+'));

        return back()->with('success', "File uploaded to “{$path}”.");
    }

    public function download(Request $request, string $workspaceId, string $provider, string $path)
    {
        // read‐only, no need to check canUpdate
        $service = CloudStorageProviderFactory::make($provider);
        $fs = $service->filesystem($workspaceId);

        if (! $fs->fileExists($path)) {
            abort(404, 'File not found.');
        }

        $stream = $fs->readStream($path);

        return Response::stream(function() use ($stream) {
            fpassthru($stream);
        }, 200, [
            'Content-Type'        => $fs->mimeType($path),
            'Content-Length'      => $fs->fileSize($path),
            'Content-Disposition' => 'attachment; filename="'.basename($path).'"',
        ]);
    }

    public function delete(Request $request, string $workspaceId, string $provider, string $path)
    {
        $this->canUpdate($request);

        $service = CloudStorageProviderFactory::make($provider);
        $fs = $service->filesystem($workspaceId);

        if (! $fs->fileExists($path)) {
            return back()->with('error', 'File not found.');
        }

        $fs->delete($path);
        return back()->with('success', "Deleted “{$path}”.");
    }
}