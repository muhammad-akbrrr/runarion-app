<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Database\Seeder;
use App\Models\User;

/**
 * User Seeder
 * 
 * Seeds the users table with initial data including:
 * - A super admin user with predefined credentials
 * - A set of random users for testing purposes
 */
class UserSeeder extends Seeder
{
  /**
   * Run the database seeds.
   * 
   * 1. Create Super Admin with email 'admin@runarion.com' as owner of the Demo Workspace
   * 2. Create 10 random users using the UserFactory, each become owner of a workspace
   * 3. For each workspace, assign 1 user as admin and 1-3 users as members
   * @return void
   */
  public function run(): void
  {
    $workspaces = Workspace::all();

    foreach ($workspaces as $workspace) {
      $userField = [
        'last_workspace_id' => $workspace->id,
      ];
      if ($workspace->name === 'Demo Workspace') {
        $userField['name'] = 'Super Admin';
        $userField['email'] = 'admin@runarion.com';
      }
      $user = User::factory()->create($userField);

      WorkspaceMember::create([
        'workspace_id' => $workspace->id,
        'user_id' => $user->id,
        'role' => 'owner',
      ]);
    }

    foreach ($workspaces as $workspace) {
      $userIds = User::where('last_workspace_id', '!=', $workspace->id)
        ->inRandomOrder()
        ->take(rand(2, 4))
        ->pluck('id');

      foreach ($userIds as $index => $userId) {
        WorkspaceMember::create([
          'workspace_id' => $workspace->id,
          'user_id' => $userId,
          'role' => $index === 0 ? 'admin' : 'member',
        ]);
      }
    }
  }
}