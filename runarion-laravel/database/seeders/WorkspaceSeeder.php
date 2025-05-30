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
        // Create a workspace for each user and set as owner
        $user_workspace_pairs = [];
        User::all()->each(function ($user) use (&$user_workspace_pairs) {
            $workspace = $user->email === 'admin@runarion.com' ? Workspace::factory()->create([
                'name' => 'Demo Workspace',
                'slug' => 'demo-workspace',
            ]) : Workspace::factory()->create();
            
            $user_workspace_pairs[] = [
                'user_id' => $user->id,
                'workspace_id' => $workspace->id,
            ];

            WorkspaceMember::create([
                'workspace_id' => $workspace->id,
                'user_id' => $user->id,
                'role' => 'owner',
            ]);
        });

        // Assign 1-4 random users to each workspace as admin or member
        foreach ($user_workspace_pairs as $pair) {
            $users = User::where('id', '!=', $pair['user_id'])->inRandomOrder()->take(rand(1, 4))->get();

            foreach ($users as $index => $user) {
                WorkspaceMember::create([
                    'workspace_id' => $pair['workspace_id'],
                    'user_id' => $user->id,
                    'role' => $index === 0 ? 'admin' : 'member',
                ]);
            }
        }
    }
}