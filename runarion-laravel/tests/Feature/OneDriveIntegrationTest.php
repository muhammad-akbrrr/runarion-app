<?php

namespace Tests\Feature;

use Tests\TestCase;
use App\Services\CloudStorage\CloudStorageProviderFactory;
use App\Services\OneDriveService;

class OneDriveIntegrationTest extends TestCase
{
    public function test_onedrive_provider_can_be_created()
    {
        $provider = CloudStorageProviderFactory::make('onedrive');
        $this->assertInstanceOf(\App\Services\CloudStorage\Providers\OneDriveProvider::class, $provider);
    }

    public function test_onedrive_service_can_be_instantiated()
    {
        $service = new OneDriveService();
        $this->assertInstanceOf(OneDriveService::class, $service);
    }

    public function test_onedrive_config_is_loaded()
    {
        $this->assertNotNull(config('services.onedrive.client_id'));
        $this->assertNotNull(config('services.onedrive.client_secret'));
        $this->assertNotNull(config('services.onedrive.redirect_uri'));
    }
}
