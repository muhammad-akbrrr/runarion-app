<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Validation\Rule;
use Illuminate\Support\Facades\DB;

/**
 * Model Workspace
 * 
 * mewakili workspace dalam sistem yang dapat mengandung beberapa project dan user
 * termasuk fitur manajemen berlangganan dan billing
 */
class Workspace extends Model
{
    use HasFactory, SoftDeletes, HasUlids;

    // Constants for workspace limits
    const DEFAULT_GENERATION_QUOTA = 50;
    const DEFAULT_PROJECT_LIMIT = 30;

    protected $fillable = [
        'name',
        'slug',
        'cover_image_url',
        'timezone',
        'settings',
        'permissions',
        'cloud_storage',
        'llm',
        'billing_email',
        'billing_name',
        'billing_address',
        'billing_city',
        'billing_state',
        'billing_postal_code',
        'billing_country',
        'billing_phone',
        'billing_tax_id',
        'stripe_customer_id',
        'stripe_subscription_id',
        'trial_ends_at',
        'subscription_ends_at',
        'is_active',
        'monthly_quota',
        'quota'
    ];

    protected $casts = [
        'settings' => 'array',
        'permissions' => 'array',
        'cloud_storage' => 'array',
        'llm' => 'array',
        'trial_ends_at' => 'datetime',
        'subscription_ends_at' => 'datetime',
        'is_active' => 'boolean',
        'monthly_quota' => 'integer',
        'quota' => 'integer'
    ];

    /**
     * Get the validation rules that apply to the model.
     *
     * @return array<string, mixed>
     */
    public static function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:255'],
            'slug' => ['required', 'string', 'max:255', 'unique:workspaces,slug'],
            'cover_image_url' => ['nullable', 'string', 'url'],
            'timezone' => ['nullable', 'string', 'timezone'],
            'settings' => ['nullable', 'array'],
            'permissions' => ['nullable', 'array'],
            'cloud_storage' => ['nullable', 'array'],
            'llm' => ['nullable', 'array'],
            'billing_email' => ['nullable', 'email'],
            'billing_name' => ['nullable', 'string', 'max:255'],
            'billing_address' => ['nullable', 'string', 'max:255'],
            'billing_city' => ['nullable', 'string', 'max:255'],
            'billing_state' => ['nullable', 'string', 'max:255'],
            'billing_postal_code' => ['nullable', 'string', 'max:20'],
            'billing_country' => ['nullable', 'string', 'max:2'],
            'billing_phone' => ['nullable', 'string', 'max:20'],
            'billing_tax_id' => ['nullable', 'string', 'max:50'],
            'stripe_customer_id' => ['nullable', 'string'],
            'stripe_subscription_id' => ['nullable', 'string'],
            'trial_ends_at' => ['nullable', 'date'],
            'subscription_ends_at' => ['nullable', 'date'],
            'is_active' => ['boolean'],
        ];
    }

    /**
     * Get the members of the workspace.
     */
    public function members()
    {
        return $this->hasMany(WorkspaceMember::class);
    }

    /**
     * Get the users that belong to the workspace.
     */
    public function users()
    {
        return $this->belongsToMany(User::class, 'workspace_members')
            ->withPivot('role')
            ->withTimestamps();
    }

    /**
     * Get the projects that belong to the workspace.
     */
    public function projects()
    {
        return $this->hasMany(Projects::class);
    }

    /**
     * Get the owner of the workspace.
     */
    public function owner()
    {
        return $this->members()->where('role', 'owner')->first()?->user;
    }

    /**
     * Get the generation logs for the workspace.
     */
    public function generationLogs()
    {
        return $this->hasMany(GenerationLog::class, 'workspace_id');
    }

    /**
     * Check if the workspace has reached its project limit.
     *
     * @return bool
     */
    public function hasReachedProjectLimit()
    {
        $projectLimit = $this->settings['project_limit'] ?? self::DEFAULT_PROJECT_LIMIT;
        $projectCount = $this->projects()->count();
        
        return $projectCount >= $projectLimit;
    }

    /**
     * Check if the workspace has generation quota available.
     *
     * @return bool
     */
    public function hasGenerationQuotaAvailable()
    {
        return $this->quota > 0;
    }

    /**
     * Decrement the generation quota by 1.
     *
     * @return bool
     */
    public function decrementGenerationQuota()
    {
        if ($this->quota <= 0) {
            return false;
        }

        $this->quota -= 1;
        return $this->save();
    }

    /**
     * Reset the monthly generation quota.
     *
     * @return bool
     */
    public function resetMonthlyQuota()
    {
        $this->quota = $this->monthly_quota;
        return $this->save();
    }

    /**
     * Get the number of generations used this month.
     *
     * @return int
     */
    public function getGenerationsUsedThisMonth()
    {
        $startOfMonth = now()->startOfMonth();
        
        return $this->generationLogs()
            ->where('created_at', '>=', $startOfMonth)
            ->where('success', true)
            ->count();
    }

    /**
     * Get the remaining generation quota.
     *
     * @return int
     */
    public function getRemainingQuota()
    {
        return max(0, $this->quota);
    }
}
