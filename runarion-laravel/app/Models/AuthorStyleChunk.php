<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

class AuthorStyleChunk extends Model
{
    use HasUlids, SoftDeletes;

    protected $fillable = [
        'author_style_id',
        'author_sample_id',
        'chunk_number',
        'chunk_start_index',
        'chunk_char_count',
        'chunk_token_count',
        'author_style_chunk_ids',
        'style_text',
        'style_text_token_count',
        'error_message',
        'processing_time_ms',
    ];

    protected $casts = [
        'chunk_number' => 'integer',
        'chunk_start_index' => 'integer',
        'chunk_char_count' => 'integer',
        'chunk_token_count' => 'integer',
        'author_style_chunk_ids' => 'array',
        'style_text_token_count' => 'integer',
        'processing_time_ms' => 'integer',
    ];

    public static function rules(): array
    {
        return [
            'author_style_id' => ['required', 'ulid'],
            'author_sample_id' => ['nullable', 'ulid'],
            'chunk_number' => ['nullable', 'integer'],
            'chunk_start_index' => ['nullable', 'integer'],
            'chunk_char_count' => ['nullable', 'integer'],
            'chunk_token_count' => ['nullable', 'integer'],
            'author_style_chunk_ids' => ['nullable', 'array'],
            'author_style_chunk_ids.*' => ['ulid'],
            'style_text' => ['nullable', 'string'],
            'style_text_token_count' => ['nullable', 'integer'],
            'error_message' => ['nullable', 'string'],
            'processing_time_ms' => ['required', 'integer'],
        ];
    }
}
