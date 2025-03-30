<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Workspace extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'name',
        'slug',
        'description',
        'cover_image_url',
        'settings',
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
    ];

    protected $casts = [
        'settings' => 'array',
        'trial_ends_at' => 'datetime',
        'subscription_ends_at' => 'datetime',
        'is_active' => 'boolean',
    ];

    public function members(): HasMany
    {
        return $this->hasMany(WorkspaceMember::class);
    }

    public function users(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'workspace_members');
    }

    public function projects(): HasMany
    {
        return $this->hasMany(Projects::class);
    }

    public function owners(): HasMany
    {
        return $this->members()->where('role', 'owner');
    }

    public function admins(): HasMany
    {
        return $this->members()->where('role', 'admin');
    }

    public function regularMembers(): HasMany
    {
        return $this->members()->where('role', 'member');
    }

    public function hasActiveSubscription(): bool
    {
        if (!$this->subscription_ends_at) {
            return false;
        }

        return $this->subscription_ends_at->isFuture();
    }

    public function isOnTrial(): bool
    {
        if (!$this->trial_ends_at) {
            return false;
        }

        return $this->trial_ends_at->isFuture();
    }

    public function getSubscriptionStatus(): string
    {
        if ($this->isOnTrial()) {
            return 'trial';
        }

        if ($this->hasActiveSubscription()) {
            return 'active';
        }

        return 'inactive';
    }
}
