<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

/**
 * Database Seeder
 * 
 * Main seeder class that orchestrates the seeding of all database tables.
 * Calls individual seeders in the correct order to maintain data relationships.
 */
class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     * 
     * The seeding process follows this order:
     * 1. WorkspaceSeeder - Creates workspaces
     * 2. UserSeeder - Creates users and assigns them to workspaces
     * 3. FolderSeeder - Creates folders within workspaces
     * 4. ProjectSeeder - Creates projects within folders
     * 5. UpdateProjectRelations - Updates project authors and highlighted projects
     * 
     * @return void
     */
    public function run(): void
    {
        $this->call([
            WorkspaceSeeder::class,
            UserSeeder::class,
            FolderSeeder::class,
            ProjectSeeder::class,
            UpdateProjectRelations::class,
        ]);
    }
}
