<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Concerns\HasUlids;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Validation\Rule;
use Illuminate\Support\Str;

/**
 * ProjectContent Model
 * 
 * Stores consolidated project content in JSON format with one-to-one relationship to projects
 * Includes version control for generation history and step management
 */
class ProjectContent extends Model
{
  use HasFactory, SoftDeletes, HasUlids;

  protected $table = 'project_content';

  protected $fillable = [
    'project_id',
    'content',
    'metadata',
    'generation_history',
    'current_step_id',
    'last_selected_versions',
    'last_edited_at',
    'last_edited_by',
  ];

  protected $casts = [
    'content' => 'array',
    'metadata' => 'array',
    'generation_history' => 'array',
    'last_selected_versions' => 'array',
    'last_edited_at' => 'datetime',
    'last_edited_by' => 'integer',
  ];

  /**
   * Get the project that owns the content.
   */
  public function project()
  {
    return $this->belongsTo(Projects::class, 'project_id');
  }

  /**
   * Get the user who last edited the content.
   */
  public function lastEditor()
  {
    return $this->belongsTo(User::class, 'last_edited_by');
  }

  /**
   * Get the validation rules that apply to the model.
   *
   * @return array<string, mixed>
   */
  public static function rules(): array
  {
    return [
      'project_id' => ['required', 'ulid', 'exists:projects,id', 'unique:project_content,project_id'],
      'content' => ['required', 'array'],
      'content.*.order' => ['required', 'integer', 'min:0'],
      'content.*.chapter_name' => ['required', 'string', 'max:255'],
      'content.*.content' => ['required', 'string', 'max:1000000'], // content for markdown
      'content.*.summary' => ['nullable', 'string'],
      'content.*.plot_points' => ['nullable', 'array'],
      'metadata' => ['nullable', 'array'],
      'last_edited_by' => ['nullable', 'integer', 'exists:users,id'],
    ];
  }

  /**
   * Get total word count from all chapters
   */
  public function getTotalWordCountAttribute()
  {
    if (!$this->content) {
      return 0;
    }

    $totalWords = 0;
    foreach ($this->content as $chapter) {
      // Remove markdown syntax for accurate word count
      $plainText = $this->stripMarkdown($chapter['content'] ?? '');
      $totalWords += str_word_count($plainText);
    }

    return $totalWords;
  }

  /**
   * Strip markdown syntax from text for word counting
   */
  private function stripMarkdown($text)
  {
    // Remove markdown syntax
    $text = preg_replace('/[#*_`~\[\]()]/u', '', $text);
    // Replace multiple whitespace with single space
    $text = preg_replace('/\s+/u', ' ', $text);
    return trim($text);
  }

  /**
   * Get chapter count
   */
  public function getChapterCountAttribute()
  {
    return $this->content ? count($this->content) : 0;
  }

  /**
   * Get chapters ordered by their order field
   */
  public function getOrderedChaptersAttribute()
  {
    if (!$this->content) {
      return [];
    }

    $chapters = $this->content;
    usort($chapters, function ($a, $b) {
      return $a['order'] <=> $b['order'];
    });

    return $chapters;
  }

  /**
   * Get a specific chapter by order
   */
  public function getChapterByOrder($order)
  {
    if (!$this->content) {
      return null;
    }

    foreach ($this->content as $chapter) {
      if ($chapter['order'] == $order) {
        return $chapter;
      }
    }

    return null;
  }

  /**
   * Add a new chapter with automatic order
   */
  public function addChapter($chapterName, $content)
  {
    $chapters = $this->content ?? [];
    $newOrder = count($chapters);

    $chapters[] = [
      'order' => $newOrder,
      'chapter_name' => $chapterName,
      'content' => $content,
    ];

    $this->update(['content' => $chapters]);
    return $this;
  }

  /**
   * Update a chapter by order
   */
  public function updateChapter($order, $chapterName, $content)
  {
    if (!$this->content) {
      return false;
    }

    $chapters = $this->content;
    foreach ($chapters as &$chapter) {
      if ($chapter['order'] == $order) {
        $chapter['chapter_name'] = $chapterName;
        $chapter['content'] = $content;
        $this->update(['content' => $chapters]);
        return true;
      }
    }

    return false;
  }

  /**
   * Remove a chapter by order
   */
  public function removeChapter($order)
  {
    if (!$this->content) {
      return false;
    }

    $chapters = array_filter($this->content, function ($chapter) use ($order) {
      return $chapter['order'] != $order;
    });

    // Reorder remaining chapters
    $reorderedChapters = [];
    foreach (array_values($chapters) as $index => $chapter) {
      $chapter['order'] = $index;
      $reorderedChapters[] = $chapter;
    }

    $this->update(['content' => $reorderedChapters]);
    return true;
  }

  /**
   * Update the last edited timestamp and user
   */
  public function updateLastEdited($userId = null)
  {
    $this->update([
      'last_edited_at' => now(),
      'last_edited_by' => $userId ?? auth()->id(),
    ]);
  }

  /**
   * Initialize generation history for a chapter if it doesn't exist
   */
  public function initializeGenerationHistory($chapterOrder)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      $history[$chapterOrder] = [
        'steps' => [],
        'currentStepId' => null,
        'lastSelectedVersions' => [],
      ];
      
      $this->update(['generation_history' => $history]);
    }
    
    return $history[$chapterOrder];
  }

  /**
   * Add a new generation step
   */
  public function addGenerationStep($chapterOrder, $content, $settings, $isUserGenerated = true, $parentStepId = null)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      $this->initializeGenerationHistory($chapterOrder);
      $history = $this->generation_history;
    }
    
    $stepId = Str::uuid()->toString();
    $timestamp = now()->timestamp;
    
    // Get parent version index if parent step exists
    $parentVersionIndex = null;
    if ($parentStepId) {
      $parentVersionIndex = $history[$chapterOrder]['lastSelectedVersions'][$parentStepId] ?? 0;
    }
    
    $newStep = [
      'id' => $stepId,
      'parentId' => $parentStepId,
      'parentVersionIndex' => $parentVersionIndex,
      'content' => $content,
      'timestamp' => $timestamp,
      'settings' => $settings,
      'isUserGenerated' => $isUserGenerated,
      'versions' => [
        [
          'index' => 0,
          'content' => $content,
          'timestamp' => $timestamp,
        ]
      ],
    ];
    
    $history[$chapterOrder]['steps'][] = $newStep;
    $history[$chapterOrder]['currentStepId'] = $stepId;
    $history[$chapterOrder]['lastSelectedVersions'][$stepId] = 0;
    
    $this->update(['generation_history' => $history]);
    
    return $stepId;
  }

  /**
   * Add a new version to an existing step (regenerate)
   */
  public function addVersionToStep($chapterOrder, $stepId, $content)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return false;
    }
    
    $stepIndex = $this->findStepIndex($chapterOrder, $stepId);
    if ($stepIndex === -1) {
      return false;
    }
    
    $versions = $history[$chapterOrder]['steps'][$stepIndex]['versions'];
    $newVersionIndex = count($versions);
    
    $versions[] = [
      'index' => $newVersionIndex,
      'content' => $content,
      'timestamp' => now()->timestamp,
    ];
    
    $history[$chapterOrder]['steps'][$stepIndex]['versions'] = $versions;
    $history[$chapterOrder]['lastSelectedVersions'][$stepId] = $newVersionIndex;
    
    $this->update(['generation_history' => $history]);
    
    return $newVersionIndex;
  }

  /**
   * Switch to a different step
   */
  public function switchToStep($chapterOrder, $stepId, $versionIndex = null)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return false;
    }
    
    $stepIndex = $this->findStepIndex($chapterOrder, $stepId);
    if ($stepIndex === -1) {
      return false;
    }
    
    $step = $history[$chapterOrder]['steps'][$stepIndex];
    
    // Use provided version index or last selected version
    if ($versionIndex === null) {
      $versionIndex = $history[$chapterOrder]['lastSelectedVersions'][$stepId] ?? 0;
    }
    
    // Validate version index
    if ($versionIndex >= count($step['versions'])) {
      $versionIndex = count($step['versions']) - 1;
    }
    
    $history[$chapterOrder]['currentStepId'] = $stepId;
    $history[$chapterOrder]['lastSelectedVersions'][$stepId] = $versionIndex;
    
    $this->update(['generation_history' => $history]);
    
    // Update chapter content
    $content = $step['versions'][$versionIndex]['content'];
    $this->updateChapterContent($chapterOrder, $content);
    
    return [
      'stepId' => $stepId,
      'versionIndex' => $versionIndex,
      'content' => $content,
    ];
  }

  /**
   * Switch to a different version within the current step
   */
  public function switchVersion($chapterOrder, $versionIndex)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return false;
    }
    
    $currentStepId = $history[$chapterOrder]['currentStepId'];
    if (!$currentStepId) {
      return false;
    }
    
    return $this->switchToStep($chapterOrder, $currentStepId, $versionIndex);
  }

  /**
   * Get navigation info for undo/redo
   */
  public function getNavigationInfo($chapterOrder)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return [
        'canUndo' => false,
        'canRedo' => false,
        'currentStep' => null,
        'availableVersions' => [],
        'currentVersionIndex' => 0,
      ];
    }
    
    $currentStepId = $history[$chapterOrder]['currentStepId'];
    $currentStep = null;
    $canUndo = false;
    $canRedo = false;
    
    if ($currentStepId) {
      $stepIndex = $this->findStepIndex($chapterOrder, $currentStepId);
      if ($stepIndex !== -1) {
        $currentStep = $history[$chapterOrder]['steps'][$stepIndex];
        $canUndo = $currentStep['parentId'] !== null;
        
        // Check if we can redo - must have valid child steps for current version
        $canRedo = $this->hasValidChildStepsForCurrentVersion($chapterOrder, $currentStepId);
      }
    }
    
    $availableVersions = $currentStep ? $currentStep['versions'] : [];
    $currentVersionIndex = $currentStepId ? 
      ($history[$chapterOrder]['lastSelectedVersions'][$currentStepId] ?? 0) : 0;
    
    return [
      'canUndo' => $canUndo,
      'canRedo' => $canRedo,
      'currentStep' => $currentStep,
      'availableVersions' => $availableVersions,
      'currentVersionIndex' => $currentVersionIndex,
    ];
  }

  /**
   * Undo to parent step
   */
  public function undoToParent($chapterOrder)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return false;
    }
    
    $currentStepId = $history[$chapterOrder]['currentStepId'];
    if (!$currentStepId) {
      return false;
    }
    
    $stepIndex = $this->findStepIndex($chapterOrder, $currentStepId);
    if ($stepIndex === -1) {
      return false;
    }
    
    $currentStep = $history[$chapterOrder]['steps'][$stepIndex];
    $parentStepId = $currentStep['parentId'];
    
    if (!$parentStepId) {
      return false;
    }
    
    // Remember current step as last selected version for parent
    $parentStepIndex = $this->findStepIndex($chapterOrder, $parentStepId);
    if ($parentStepIndex !== -1) {
      // Get valid child steps for the parent's current version
      $validChildSteps = $this->getValidChildStepsForCurrentVersion($chapterOrder, $parentStepId);
      $childIndex = array_search($currentStepId, array_column($validChildSteps, 'id'));
      if ($childIndex !== false) {
        $history[$chapterOrder]['lastSelectedVersions'][$parentStepId . '_child'] = $childIndex;
        $this->update(['generation_history' => $history]);
      }
    }
    
    return $this->switchToStep($chapterOrder, $parentStepId);
  }

  /**
   * Redo to last selected child step
   */
  public function redoToChild($chapterOrder)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return false;
    }
    
    $currentStepId = $history[$chapterOrder]['currentStepId'];
    if (!$currentStepId) {
      return false;
    }
    
    // Get valid child steps for current version
    $validChildSteps = $this->getValidChildStepsForCurrentVersion($chapterOrder, $currentStepId);
    if (empty($validChildSteps)) {
      return false;
    }
    
    // Get last selected child or first child
    $lastSelectedChildIndex = $history[$chapterOrder]['lastSelectedVersions'][$currentStepId . '_child'] ?? 0;
    if ($lastSelectedChildIndex >= count($validChildSteps)) {
      $lastSelectedChildIndex = 0;
    }
    
    $targetStepId = $validChildSteps[$lastSelectedChildIndex]['id'];
    
    return $this->switchToStep($chapterOrder, $targetStepId);
  }

  /**
   * Find step index by step ID
   */
  public function findStepIndex($chapterOrder, $stepId)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return -1;
    }
    
    foreach ($history[$chapterOrder]['steps'] as $index => $step) {
      if ($step['id'] === $stepId) {
        return $index;
      }
    }
    
    return -1;
  }

  /**
   * Check if step has child steps
   */
  private function hasChildSteps($chapterOrder, $stepId)
  {
    return count($this->getChildSteps($chapterOrder, $stepId)) > 0;
  }

  /**
   * Check if step has valid child steps for current version
   */
  private function hasValidChildStepsForCurrentVersion($chapterOrder, $stepId)
  {
    return count($this->getValidChildStepsForCurrentVersion($chapterOrder, $stepId)) > 0;
  }

  /**
   * Get child steps for a given step
   */
  private function getChildSteps($chapterOrder, $stepId)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return [];
    }
    
    $childSteps = [];
    foreach ($history[$chapterOrder]['steps'] as $step) {
      if ($step['parentId'] === $stepId) {
        $childSteps[] = $step;
      }
    }
    
    // Sort by timestamp
    usort($childSteps, function($a, $b) {
      return $a['timestamp'] <=> $b['timestamp'];
    });
    
    return $childSteps;
  }

  /**
   * Get valid child steps for current version of parent step
   */
  private function getValidChildStepsForCurrentVersion($chapterOrder, $stepId)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return [];
    }
    
    // Get current version index of the parent step
    $currentVersionIndex = $history[$chapterOrder]['lastSelectedVersions'][$stepId] ?? 0;
    
    $validChildSteps = [];
    foreach ($history[$chapterOrder]['steps'] as $step) {
      if ($step['parentId'] === $stepId) {
        // Check if this child step was created from the current parent version
        $childParentVersionIndex = $step['parentVersionIndex'] ?? null;
        
        // If parentVersionIndex is not set (legacy data), allow all child steps
        // If it is set, only allow child steps created from current parent version
        if ($childParentVersionIndex === null || $childParentVersionIndex === $currentVersionIndex) {
          $validChildSteps[] = $step;
        }
      }
    }
    
    // Sort by timestamp
    usort($validChildSteps, function($a, $b) {
      return $a['timestamp'] <=> $b['timestamp'];
    });
    
    return $validChildSteps;
  }

  /**
   * Update chapter content directly
   */
  private function updateChapterContent($chapterOrder, $content)
  {
    $chapters = $this->content ?? [];
    
    foreach ($chapters as &$chapter) {
      if (isset($chapter['order']) && $chapter['order'] === $chapterOrder) {
        $chapter['content'] = $content;
        break;
      }
    }
    
    $this->update(['content' => $chapters]);
  }

  /**
   * Get current step and version info for a chapter
   */
  public function getCurrentStepInfo($chapterOrder)
  {
    $history = $this->generation_history ?? [];
    
    if (!isset($history[$chapterOrder])) {
      return null;
    }
    
    $currentStepId = $history[$chapterOrder]['currentStepId'];
    if (!$currentStepId) {
      return null;
    }
    
    $stepIndex = $this->findStepIndex($chapterOrder, $currentStepId);
    if ($stepIndex === -1) {
      return null;
    }
    
    $step = $history[$chapterOrder]['steps'][$stepIndex];
    $versionIndex = $history[$chapterOrder]['lastSelectedVersions'][$currentStepId] ?? 0;
    
    return [
      'stepId' => $currentStepId,
      'step' => $step,
      'versionIndex' => $versionIndex,
      'totalVersions' => count($step['versions']),
    ];
  }
}