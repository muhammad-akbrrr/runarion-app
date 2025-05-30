<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceMember;

/**
 * Workspace Seeder
 * 
 * Seeds the workspaces and workspace_members tables with initial data including:
 * - A demo workspace owned by the super admin
 * - Multiple random workspaces with various members
 */
class WorkspaceSeeder extends Seeder
{
    /**
     * Run the database seeds.
     * 
     * Creates:
     * 1. A demo workspace named 'Demo Workspace' to be owned by the super admin
     * 2. 10 random workspaces using the WorkspaceFactory to be owned by other users
     * @return void
     */
    public function run(): void
    {
        Workspace::create([
            'name' => 'Demo Workspace',
            'slug' => 'demo-workspace'
        ]);

        Workspace::factory(10)->create();
    }
}