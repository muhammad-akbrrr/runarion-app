<?php

namespace App\Jobs;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use App\Models\DeconstructorLog;
use App\Notifications\ManuscriptDeconstructionCompleted;
use App\Models\User;
use Illuminate\Support\Str;

class ManuscriptDeconstructionJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    protected $userId;
    protected $workspaceId;
    protected $projectId;
    protected $draftFullPath;
    protected $authorStyleType;
    protected $authorStyleId;
    protected $authorSamplePaths;
    protected $newAuthorName;
    protected $writingPerspective;

    /**
     * Create a new job instance.
     */
    public function __construct($userId, $workspaceId, $projectId, $draftFullPath, $authorStyleType, $authorStyleId, $authorSamplePaths, $newAuthorName, $writingPerspective)
    {
        $this->userId = $userId;
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->draftFullPath = $draftFullPath;
        $this->authorStyleType = $authorStyleType;
        $this->authorStyleId = $authorStyleId;
        $this->authorSamplePaths = $authorSamplePaths;
        $this->newAuthorName = $newAuthorName;
        $this->writingPerspective = $writingPerspective;
    }

    /**
     * Execute the job.
     */
    public function handle(): void
    {
        $user = User::find($this->userId);
        $requestId = (string) Str::ulid();
        DeconstructorLog::create([
            'id' => $requestId,
            'user_id' => $this->userId,
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'rough_draft_path' => $this->draftFullPath,
            'author_style_info' => null,
            'author_style_id' => $this->authorStyleId,
            'writing_perspective' => $this->writingPerspective,
            'caller_info' => [
                'user_id' => $this->userId,
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId,
            ],
            'requested_at' => now(),
            'status' => 'pending',
        ]);

        $apiUrl = config('services.deconstructor.url');
        Log::info('Prepared multipart data for Python API (from Job)', [
            'fields' => isset($fields) ? $fields : null,
            'draftFullPath' => $this->draftFullPath,
            'authorSamplePaths' => $this->authorSamplePaths,
        ]);

        $perspectiveMap = [
            '1st-person' => 'first_person',
            '2nd-person' => 'second_person',
            '3rd-person-omniscient' => 'third_person_omniscient',
            '3rd-person-limited' => 'third_person_limited',
        ];

        $writingPerspective = $perspectiveMap[$this->writingPerspective] ?? $this->writingPerspective;

        // Prepare fields for the request
        $fields = [
            'author_style_type' => $this->authorStyleType,
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'user_id' => $this->userId,
            'writing_perspective_type' => $writingPerspective,
            'id' => $requestId,
        ];
        if ($this->authorStyleType === 'existing') {
            $fields['author_style_id'] = $this->authorStyleId;
        } else if ($this->authorStyleType === 'new') {
            $fields['author_name'] = $this->newAuthorName;
        }

        // Log the actual fields array
        Log::info('Prepared fields for Python API (from Job)', [
            'fields' => $fields,
            'draftFullPath' => $this->draftFullPath,
            'authorSamplePaths' => $this->authorSamplePaths,
        ]);

        // Warn if any required field is null
        $requiredFields = ['author_style_type', 'workspace_id', 'project_id', 'user_id', 'writing_perspective_type', 'id'];
        foreach ($requiredFields as $key) {
            if (!isset($fields[$key]) || $fields[$key] === null) {
                Log::warning("Field $key is null and will not be sent");
            }
        }

        try {
            $http = Http::attach(
                'rough_draft',
                fopen($this->draftFullPath, 'r'),
                basename($this->draftFullPath)
            );

            if ($this->authorStyleType === 'new') {
                foreach ($this->authorSamplePaths as $idx => $path) {
                    $http = $http->attach('author_samples', fopen($path, 'r'), basename($path));
                }
            }

            $response = $http->post($apiUrl, $fields);
            Log::info('Python API response (from Job)', ['status' => $response->status(), 'body' => $response->body()]);
        } catch (\Exception $e) {
            Log::error('Exception in ManuscriptDeconstructionJob', ['error' => $e->getMessage()]);
        } finally {
            // Clean up uploaded files
            @unlink($this->draftFullPath);
            foreach ($this->authorSamplePaths as $path) {
                @unlink($path);
            }
            Log::info('Deconstruction job completed for request_id: ' . $requestId);
            if ($user) {
                try {
                    $user->notify(new ManuscriptDeconstructionCompleted($requestId));
                } catch (\Exception $e) {
                    Log::error('Failed to send notification', ['error' => $e->getMessage()]);
                }
            }
        }
    }
}
