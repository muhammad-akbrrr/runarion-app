<?php

namespace Database\Factories;

use App\Models\User;
use App\Models\Projects;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * User Factory
 * 
 * Factory untuk membuat user test dengan data yang realistis
 * menyediakan metode untuk membuat user dalam berbagai keadaan (verified/unverified)
 */
class UserFactory extends Factory
{
    protected static ?string $password;
    protected $model = User::class;

    /**
     * Define the model's default state.
     * 
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $name = fake()->name();
        $email = Str::slug($name) . '@example.com';
        $avatarUrl = 'https://ui-avatars.com/api/?' . http_build_query([
            'name' => $name,
            'background' => 'random',
        ]);

        return [
            'name' => $name,
            'email' => $email,
            'email_verified_at' => now(),
            'password' => static::$password ??= Hash::make('password123'),
            'avatar_url' => $avatarUrl,
            'last_workspace_id' => null,
            'settings' => null,
            'notifications' => [
                'email' => fake()->randomElement([true, false]),
                'desktop' => fake()->randomElement([true, false]),
            ],
            'highlighted_projects' => null,
            'remember_token' => Str::random(10),
        ];
    }

    /**
     * Indicate that the model's email address should be unverified.
     */
    public function unverified(): static
    {
        return $this->state(fn(array $attributes) => [
            'email_verified_at' => null,
        ]);
    }
}
