<?php

namespace App\Services\CloudStorage;

use App\Services\CloudStorage\Providers\GoogleDriveProvider;
use App\Services\CloudStorage\Providers\DropboxProvider;
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
            default => throw new InvalidArgumentException("Invalid cloud storage provider: {$provider}")
        };
    }
}
