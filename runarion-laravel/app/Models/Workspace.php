<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Illuminate\Database\Eloquent\SoftDeletes;

/**
 * Model Workspace
 * 
 * mewakili workspace dalam sistem yang dapat mengandung beberapa project dan user
 * termasuk fitur manajemen berlangganan dan billing
 */
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

    /**
     * ambil semua member workspace
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function members(): HasMany
    {
        return $this->hasMany(WorkspaceMember::class);
    }

    /**
     * ambil semua user yang merupakan member workspace ini
     * 
     * @return \Illuminate\Database\Eloquent\Relations\BelongsToMany
     */
    public function users(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'workspace_members');
    }

    /**
     * ambil semua project di workspace ini
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function projects(): HasMany
    {
        return $this->hasMany(Projects::class);
    }

    /**
     * ambil owner workspace
     * workspace hanya dapat memiliki satu owner pada waktu tertentu
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasOne
     */
    public function owner(): HasOne
    {
        return $this->hasOne(WorkspaceMember::class)->where('role', 'owner');
    }

    /**
     * cek apakah suatu user adalah owner dari workspace
     * 
     * @return bool
     */
    public function isOwner(int $userId): bool
    {
        return $this->members()
            ->where('user_id', $userId)
            ->where('role', 'owner')
            ->exists();
    }

    /**
     * ambil semua admin workspace
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function admins(): HasMany
    {
        return $this->members()->where('role', 'admin');
    }

    /**
     * cek apakah suatu user adalah admin dari workspace
     * 
     * @return bool
     */
    public function isAdmin(int $userId): bool
    {
        return $this->members()
            ->where('user_id', $userId)
            ->where('role', 'admin')
            ->exists();
    }

    /**
     * cek apakah suatu user adalah owner atau admin dari workspace
     * 
     * @return bool
     */
    public function isOwnerOrAdmin(int $userId): bool
    {
        return $this->members()
            ->where('user_id', $userId)
            ->whereIn('role', ['owner', 'admin'])
            ->exists();
    }

    /**
     * ambil semua member regular dari workspace
     * 
     * @return \Illuminate\Database\Eloquent\Relations\HasMany
     */
    public function regularMembers(): HasMany
    {
        return $this->members()->where('role', 'member');
    }

    /**
     * cek apakah suatu user adalah member dari workspace, termasuk owner dan admin
     * 
     * @return bool
     */
    public function isMember(int $userId): bool
    {
        return $this->members()
            ->where('user_id', $userId)
            ->exists();
    }

    /**
     * cek apakah workspace memiliki langganan aktif
     * 
     * @return bool True jika berlangganan aktif, false jika tidak
     */
    public function hasActiveSubscription(): bool
    {
        if (!$this->subscription_ends_at) {
            return false;
        }

        return $this->subscription_ends_at->isFuture();
    }

    /**
     * cek apakah workspace sedang dalam masa trial
     * 
     * @return bool True jika sedang trial, false jika tidak
     */
    public function isOnTrial(): bool
    {
        if (!$this->trial_ends_at) {
            return false;
        }

        return $this->trial_ends_at->isFuture();
    }

    /**
     * ambil status langganan workspace saat ini
     * 
     * @return string antara: 'trial', 'active', or 'inactive'
     */
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
