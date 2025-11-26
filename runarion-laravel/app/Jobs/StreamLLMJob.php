<?php

namespace App\Jobs;

use App\Events\LLMStreamChunk;
use App\Events\LLMStreamCompleted;
use App\Events\LLMStreamStarted;
use App\Events\ProjectContentUpdated;
use App\Models\ProjectContent;
use App\Models\Projects;
use App\Services\VersionControlService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class StreamLLMJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int $chapterOrder;
    public string $prompt;
    public array $settings;
    public string $sessionId;
    public int $userId;
    public bool $isRegenerate;
    public ?string $regenerateNodeId;
    public int $timeout = 180;
    public int $tries = 1;
    
    private const REDIS_BUFFER_TTL = 300;

    /**
     * Create a new job instance.
     */
    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $prompt,
        array $settings,
        int $userId,
        ?string $sessionId = null,
        bool $isRegenerate = false,
        ?string $regenerateNodeId = null
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->prompt = $prompt;
        $this->settings = $settings;
        $this->sessionId = $sessionId ?? Str::uuid()->toString();
        $this->userId = $userId;
        $this->isRegenerate = $isRegenerate;
        $this->regenerateNodeId = $regenerateNodeId;
    }

    /**
     * Execute the job.
     */
    public function handle(): void
    {
        try {
            Log::info('Starting LLM streaming job', [
                'session_id' => $this->sessionId,
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId,
                'chapter_order' => $this->chapterOrder,
                'is_regenerate' => $this->isRegenerate,
            ]);

            broadcast(new LLMStreamStarted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId,
                $this->isRegenerate
            ));

            $requestData = $this->prepareRequestData();
            $this->streamFromPythonService($requestData);

        } catch (\Exception $e) {
            Log::error('LLM streaming job failed', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            $errorType = 'generation_failed';
            $errorMessage = $e->getMessage();
            
            if (str_contains($errorMessage, 'quota') || str_contains($errorMessage, 'limit') || str_contains($errorMessage, '429')) {
                $errorType = 'quota_exceeded';
                $errorMessage = 'Generation quota exceeded. Please try again later.';
            }

            broadcast(new LLMStreamCompleted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId,
                '',
                false,
                $errorMessage,
                $errorType
            ));
        }
    }

    /**
     * Prepare request data for Python service
     */
    private function prepareRequestData(): array
    {
        return [
            'usecase' => 'story',
            'provider' => $this->determineProvider(),
            'model' => $this->settings['aiModel'] ?? 'gemini-2.0-flash',
            'prompt' => $this->prompt,
            'instruction' => 'Continue the story in a coherent and engaging way, maintaining the same style, tone, and narrative voice. Return the continuation exclusively in Markdown format with no HTML escaping or wrappers.',
            'stream' => true,
            'generation_config' => [
                'temperature' => $this->settings['temperature'] ?? 1,
                'max_output_tokens' => $this->settings['outputLength'] ?? 300,
                'nucleus_sampling' => $this->settings['topP'] ?? 0.85,
                'top_k' => $this->settings['topK'] ?? 0.85,
                'repetition_penalty' => $this->settings['repetitionPenalty'] ?? 0.0,
                'tail_free_sampling' => $this->settings['tailFree'] ?? 0.85,
                'top_a' => $this->settings['topA'] ?? 0.85,
                'min_output_tokens' => $this->settings['minOutputToken'] ?? 50,
                'phrase_bias' => $this->settings['phraseBias'] ?? [],
                'banned_tokens' => $this->settings['bannedPhrases'] ?? [],
                'stop_sequences' => $this->settings['stopSequences'] ?? [],
            ],
            'prompt_config' => [
                'current_preset' => $this->settings['currentPreset'] ?? '',
                'context' => $this->settings['memory'] ?? '',
                'genre' => $this->settings['storyGenre'] ?? '',
                'tone' => $this->settings['storyTone'] ?? '',
                'pov' => $this->settings['storyPov'] ?? '',
            ],
            'caller' => [
                'user_id' => (string)$this->userId,
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId,
                'session_id' => $this->sessionId,
                'api_keys' => [
                    'openai' => env('OPENAI_API_KEY', ''),
                    'gemini' => env('GEMINI_API_KEY', ''),
                    'deepseek' => env('DEEPSEEK_API_KEY', ''),
                ],
            ],
        ];
    }

    /**
     * Determine AI provider based on model
     */
    private function determineProvider(): string
    {
        $model = $this->settings['aiModel'] ?? 'gemini-2.0-flash';
        
        if (stripos($model, 'gemini') !== false) {
            return 'gemini';
        } elseif (stripos($model, 'gpt') !== false) {
            return 'openai';
        } elseif (stripos($model, 'gemini') !== false) {
            return 'gemini';
        } elseif (stripos($model, 'deepseek') !== false) {
            return 'deepseek';
        }
        
        return 'gemini';
    }

    /**
     * Stream from Python service and broadcast chunks
     */
    private function streamFromPythonService(array $requestData): void
    {
        $fullText = '';
        $chunkIndex = 0;
        $pythonServiceUrl = env('PYTHON_SERVICE_URL', 'http://python-app:5000');

        Log::info('Making streaming request to Python service', [
            'session_id' => $this->sessionId,
            'url' => $pythonServiceUrl . '/api/stream',
        ]);

        try {
            $response = Http::timeout($this->timeout)
                ->withHeaders([
                    'Content-Type' => 'application/json',
                    'Accept' => 'text/event-stream',
                    'Connection' => 'keep-alive',
                ])
                ->withOptions([
                    'stream' => true,
                    'read_timeout' => $this->timeout,
                    'connect_timeout' => 30,
                ])
                ->post($pythonServiceUrl . '/api/stream', $requestData);

            if (!$response->successful()) {
                throw new \Exception('Failed to connect to Python service: ' . $response->body());
            }

            $body = $response->getBody();
            $buffer = '';

            while (!$body->eof()) {
                $chunk = $body->read(1024);
                $buffer .= $chunk;

                while (($pos = strpos($buffer, "\n\n")) !== false) {
                    $line = substr($buffer, 0, $pos);
                    $buffer = substr($buffer, $pos + 2);

                    $this->processStreamLine($line, $fullText, $chunkIndex);
                }
            }

            if (!empty($buffer)) {
                $this->processStreamLine($buffer, $fullText, $chunkIndex);
            }

            $this->updateProjectContentOptimized($fullText);

            broadcast(new LLMStreamCompleted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId,
                $fullText,
                true
            ));

            Log::info('LLM streaming completed successfully', [
                'session_id' => $this->sessionId,
                'total_chunks' => $chunkIndex,
                'total_length' => strlen($fullText),
                'is_regenerate' => $this->isRegenerate,
            ]);

        } catch (\Exception $e) {
            Log::error('Streaming error', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
            ]);
            throw $e;
        }
    }

    /**
     * Process individual stream line
     */
    private function processStreamLine(string $line, string &$fullText, int &$chunkIndex): void
    {
        $line = trim($line);
        
        if (empty($line) || !str_starts_with($line, 'data: ')) {
            return;
        }

        $data = substr($line, 6);
        
        if ($data === '[DONE]') {
            return;
        }

        try {
            $decoded = json_decode($data, true);
            
            if (json_last_error() !== JSON_ERROR_NONE) {
                Log::warning('Invalid JSON in stream', [
                    'session_id' => $this->sessionId,
                    'data' => $data,
                ]);
                return;
            }

            if (isset($decoded['error'])) {
                Log::error('Error in stream', [
                    'session_id' => $this->sessionId,
                    'error' => $decoded['error'],
                ]);
                throw new \Exception($decoded['error']);
            }

            $textChunk = $decoded['chunk'] ?? '';
            
            if (!empty($textChunk)) {
                $fullText .= $textChunk;
                
                broadcast(new LLMStreamChunk(
                    $this->workspaceId,
                    $this->projectId,
                    $this->chapterOrder,
                    $this->sessionId,
                    $textChunk,
                    $chunkIndex
                ));
                
                $chunkIndex++;
            }
        } catch (\Exception $e) {
            Log::warning('Error processing stream chunk', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'data' => $data,
            ]);
            throw $e;
        }
    }

    /**
     * Update project content with generated text using optimized version control
     */
    private function updateProjectContentOptimized(string $generatedText): void
    {
        if (empty($generatedText)) {
            return;
        }

        DB::transaction(function () use ($generatedText) {
            $versionControlService = app(VersionControlService::class);
            
            $baseContent = $this->prompt;
            $finalContent = $baseContent;
            
            if ($baseContent !== '') {
                if (!str_ends_with($baseContent, "\n") && !str_starts_with($generatedText, "\n")) {
                    if (!str_ends_with($baseContent, " ")) {
                        $finalContent .= " ";
                    }
                }
            }
            
            $finalContent .= $generatedText;

            if ($this->isRegenerate && $this->regenerateNodeId) {
                // Add new version to the specified node (not current state)
                $versionIndex = $versionControlService->addVersion($this->regenerateNodeId, $finalContent);
                
                Log::info('Added new version to regenerate node', [
                    'session_id' => $this->sessionId,
                    'chapter_order' => $this->chapterOrder,
                    'node_id' => $this->regenerateNodeId,
                    'version_index' => $versionIndex,
                    'final_content_length' => strlen($finalContent),
                ]);
            } else {
                // Create new node with current node as parent
                $currentState = $versionControlService->getCurrentState($this->projectId, $this->chapterOrder);
                $parentNodeId = $currentState ? $currentState['node_id'] : null;
                $parentVersionIndex = $currentState ? $currentState['version_index'] : null;
                
                $nodeId = $versionControlService->createNode(
                    $this->projectId,
                    $this->chapterOrder,
                    $finalContent,
                    $this->settings,
                    $parentNodeId,
                    $parentVersionIndex
                );
                
                Log::info('Created new generation node', [
                    'session_id' => $this->sessionId,
                    'chapter_order' => $this->chapterOrder,
                    'node_id' => $nodeId,
                    'parent_node_id' => $parentNodeId,
                    'parent_version_index' => $parentVersionIndex,
                    'final_content_length' => strlen($finalContent),
                ]);
            }

            // Clear cache to ensure fresh data
            $this->clearCache($this->projectId, $this->chapterOrder);
        });

        // Broadcast content updated event after transaction
        broadcast(new ProjectContentUpdated(
            $this->workspaceId,
            $this->projectId,
            $this->chapterOrder,
            $generatedText, // Send only the generated part for streaming
            $this->isRegenerate ? 'llm_regeneration' : 'llm_generation'
        ));
    }

    private function clearCache(string $projectId, int $chapterOrder): void
    {
        Cache::forget("content:{$projectId}:{$chapterOrder}");
        Cache::forget("navigation:{$projectId}:{$chapterOrder}");
    }

    /**
     * Handle job failure.
     */
    public function failed(\Throwable $exception): void
    {
        Log::error('StreamLLMJob failed', [
            'session_id' => $this->sessionId,
            'error' => $exception->getMessage(),
            'trace' => $exception->getTraceAsString(),
        ]);

        // Determine error type
        $errorType = 'generation_failed';
        $errorMessage = 'Job failed: ' . $exception->getMessage();
        
        if (str_contains($exception->getMessage(), 'quota') || str_contains($exception->getMessage(), 'limit')) {
            $errorType = 'quota_exceeded';
            $errorMessage = 'Generation quota exceeded. Please try again later.';
        }

        // Broadcast error event
        broadcast(new LLMStreamCompleted(
            $this->workspaceId,
            $this->projectId,
            $this->chapterOrder,
            $this->sessionId,
            '',
            false,
            $errorMessage,
            $errorType
        ));
    }
}
