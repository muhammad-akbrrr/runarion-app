<?php

namespace App\Jobs;

use App\Events\LLMStreamChunk;
use App\Events\LLMStreamCompleted;
use App\Events\LLMStreamStarted;
use App\Events\ProjectContentUpdated;
use App\Models\ProjectContent;
use App\Models\Projects;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
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
    public int $timeout = 180; // 3 minutes timeout
    public int $tries = 1; // No retries for streaming jobs

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
        ?string $sessionId = null
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->prompt = $prompt;
        $this->settings = $settings;
        $this->sessionId = $sessionId ?? Str::uuid()->toString();
        $this->userId = $userId;
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
            ]);

            // Broadcast stream started event
            broadcast(new LLMStreamStarted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId
            ));

            // Get current chapter content for context
            $currentChapterContent = $this->getCurrentChapterContent();

            // Prepare request data for Python service
            $requestData = $this->prepareRequestData($currentChapterContent);

            // Make streaming request to Python service
            $this->streamFromPythonService($requestData);

        } catch (\Exception $e) {
            Log::error('LLM streaming job failed', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            // Broadcast error event
            broadcast(new LLMStreamCompleted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId,
                '',
                false,
                $e->getMessage()
            ));
        }
    }

    /**
     * Get current chapter content for context
     */
    private function getCurrentChapterContent(): string
    {
        $projectContent = ProjectContent::where('project_id', $this->projectId)->first();
        
        if (!$projectContent) {
            return '';
        }

        $chapters = $projectContent->content ?? [];
        foreach ($chapters as $chapter) {
            if (isset($chapter['order']) && $chapter['order'] === $this->chapterOrder) {
                return $chapter['content'] ?? '';
            }
        }

        return '';
    }

    /**
     * Prepare request data for Python service
     */
    private function prepareRequestData(string $currentChapterContent): array
    {
        return [
            'usecase' => 'story',
            'provider' => $this->determineProvider(),
            'model' => $this->settings['aiModel'] ?? 'gpt-4o-mini',
            'prompt' => $this->prompt,
            'instruction' => 'Continue the story in a coherent and engaging way, maintaining the same style, tone, and narrative voice.',
            'stream' => true, // Enable streaming
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
                'context' => $currentChapterContent,
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
        $model = $this->settings['aiModel'] ?? 'gpt-4o-mini';
        
        if (stripos($model, 'gpt') !== false) {
            return 'openai';
        } elseif (stripos($model, 'gemini') !== false) {
            return 'gemini';
        } elseif (stripos($model, 'deepseek') !== false) {
            return 'deepseek';
        }
        
        return 'openai';
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

        // Create HTTP client with streaming support
        $response = Http::timeout($this->timeout)
            ->withHeaders([
                'Content-Type' => 'application/json',
                'Accept' => 'text/event-stream',
            ])
            ->withOptions([
                'stream' => true,
                'read_timeout' => $this->timeout,
            ])
            ->post($pythonServiceUrl . '/api/stream', $requestData);

        if (!$response->successful()) {
            throw new \Exception('Failed to connect to Python service: ' . $response->body());
        }

        // Process streaming response
        $body = $response->getBody();
        $buffer = '';

        while (!$body->eof()) {
            $chunk = $body->read(1024);
            $buffer .= $chunk;

            // Process complete lines
            while (($pos = strpos($buffer, "\n\n")) !== false) {
                $line = substr($buffer, 0, $pos);
                $buffer = substr($buffer, $pos + 2);

                $this->processStreamLine($line, $fullText, $chunkIndex);
            }
        }

        // Process any remaining buffer
        if (!empty($buffer)) {
            $this->processStreamLine($buffer, $fullText, $chunkIndex);
        }

        // Update project content with final text
        $this->updateProjectContent($fullText);

        // Broadcast completion event
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
        ]);
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

        $data = substr($line, 6); // Remove 'data: ' prefix
        
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

            // Check for error
            if (isset($decoded['error'])) {
                Log::error('Error in stream', [
                    'session_id' => $this->sessionId,
                    'error' => $decoded['error'],
                ]);
                throw new \Exception($decoded['error']);
            }

            // Extract text chunk - assuming Flask always returns in the same format with 'chunk' field
            $textChunk = $decoded['chunk'] ?? '';
            
            if (!empty($textChunk)) {
                $fullText .= $textChunk;
                
                // Broadcast chunk event
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
     * Update project content with generated text
     */
    private function updateProjectContent(string $generatedText): void
    {
        if (empty($generatedText)) {
            return;
        }

        $projectContent = ProjectContent::where('project_id', $this->projectId)->first();
        
        if (!$projectContent) {
            Log::error('Project content not found', [
                'session_id' => $this->sessionId,
                'project_id' => $this->projectId,
            ]);
            return;
        }

        $chapters = $projectContent->content ?? [];
        $updatedContent = '';
        
        foreach ($chapters as &$chapter) {
            if (isset($chapter['order']) && $chapter['order'] === $this->chapterOrder) {
                $existingContent = $chapter['content'] ?? '';
                
                // Add space if needed
                if ($existingContent !== '' && 
                    substr($existingContent, -1) !== ' ' && 
                    substr($generatedText, 0, 1) !== ' ') {
                    $existingContent .= ' ';
                }
                
                $chapter['content'] = $existingContent . $generatedText;
                $updatedContent = $chapter['content'];
                break;
            }
        }
        
        $projectContent->content = $chapters;
        $projectContent->updateLastEdited($this->userId);
        $projectContent->save();

        // Broadcast content updated event
        broadcast(new ProjectContentUpdated(
            $this->workspaceId,
            $this->projectId,
            $this->chapterOrder,
            $updatedContent,
            'llm_generation'
        ));

        Log::info('Project content updated', [
            'session_id' => $this->sessionId,
            'chapter_order' => $this->chapterOrder,
            'generated_length' => strlen($generatedText),
        ]);
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

        // Broadcast error event
        broadcast(new LLMStreamCompleted(
            $this->workspaceId,
            $this->projectId,
            $this->chapterOrder,
            $this->sessionId,
            '',
            false,
            'Job failed: ' . $exception->getMessage()
        ));
    }
}
