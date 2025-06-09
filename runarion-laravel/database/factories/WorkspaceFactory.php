<?php

namespace Database\Factories;

use App\Models\Workspace;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * Workspace Factory
 * 
 * Factory untuk membuat workspace test dengan data yang realistis
 * menyediakan metode untuk membuat workspace dalam berbagai keadaan (aktif/tidak aktif, trial/kadaluarsa)
 */
class WorkspaceFactory extends Factory
{
  protected $model = Workspace::class;

  /**
   * Define the model's default state.
   * membuat workspace dengan informasi lengkap termasuk detail billing,
   * informasi langganan, dan pengaturan.
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    $name = fake()->company();
    $slug = Str::slug($name);
    $imageUrl = 'https://ui-avatars.com/api/?' . http_build_query([
      'name' => $name,
      'background' => 'random',
    ]);

    return [
      'name' => $name,
      'slug' => $slug,
      'cover_image_url' => $imageUrl,
      'timezone' => fake()->timezone(),
      'settings' => null,
      'permissions' => [
        'invite_members' => ['admin'],
        'invite_guests' => ['admin'],
        'manage_users' => ['admin'],
        'create_projects' => ['member', 'admin'],
        'delete_projects' => ['member', 'admin'],
      ],
      'cloud_storage' => [
        'google_drive' => [
          'enabled' => fake()->boolean(),
        ],
        'dropbox' => [
          'enabled' => fake()->boolean(),
        ],
        'onedrive' => [
          'enabled' => fake()->boolean(),
        ],
      ],
      'llm' => [
        'openai' => [
          'enabled' => fake()->boolean(),
          'api_key' => fake()->uuid(),
        ],
        'gemini' => [
          'enabled' => fake()->boolean(),
          'api_key' => fake()->uuid(),
        ],
        'deepseek' => [
          'enabled' => fake()->boolean(),
          'api_key' => fake()->uuid(),
        ],
      ],
      'billing_email' => fake()->safeEmail(),
      'billing_name' => fake()->company(),
      'billing_address' => fake()->streetAddress(),
      'billing_city' => fake()->city(),
      'billing_state' => fake()->state(),
      'billing_postal_code' => fake()->postcode(),
      'billing_country' => fake()->country(),
      'billing_phone' => fake()->phoneNumber(),
      'billing_tax_id' => fake()->numerify('TAX-####'),
      'stripe_customer_id' => fake()->uuid(),
      'stripe_subscription_id' => fake()->uuid(),
      'trial_ends_at' => fake()->dateTimeBetween('now', '+14 days'),
      'subscription_ends_at' => fake()->dateTimeBetween('+15 days', '+1 year'),
      'is_active' => true,
      'monthly_quota' => 10,
      'quota' => 10
    ];
  }

  /**
   * Set the workspace as inactive.
   * 
   * @return self
   */
  public function inactive(): self
  {
    return $this->state(fn(array $attributes) => [
      'is_active' => false,
    ]);
  }

  /**
   * Set the workspace as being in trial period.
   * 
   * @return self
   */
  public function trial(): self
  {
    return $this->state(fn(array $attributes) => [
      'trial_ends_at' => fake()->dateTimeBetween('now', '+14 days'),
      'subscription_ends_at' => null,
    ]);
  }

  /**
   * Set the workspace as having an expired subscription.
   * 
   * @return self
   */
  public function expired(): self
  {
    return $this->state(fn(array $attributes) => [
      'trial_ends_at' => fake()->dateTimeBetween('-1 month', '-1 day'),
      'subscription_ends_at' => fake()->dateTimeBetween('-1 month', '-1 day'),
    ]);
  }
}