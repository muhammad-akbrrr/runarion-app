<?php

namespace App\Jobs;

use App\Events\LLMStreamChunk;
use App\Events\LLMStreamCompleted;
use App\Events\LLMStreamStarted;
use App\Events\ProjectContentUpdated;
use App\Models\AuthorStyle;
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
                'attempt' => $this->attempts(),
            ]);

            // Broadcast stream started event
            $event = new LLMStreamStarted(
                $this->workspaceId,
                $this->projectId,
                $this->chapterOrder,
                $this->sessionId,
                $this->isRegenerate
            );
            
            broadcast($event);
            
            Log::info('LLMStreamStarted event broadcasted', [
                'channel' => "project.{$this->workspaceId}.{$this->projectId}",
                'session_id' => $this->sessionId,
                'chapter_order' => $this->chapterOrder,
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId,
            ]);

            $requestData = $this->prepareRequestData();
            $this->streamFromPythonService($requestData);

        } catch (\Illuminate\Http\Client\ConnectionException $e) {
            Log::error('Connection error in LLM streaming job', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'attempt' => $this->attempts(),
            ]);

            $this->handleStreamingError($e, 'connection_error', 
                'Failed to connect to AI service. Please check your connection and try again.');

        } catch (\Illuminate\Http\Client\RequestException $e) {
            Log::error('Request error in LLM streaming job', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'status' => $e->response?->status(),
                'attempt' => $this->attempts(),
            ]);

            $errorType = 'generation_failed';
            $errorMessage = 'AI service request failed. Please try again.';
            
            if ($e->response) {
                $status = $e->response->status();
                
                if ($status === 429) {
                    $errorType = 'quota_exceeded';
                    $errorMessage = 'Generation quota exceeded. Please try again later.';
                } elseif ($status === 401 || $status === 403) {
                    $errorType = 'authentication_error';
                    $errorMessage = 'AI service authentication failed. Please check your API keys.';
                } elseif ($status === 400) {
                    $errorType = 'invalid_request';
                    $errorMessage = 'Invalid generation request. Please check your settings.';
                } elseif ($status >= 500) {
                    $errorType = 'service_error';
                    $errorMessage = 'AI service is temporarily unavailable. Please try again later.';
                }
            }

            $this->handleStreamingError($e, $errorType, $errorMessage);

        } catch (\Exception $e) {
            Log::error('Unexpected error in LLM streaming job', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'type' => get_class($e),
                'trace' => $e->getTraceAsString(),
                'attempt' => $this->attempts(),
            ]);

            $errorType = 'generation_failed';
            $errorMessage = $e->getMessage();
            
            // Categorize common errors
            if (str_contains($errorMessage, 'quota') || str_contains($errorMessage, 'limit') || str_contains($errorMessage, '429')) {
                $errorType = 'quota_exceeded';
                $errorMessage = 'Generation quota exceeded. Please try again later.';
            } elseif (str_contains($errorMessage, 'timeout')) {
                $errorType = 'timeout_error';
                $errorMessage = 'Generation timed out. Please try again with shorter content or lower output length.';
            } elseif (str_contains($errorMessage, 'memory') || str_contains($errorMessage, 'out of memory')) {
                $errorType = 'memory_error';
                $errorMessage = 'Insufficient memory for generation. Please try with shorter content.';
            } elseif (str_contains($errorMessage, 'token')) {
                $errorType = 'token_limit_error';
                $errorMessage = 'Content exceeds token limit. Please reduce the input size.';
            }

            $this->handleStreamingError($e, $errorType, $errorMessage);
        }
    }

    /**
     * Handle streaming errors with proper logging and broadcasting
     */
    private function handleStreamingError(\Exception $e, string $errorType, string $errorMessage): void
    {
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

    /**
     * Prepare request data for Python service
     */
    private function prepareRequestData(): array
    {
        // Process writing guidance from the prompt
        $processedPrompt = $this->processWritingGuidance($this->prompt);
        
        return [
            'usecase' => 'story',
            'provider' => $this->determineProvider(),
            'model' => $this->settings['aiModel'] ?? 'gemini-2.0-flash',
            'prompt' => $processedPrompt['baseContent'],
            'writing_guidance' => $processedPrompt['guidance'],
            'chapter_order' => $this->chapterOrder, // Include chapter_order for conversation history
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
                // Gemini thinking config - null uses model-specific defaults
                // Set to 0 to disable thinking, or a positive value for custom budget
                'thinking_budget' => $this->settings['thinkingBudget'] ?? null,
                'include_thinking' => $this->settings['includeThinking'] ?? false,
            ],
            'prompt_config' => $this->buildPromptConfig(),
            'caller' => [
                'user_id' => (string)$this->userId,
                'workspace_id' => $this->workspaceId,
                'project_id' => $this->projectId, // Required for conversation history
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
     * Process writing guidance from content.
     * Extracts text within parentheses ((), [], {}) as guidance instructions for the AI.
     * Returns both the base content (without markers) for AI processing and the guidance array.
     * 
     * NOTE: The guidance markers are NOT removed from the editor content - they remain visible.
     * This method only extracts them for sending to the AI as separate instructions.
     * 
     * @param string $content The content to process
     * @return array Array with 'baseContent' (for AI) and 'guidance' keys
     */
    private function processWritingGuidance(string $content): array
    {
        $guidance = [];
        $baseContent = $content;
        
        // Match all types of parentheses: (), [], {}
        // This regex captures text within any type of bracket
        $pattern = '/[\(\[\{]([^\)\]\}]+)[\)\]\}]/';
        
        // Extract all guidance instructions
        if (preg_match_all($pattern, $content, $matches)) {
            if (!empty($matches[1])) {
                $guidance = $matches[1];
                
                // Remove guidance markers from base content FOR AI PROCESSING ONLY
                // The original content in the editor remains unchanged
                $baseContent = preg_replace($pattern, '', $content);
                
                // Clean up extra whitespace that may result from removal
                $baseContent = preg_replace('/\s+/', ' ', $baseContent);
                $baseContent = trim($baseContent);
            }
        }
        
        Log::info('Processed writing guidance', [
            'session_id' => $this->sessionId,
            'original_length' => strlen($content),
            'base_content_length' => strlen($baseContent),
            'guidance_count' => count($guidance),
            'guidance' => $guidance,
        ]);
        
        return [
            'baseContent' => $baseContent,
            'guidance' => $guidance,
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
     * Build the prompt configuration with logging.
     * 
     * @return array
     */
    private function buildPromptConfig(): array
    {
        $authorProfileId = $this->settings['authorProfile'] ?? null;
        $authorStyleDna = $this->getFormattedAuthorStyle($authorProfileId);
        
        Log::info('Building prompt_config for generation', [
            'author_profile_id' => $authorProfileId,
            'author_style_found' => !empty($authorStyleDna),
            'author_style_length' => strlen($authorStyleDna),
            'preset' => $this->settings['currentPreset'] ?? 'none',
            'genre' => $this->settings['storyGenre'] ?? 'none',
            'tone' => $this->settings['storyTone'] ?? 'none',
            'pov' => $this->settings['storyPov'] ?? 'none',
            'session_id' => $this->sessionId,
        ]);
        
        return [
            'current_preset' => $this->settings['currentPreset'] ?? '',
            'context' => $this->settings['memory'] ?? '',
            'genre' => $this->settings['storyGenre'] ?? '',
            'tone' => $this->settings['storyTone'] ?? '',
            'pov' => $this->settings['storyPov'] ?? '',
            'author_profile' => $authorStyleDna,
        ];
    }

    /**
     * Look up and format AuthorStyle data from the database.
     * 
     * The AuthorStyle contains techniques_json and examples_json which need to be
     * formatted into a readable style DNA text for the AI prompt.
     * 
     * @param string|null $authorProfileId The AuthorStyle ID from the sidebar selection
     * @return string Formatted style DNA text, or empty string if not found
     */
    private function getFormattedAuthorStyle(?string $authorProfileId): string
    {
        if (empty($authorProfileId)) {
            return '';
        }

        try {
            $authorStyle = AuthorStyle::find($authorProfileId);
            
            if (!$authorStyle || $authorStyle->status !== 'profiling_completed') {
                Log::warning('AuthorStyle not found or not completed', [
                    'author_profile_id' => $authorProfileId,
                    'session_id' => $this->sessionId,
                ]);
                return '';
            }

            $styleDna = [];
            $styleDna[] = "AUTHOR STYLE: {$authorStyle->author_name}";
            $styleDna[] = "";

            // Format techniques
            $techniques = $authorStyle->techniques_json;
            if (!empty($techniques)) {
                $styleDna[] = "WRITING TECHNIQUES:";
                
                // Dialogue techniques
                if (!empty($techniques['dialogue'])) {
                    $d = $techniques['dialogue'];
                    if (!empty($d['conversation_style'])) {
                        $styleDna[] = "- Dialogue Style: {$d['conversation_style']}";
                    }
                    if (!empty($d['dialogue_balance'])) {
                        $styleDna[] = "- Dialogue Balance: {$d['dialogue_balance']}";
                    }
                    if (!empty($d['character_voices'])) {
                        $styleDna[] = "- Character Voices: {$d['character_voices']}";
                    }
                }
                
                // Action techniques
                if (!empty($techniques['action'])) {
                    $a = $techniques['action'];
                    if (!empty($a['action_sequences'])) {
                        $styleDna[] = "- Action Sequences: {$a['action_sequences']}";
                    }
                    if (!empty($a['tension'])) {
                        $styleDna[] = "- Tension Building: {$a['tension']}";
                    }
                }
                
                // Worldbuilding techniques
                if (!empty($techniques['worldbuilding'])) {
                    $w = $techniques['worldbuilding'];
                    if (!empty($w['world_reveals'])) {
                        $styleDna[] = "- World Reveals: {$w['world_reveals']}";
                    }
                    if (!empty($w['exposition'])) {
                        $styleDna[] = "- Exposition Style: {$w['exposition']}";
                    }
                }
                
                // Description techniques
                if (!empty($techniques['descriptions'])) {
                    $desc = $techniques['descriptions'];
                    if (!empty($desc['character_descriptions'])) {
                        $styleDna[] = "- Character Descriptions: {$desc['character_descriptions']}";
                    }
                    if (!empty($desc['scene_painting'])) {
                        $styleDna[] = "- Scene Painting: {$desc['scene_painting']}";
                    }
                    if (!empty($desc['atmosphere'])) {
                        $styleDna[] = "- Atmosphere: {$desc['atmosphere']}";
                    }
                }
                
                // Literary techniques
                if (!empty($techniques['literary'])) {
                    $l = $techniques['literary'];
                    if (!empty($l['devices'])) {
                        $styleDna[] = "- Literary Devices: {$l['devices']}";
                    }
                    if (!empty($l['metaphors'])) {
                        $styleDna[] = "- Metaphor Usage: {$l['metaphors']}";
                    }
                    if (!empty($l['pacing'])) {
                        $styleDna[] = "- Pacing: {$l['pacing']}";
                    }
                    if (!empty($l['scene_structure'])) {
                        $styleDna[] = "- Scene Structure: {$l['scene_structure']}";
                    }
                }
            }

            // Format examples (include a few key examples)
            $examples = $authorStyle->examples_json;
            if (!empty($examples)) {
                $styleDna[] = "";
                $styleDna[] = "STYLE EXAMPLES:";
                
                // Add dialogue examples
                if (!empty($examples['dialogue']) && count($examples['dialogue']) > 0) {
                    $styleDna[] = "Dialogue Example: \"{$examples['dialogue'][0]}\"";
                }
                
                // Add description examples
                if (!empty($examples['descriptions']) && count($examples['descriptions']) > 0) {
                    $styleDna[] = "Description Example: \"{$examples['descriptions'][0]}\"";
                }
            }

            $result = implode("\n", $styleDna);
            
            Log::info('Formatted AuthorStyle for generation', [
                'author_profile_id' => $authorProfileId,
                'author_name' => $authorStyle->author_name,
                'style_dna_length' => strlen($result),
                'session_id' => $this->sessionId,
            ]);

            return $result;

        } catch (\Exception $e) {
            Log::error('Failed to format AuthorStyle', [
                'author_profile_id' => $authorProfileId,
                'error' => $e->getMessage(),
                'session_id' => $this->sessionId,
            ]);
            return '';
        }
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
            'model' => $requestData['model'] ?? 'unknown',
            'provider' => $requestData['provider'] ?? 'unknown',
        ]);

        try {
            $response = Http::timeout($this->timeout)
                ->retry(2, 1000, function ($exception, $request) {
                    // Retry on connection errors and 5xx errors
                    if ($exception instanceof \Illuminate\Http\Client\ConnectionException) {
                        Log::warning('Connection error, retrying...', [
                            'session_id' => $this->sessionId,
                            'error' => $exception->getMessage()
                        ]);
                        return true;
                    }
                    
                    if ($exception instanceof \Illuminate\Http\Client\RequestException) {
                        $status = $exception->response?->status();
                        if ($status && $status >= 500 && $status < 600) {
                            Log::warning('Server error, retrying...', [
                                'session_id' => $this->sessionId,
                                'status' => $status
                            ]);
                            return true;
                        }
                    }
                    
                    return false;
                })
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
                $statusCode = $response->status();
                $body = $response->body();
                
                Log::error('Python service returned error', [
                    'session_id' => $this->sessionId,
                    'status' => $statusCode,
                    'body' => $body
                ]);
                
                // Provide specific error messages based on status code
                if ($statusCode === 429) {
                    throw new \Exception('Generation quota exceeded. Please try again later.');
                } elseif ($statusCode === 401 || $statusCode === 403) {
                    throw new \Exception('AI service authentication failed. Please check your API keys.');
                } elseif ($statusCode === 400) {
                    throw new \Exception('Invalid generation request: ' . $body);
                } elseif ($statusCode >= 500) {
                    throw new \Exception('AI service is temporarily unavailable. Please try again later.');
                } else {
                    throw new \Exception('Failed to connect to Python service (HTTP ' . $statusCode . '): ' . $body);
                }
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

        } catch (\Illuminate\Http\Client\ConnectionException $e) {
            Log::error('Connection error during streaming', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'url' => $pythonServiceUrl
            ]);
            throw new \Exception('Failed to connect to AI service. Please check your connection and try again.');

        } catch (\Exception $e) {
            Log::error('Streaming error', [
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
                'type' => get_class($e),
                'chunks_received' => $chunkIndex,
                'text_length' => strlen($fullText)
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
                
                // Split large chunks to avoid Reverb's message size limit
                // Split at 4KB to be extra safe (leaves room for metadata and JSON encoding overhead)
                $maxChunkSize = 4096; // 4KB in bytes - conservative to handle JSON encoding overhead
                $chunkSize = strlen($textChunk);
                
                if ($chunkSize > $maxChunkSize) {
                    Log::info('Splitting large chunk', [
                        'session_id' => $this->sessionId,
                        'original_size' => $chunkSize,
                        'max_size' => $maxChunkSize,
                        'will_split_into' => ceil($chunkSize / $maxChunkSize) . ' chunks'
                    ]);
                }
                
                $chunks = str_split($textChunk, $maxChunkSize);
                
                foreach ($chunks as $subChunk) {
                    $subChunkSize = strlen($subChunk);
                broadcast(new LLMStreamChunk(
                    $this->workspaceId,
                    $this->projectId,
                    $this->chapterOrder,
                    $this->sessionId,
                        $subChunk,
                    $chunkIndex
                ));
                
                $chunkIndex++;
                }
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
            Log::warning('Attempted to save empty generated text', [
                'session_id' => $this->sessionId,
                'chapter_order' => $this->chapterOrder
            ]);
            return;
        }

        try {
            DB::transaction(function () use ($generatedText) {
                $versionControlService = app(VersionControlService::class);
                
                // Keep the original prompt content intact (including guidance markers)
                // The guidance was already extracted and sent to the AI, but we don't remove it from the editor
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

        } catch (\Illuminate\Database\QueryException $e) {
            Log::error('Database error saving generated content', [
                'session_id' => $this->sessionId,
                'chapter_order' => $this->chapterOrder,
                'error' => $e->getMessage(),
                'code' => $e->getCode()
            ]);
            
            throw new \Exception('Failed to save generated content to database. Please try again.');

        } catch (\Exception $e) {
            Log::error('Error saving generated content', [
                'session_id' => $this->sessionId,
                'chapter_order' => $this->chapterOrder,
                'error' => $e->getMessage(),
                'type' => get_class($e)
            ]);
            
            throw new \Exception('Failed to save generated content: ' . $e->getMessage());
        }
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
        Log::error('StreamLLMJob failed permanently', [
            'session_id' => $this->sessionId,
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'error' => $exception->getMessage(),
            'type' => get_class($exception),
            'trace' => $exception->getTraceAsString(),
            'attempts' => $this->attempts(),
        ]);

        // Determine error type and provide user-friendly message
        $errorType = 'generation_failed';
        $errorMessage = 'Generation failed after multiple attempts. Please try again.';
        
        if ($exception instanceof \Illuminate\Http\Client\ConnectionException) {
            $errorType = 'connection_error';
            $errorMessage = 'Failed to connect to AI service. Please check your connection and try again.';
        } elseif ($exception instanceof \Illuminate\Http\Client\RequestException) {
            $status = $exception->response?->status();
            
            if ($status === 429) {
                $errorType = 'quota_exceeded';
                $errorMessage = 'Generation quota exceeded. Please try again later.';
            } elseif ($status === 401 || $status === 403) {
                $errorType = 'authentication_error';
                $errorMessage = 'AI service authentication failed. Please check your API keys.';
            } elseif ($status === 400) {
                $errorType = 'invalid_request';
                $errorMessage = 'Invalid generation request. Please check your settings.';
            } elseif ($status >= 500) {
                $errorType = 'service_error';
                $errorMessage = 'AI service is temporarily unavailable. Please try again later.';
            }
        } elseif (str_contains($exception->getMessage(), 'quota') || str_contains($exception->getMessage(), 'limit')) {
            $errorType = 'quota_exceeded';
            $errorMessage = 'Generation quota exceeded. Please try again later.';
        } elseif (str_contains($exception->getMessage(), 'timeout')) {
            $errorType = 'timeout_error';
            $errorMessage = 'Generation timed out. Please try again with shorter content or lower output length.';
        } elseif (str_contains($exception->getMessage(), 'memory')) {
            $errorType = 'memory_error';
            $errorMessage = 'Insufficient memory for generation. Please try with shorter content.';
        } elseif (str_contains($exception->getMessage(), 'token')) {
            $errorType = 'token_limit_error';
            $errorMessage = 'Content exceeds token limit. Please reduce the input size.';
        } elseif (str_contains($exception->getMessage(), 'database') || str_contains($exception->getMessage(), 'Database')) {
            $errorType = 'database_error';
            $errorMessage = 'Failed to save generated content. Please try again.';
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
