<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
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
    ];

    protected $casts = [
        'settings' => 'array',
        'permissions' => 'array',
        'cloud_storage' => 'array',
        'llm' => 'array',
        'trial_ends_at' => 'datetime',
        'subscription_ends_at' => 'datetime',
        'is_active' => 'boolean',
    ];
}
