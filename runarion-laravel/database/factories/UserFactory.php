<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * User Factory
 * 
 * Factory untuk membuat user test dengan data yang realistis
 * menyediakan metode untuk membuat user dengan berbagai keadaan (terverifikasi/tidak terverifikasi)
 */
class UserFactory extends Factory
{
    /**
     * password yang sedang digunakan oleh factory.
     * ini adalah properti statis untuk memastikan hashing password yang konsisten.
     */
    protected static ?string $password;

    /**
     * Define the model's default state.
     * membuat user dengan informasi dasar termasuk nama, email, dan password.
     * 
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'name' => fake()->name(),
            'email' => fake()->unique()->safeEmail(),
            'email_verified_at' => now(),
            'password' => static::$password ??= Hash::make('password123'),
            'remember_token' => Str::random(10),
        ];
    }

    /**
     * Indikasi bahwa alamat email model harus tidak terverifikasi.
     * 
     * @return static
     */
    public function unverified(): static
    {
        return $this->state(fn(array $attributes) => [
            'email_verified_at' => null,
        ]);
    }
}
