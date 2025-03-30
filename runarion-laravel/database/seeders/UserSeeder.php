<?php

namespace Database\Seeders;

// use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
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
   * Creates:
   * 1. A super admin user with email 'admin@runarion.com' and password 'password'
   * 2. 10 random users using the UserFactory
   * 
   * @return void
   */
  public function run(): void
  {
    // Create a super admin user
    User::create([
      'name' => 'Super Admin',
      'email' => 'admin@runarion.com',
      'password' => Hash::make('password123'),
      'email_verified_at' => now(),
    ]);

    // Create some regular users
    User::factory(10)->create();
  }
}