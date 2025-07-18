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
        $requestData = [
            "author_name" => $this->authorName,
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

            // Make the API call
            $response = Http::timeout(300)->withoutVerifying()->asMultipart()->post($apiUrl, $multipartFiles);

            // Log the response
            Log::info('Author style analysis API response', [
                'status' => $response->status(),
                'success' => $response->successful(),
                'author_name' => $this->authorName,
                'duration_ms' => (int)((microtime(true) - $startTime) * 1000),
            ]);

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
