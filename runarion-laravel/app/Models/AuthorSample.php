<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\Rule;

class AuthorSample extends Model
{
    use HasUlids;

    protected $fillable = [
        'document_path',
        'document_hash',
        'text_content',
        'error_message',
    ];

    protected $casts = [];

    public static function rules(): array
    {
        return [
            'document_path' => ['required', 'string'],
            'document_hash' => ['nullable', 'string', Rule::unique('author_samples')],
            'text_content' => ['nullable', 'string'],
            'error_message' => ['nullable', 'string'],
        ];
    }
}
