<?php

namespace Database\Seeders;

use App\Models\Folder;
use App\Models\Workspace;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

/**
 * Folder Seeder
 * 
 * Seeds the folders table with initial data.
 * Creates a set of standard folders for each workspace to organize projects.
 */
class FolderSeeder extends Seeder
{
  /**
   * Run the database seeds.
   * 
   * For each workspace, creates the following standard folders:
   * - Development
   * - Design
   * - Documentation
   * - Marketing
   * - Research
   * - Resources
   * 
   * Each folder is created with:
   * - A name and corresponding slug
   * - Association with its parent workspace
   * 
   * @return void
   */
  public function run(): void
  {
    // Create folders for each workspace
    Workspace::all()->each(function ($workspace) {
      // Create root folders
      $folders = [
        'Development',
        'Design',
        'Documentation',
        'Marketing',
        'Research',
        'Resources',
      ];

      foreach ($folders as $folderName) {
        Folder::factory()->create([
          'workspace_id' => $workspace->id,
          'name' => $folderName,
          'slug' => Str::slug($folderName),
        ]);
      }
    });
  }
}