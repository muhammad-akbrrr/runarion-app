<?php

namespace Database\Factories;

use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * WorkspaceMember Factory
 * 
 * Factory untuk membuat membership workspace test dengan berbagai role.
 * menyediakan metode untuk membuat membership dengan role tertentu (owner/admin/member).
 * memastikan hanya ada satu owner per workspace.
 */
class WorkspaceMemberFactory extends Factory
{
  protected $model = WorkspaceMember::class;

  /**
   * Define the model's default state.
   * membuat membership workspace dengan role acak.
   * catatan: hanya membuat role owner jika tidak ada owner untuk workspace.
   * 
   * @return array<string, mixed>
   */
  public function definition(): array
  {
    $workspace = Workspace::factory();
    $user = User::factory();

    // cek apakah workspace sudah memiliki owner
    $hasOwner = WorkspaceMember::where('workspace_id', $workspace->id)
      ->where('role', 'owner')
      ->exists();

    // jika workspace sudah memiliki owner, jangan membuat owner lain
    $role = $hasOwner ? fake()->randomElement(['admin', 'member']) : fake()->randomElement(['owner', 'admin', 'member']);

    return [
      'workspace_id' => $workspace,
      'user_id' => $user,
      'role' => $role,
    ];
  }

  /**
   * Set the member role to owner.
   * akan melempar exception jika workspace sudah memiliki owner.
   * 
   * @return self
   */
  public function owner(): self
  {
    return $this->state(function (array $attributes) {
      // cek apakah workspace sudah memiliki owner
      $hasOwner = WorkspaceMember::where('workspace_id', $attributes['workspace_id'])
        ->where('role', 'owner')
        ->exists();

      if ($hasOwner) {
        throw new \RuntimeException('Workspace already has an owner.');
      }

      return [
        'role' => 'owner',
      ];
    });
  }

  /**
   * Set the member role to admin.
   * 
   * @return self
   */
  public function admin(): self
  {
    return $this->state(fn(array $attributes) => [
      'role' => 'admin',
    ]);
  }

  /**
   * Set the member role to regular member.
   * 
   * @return self
   */
  public function member(): self
  {
    return $this->state(fn(array $attributes) => [
      'role' => 'member',
    ]);
  }
}