<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\SoftDeletes;

/**
 * Projects Model
 * 
 * mewakili project yang ada pada workspace, setiap project bisa disimpan di folder
 * memiliki setting & konfigurasi tersendiri
 */
class Projects extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'workspace_id',
        'folder_id',
        'name',
        'slug',
        'description',
        'settings',
        'is_public',
        'is_active',
    ];

    protected $casts = [
        'settings' => 'array',
        'is_public' => 'boolean',
        'is_active' => 'boolean',
    ];

    /**
     * ambil workspace yang memiliki project ini
     * 
     * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
     */
    public function workspace(): BelongsTo
    {
        return $this->belongsTo(Workspace::class);
    }

    /**
     * ambil folder yang memiliki project ini
     * 
     * @return \Illuminate\Database\Eloquent\Relations\BelongsTo
     */
    public function folder(): BelongsTo
    {
        return $this->belongsTo(Folder::class);
    }

    /**
     * ambil value setting tertentu dari array setting project
     * 
     * @param string $key The setting key to retrieve
     * @param mixed $default The default value if setting doesn't exist
     * @return mixed The setting value or default if not found
     */
    public function getSetting(string $key, $default = null)
    {
        return $this->settings[$key] ?? $default;
    }

    /**
     * set value setting tertentu dari array setting project
     * 
     * @param string $key The setting key to set
     * @param mixed $value The value to set
     * @return void
     */
    public function setSetting(string $key, $value): void
    {
        $settings = $this->settings ?? [];
        $settings[$key] = $value;
        $this->settings = $settings;
    }
}
