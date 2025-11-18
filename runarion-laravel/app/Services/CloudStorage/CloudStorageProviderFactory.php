<?php

namespace App\Services\CloudStorage;

use App\Services\CloudStorage\Providers\GoogleDriveProvider;
use App\Services\CloudStorage\Providers\DropboxProvider;
use App\Services\CloudStorage\Providers\OneDriveProvider;
use InvalidArgumentException;

class CloudStorageProviderFactory
{
    public static function make(string $provider): CloudStorageProviderInterface
    {
        // Normalize to underscore
        $provider = str_replace('-', '_', $provider);

        return match ($provider) {
            'google_drive' => new GoogleDriveProvider(),
            'dropbox' => new DropboxProvider(),
            'onedrive' => new OneDriveProvider(),
            default => throw new InvalidArgumentException("Invalid cloud storage provider: {$provider}")
        };
    }
}
