<?php

namespace App\Services\CloudStorage;

use Illuminate\Http\Request;
use League\Flysystem\Filesystem;

interface CloudStorageProviderInterface
{
    public function redirect(Request $request, string $workspaceId);
    public function callback(Request $request);
    public function disconnect(Request $request, string $workspaceId);
    public function filesystem(string $workspaceId): Filesystem;
}
