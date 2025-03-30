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
     * Calls all individual seeders in the correct order:
     * 1. UserSeeder - Creates users
     * 2. WorkspaceSeeder - Creates workspaces and memberships
     * 3. FolderSeeder - Creates folders within workspaces
     * 4. ProjectSeeder - Creates projects within folders
     * 
     * @return void
     */
    public function run(): void
    {
        // additional seeders will be added to the array below

        $this->call([
            UserSeeder::class,
            WorkspaceSeeder::class,
            FolderSeeder::class,
            ProjectSeeder::class
        ]);
    }
}
