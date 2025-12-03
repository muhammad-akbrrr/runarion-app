<?php

namespace App\Jobs;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

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
        $apiUrl = "http://python-app:5000/api/analyze-style";

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
            // Prepare multipart request
            $multipartFiles = [];
            $fileHandles = []; // Track handles for cleanup
            
            foreach ($this->authorFilePaths as $index => $path) {
                $handle = fopen($path, 'r');
                if (!$handle) {
                    throw new \Exception("Cannot open file: $path");
                }
                
                $fileHandles[] = $handle;
                $multipartFiles[] = [
                    'name' => 'files',
                    'contents' => $handle,
                    'filename' => basename($path)
                ];
            }

            // Add the JSON data as a part of the multipart request
            $multipartFiles[] = [
                'name' => 'data',
                'contents' => json_encode($requestData)
            ];

            // Make the API call - style analysis can take 10+ minutes with multiple LLM calls
            $response = Http::timeout(840)->withoutVerifying()->asMultipart()->post($apiUrl, $multipartFiles);

            // Log the response with body for debugging
            Log::info('Author style analysis API response', [
                'status' => $response->status(),
                'success' => $response->successful(),
                'author_name' => $this->authorName,
                'duration_ms' => (int)((microtime(true) - $startTime) * 1000),
                'response_body' => $response->successful() ? 'success' : $response->body(),
            ]);

            // Throw exception if request failed to trigger job retry
            if (!$response->successful()) {
                throw new \Exception("API request failed with status {$response->status()}: {$response->body()}");
            }

        } catch (\Exception $e) {
            Log::error('Exception in AuthorStyleJob', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
                'author_name' => $this->authorName,
                'duration_ms' => (int)((microtime(true) - $startTime) * 1000),
            ]);
        } finally {
            // Close file handles if they exist
            if (isset($fileHandles)) {
                foreach ($fileHandles as $handle) {
                    if (is_resource($handle)) {
                        fclose($handle);
                    }
                }
            }
            
            // Clean up uploaded files
            foreach ($this->authorFilePaths as $path) {
                @unlink($path);
            }
        }
    }
}
