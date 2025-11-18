<?php

namespace App\Providers;

use Illuminate\Support\Facades\Storage;
use Illuminate\Support\ServiceProvider;
use Justus\FlysystemOneDrive\OneDriveAdapter;
use League\Flysystem\Filesystem;

class OneDriveServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        Storage::extend('onedrive', function ($app, $config) {
            $adapter = new OneDriveAdapter($config['access_token']);
            return new Filesystem($adapter);
        });
    }
}
