<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;

class IntermediateAuthorStyle extends Model
{
    use HasUlids;

    protected $fillable = [
        'structured_style_id',
        'style',
        'passages',
        'processing_time_ms',
    ];

    protected $casts = [
        'passages' => 'array',
        'processing_time_ms' => 'integer',
    ];

    public static function rules(): array
    {
        return [
            'structured_style_id' => ['required', 'ulid'],
            'style' => ['required', 'string'],
            'passages' => ['required', 'array'],
            'passages.*' => ['required', 'array'], 
            'processing_time_ms' => ['required', 'integer'],
        ];
    }
}
