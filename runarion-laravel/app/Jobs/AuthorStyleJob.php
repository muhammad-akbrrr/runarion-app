<?php

namespace App\Jobs;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;
use App\Services\PythonServiceClient;

class AuthorStyleJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    /**
     * The number of seconds the job can run before timing out.
     * Style analysis requires multiple LLM calls and can take 10+ minutes.
     */
    public $timeout = 900; // 15 minutes

    /**
     * The number of times the job may be attempted.
     */
    public $tries = 2;

    protected $userId;
    protected $workspaceId;
    protected $projectId;
    protected $authorName;
    protected $authorFilePaths;

    /**
     * Create a new job instance.
     */
    public function __construct($userId, $workspaceId, $projectId, $authorName, $authorFilePaths)
    {
        $this->userId = $userId;
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->authorName = $authorName;
        $this->authorFilePaths = $authorFilePaths;
    }

    /**
     * Execute the job.
     */
    public function handle(): void
    {
        $startTime = microtime(true);
        $pythonClient = app(PythonServiceClient::class);

        // Prepare request data
        // on_exist: "update" allows re-running analysis if a previous attempt failed
        $requestData = [
            "author_name" => $this->authorName,
            "on_exist" => "update",
            "caller" => [
                "user_id" => (string)$this->userId,
                "workspace_id" => $this->workspaceId,
                "project_id" => $this->projectId
            ]
        ];

        try {
            Log::info('Author style analysis API response', [
                'author_name' => $this->authorName,
                'duration_ms' => (int)((microtime(true) - $startTime) * 1000),
            ]);
            $pythonClient->analyzeAuthorStyle($requestData, $this->authorFilePaths);

        } catch (\Exception $e) {
            Log::error('Exception in AuthorStyleJob', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
                'author_name' => $this->authorName,
                'duration_ms' => (int)((microtime(true) - $startTime) * 1000),
            ]);

            throw $e;
        } finally {
            // Clean up uploaded files
            foreach ($this->authorFilePaths as $path) {
                @unlink($path);
            }
        }
    }
}
