<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class AuthorStyleSample extends Model
{
    use HasUlids, SoftDeletes;

    protected $fillable = [
        'author_style_id',
        'author_sample_id',
    ];

    public static function rules(): array
    {
        return [
            'author_style_id' => ['required', 'ulid'],
            'author_sample_id' => ['required', 'ulid'],
        ];
    }
}
