<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        // additional seeders will be added to the array below

        $this->call([
            UserSeeder::class,
            WorkspaceSeeder::class,
            ProjectSeeder::class
        ]);
    }
}
