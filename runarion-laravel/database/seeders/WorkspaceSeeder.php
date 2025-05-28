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
     * 1. A demo workspace named 'Demo Workspace' owned by the super admin
     * 2. 5 random workspaces using the WorkspaceFactory
     * 3. For each random workspace:
     *    - Attaches 2-5 random users as members
     *    - First user becomes owner, others become admin or regular members
     * 
     * @return void
     */
    public function run(): void
    {
        // Create a demo workspace for the super admin
        $demoWorkspace = Workspace::factory()->create([
            'name' => 'Demo Workspace',
            'slug' => 'demo-workspace',
        ]);

        // Attach super admin as owner
        WorkspaceMember::create([
            'workspace_id' => $demoWorkspace->id,
            'user_id' => User::where('email', 'admin@runarion.com')->first()->id,
            'role' => 'owner',
        ]);

        // Create some random workspaces
        $workspaces = Workspace::factory(5)->create();

        // For each workspace, attach 2-5 random users as members
        foreach ($workspaces as $workspace) {
            $users = User::inRandomOrder()->limit(fake()->numberBetween(2, 5))->get();

            foreach ($users as $index => $user) {
                WorkspaceMember::create([
                    'workspace_id' => $workspace->id,
                    'user_id' => $user->id,
                    'role' => $index === 0 ? 'owner' : ($index === 1 ? 'admin' : 'member'),
                ]);
            }
        }

        // Ensure each user is attached to at least one workspace
        User::all()->each(function ($user) use ($workspaces) {
            $numWorkspaces = WorkspaceMember::where('user_id', $user->id)->count();
            if ($numWorkspaces === 0) {
                // Attach user to a random workspace
                $randomWorkspace = $workspaces->random();
                WorkspaceMember::create([
                    'workspace_id' => $randomWorkspace->id,
                    'user_id' => $user->id,
                    'role' => 'member',
                ]);
            }
        });
    }
}