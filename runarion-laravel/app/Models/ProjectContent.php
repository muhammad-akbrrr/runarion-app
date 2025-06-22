<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\Rule;

class ProjectContent extends Model
{
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'project_id',
        'content',
        'editor_state',
        'word_count',
        'character_count',
        'version',
        'last_edited_at',
    ];

    /**
     * The attributes that should be cast.
     *
     * @var array<string, string>
     */
    protected $casts = [
        'editor_state' => 'array',
        'word_count' => 'integer',
        'character_count' => 'integer',
        'version' => 'integer',
        'last_edited_at' => 'datetime',
    ];

    /**
     * Get the project that owns the content.
     */
    public function project()
    {
        return $this->belongsTo(Projects::class, 'project_id');
    }

    /**
     * Calculate word count from content.
     *
     * @param string $content
     * @return int
     */
    public static function calculateWordCount($content)
    {
        // Remove HTML tags and trim whitespace
        $text = trim(strip_tags($content));
        
        // Return 0 if content is empty
        if (empty($text)) {
            return 0;
        }
        
        // Split by whitespace and count non-empty words
        $words = preg_split('/\s+/', $text, -1, PREG_SPLIT_NO_EMPTY);
        return count($words);
    }

    /**
     * Calculate character count from content.
     *
     * @param string $content
     * @return int
     */
    public static function calculateCharacterCount($content)
    {
        // Remove HTML tags and trim whitespace
        $text = trim(strip_tags($content));
        
        // Return 0 if content is empty
        if (empty($text)) {
            return 0;
        }
        
        // Count characters
        return mb_strlen($text);
    }

    /**
     * Get the validation rules that apply to the model.
     *
     * @return array<string, mixed>
     */
    public static function rules(): array
    {
        return [
            'project_id' => ['required', 'ulid', 'exists:projects,id'],
            'content' => ['nullable', 'string'],
            'editor_state' => ['nullable', 'array'],
            'word_count' => ['integer', 'min:0'],
            'character_count' => ['integer', 'min:0'],
            'version' => ['integer', 'min:1'],
            'last_edited_at' => ['nullable', 'date'],
        ];
    }
}
