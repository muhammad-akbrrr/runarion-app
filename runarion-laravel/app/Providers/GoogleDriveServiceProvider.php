<?php

namespace App\Providers;

use Illuminate\Support\Facades\Storage;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Crypt;
use Masbug\Flysystem\GoogleDriveAdapter;
use Google\Client as GoogleClient;
use Google\Service\Drive;

class GoogleDriveServiceProvider extends ServiceProvider
{
    /**
     * Register services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap services.
     */
    public function boot(): void
    {
        Storage::extend('google_drive', function ($app, $config) {
            $client = new GoogleClient();
            $client->setClientId($config['client_id']);
            $client->setClientSecret($config['client_secret']);
            $client->setAccessType('offline');
            $client->setApprovalPrompt('force');
            
            // Set the refresh token if provided
            if (isset($config['refresh_token'])) {
                $client->refreshToken($config['refresh_token']);
            }
            
            $service = new Drive($client);
            $adapter = new GoogleDriveAdapter($service, $config['folder_id'] ?? null, [
                'teamDriveId' => $config['team_drive_id'] ?? null,
            ]);
            
            return new \League\Flysystem\Filesystem($adapter);
        });
    }
}
