<?php

namespace App\Jobs;

use App\Events\AdvisorStreamChunk;
use App\Events\AdvisorStreamCompleted;
use App\Events\AdvisorStreamStarted;
use App\Models\AdvisorChat;
use App\Models\AdvisorMessage;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class AdvisorStreamJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $timeout = 300;

    public int $tries = 1;

    public function __construct(
        public string $workspaceId,
        public string $projectId,
        public string $chatId,
        public string $sessionId,
        public string $storyContext,
        public array $conversationHistory,
        public array $generationSettings,
        public ?string $userMessageId = null,
    ) {}

    public static function cancellationCacheKey(string $sessionId): string
    {
        return "advisor-stream-cancelled:{$sessionId}";
    }

    public function handle(): void
    {
        $chat = AdvisorChat::findOrFail($this->chatId);

        broadcast(new AdvisorStreamStarted(
            $this->workspaceId,
            $this->projectId,
            $this->chatId,
            $this->sessionId,
            $this->userMessageId,
        ));

        $pythonApiUrl = env('PYTHON_SERVICE_URL', 'http://python-app:5000');
        $fullResponse = '';
        $chunkIndex = 0;
        $cancelled = false;

        try {
            $payload = [
                'model' => $this->generationSettings['model'] ?? $chat->model ?? 'gemini-2.5-flash',
                'system_instructions' => $chat->system_instructions ?? $this->getDefaultSystemInstructions(),
                'story_context' => $this->storyContext,
                'conversation_history' => $this->conversationHistory,
                'project_id' => $this->projectId,
                'stream' => true,
                'thinking_budget' => $this->generationSettings['thinking_budget'] ?? 4096,
                'max_output_tokens' => $this->generationSettings['max_output_tokens'] ?? 4000,
                'temperature' => $this->generationSettings['temperature'] ?? 0.8,
                'caller' => [
                    'user_id' => (string) $chat->user_id,
                    'workspace_id' => $this->workspaceId,
                    'project_id' => $this->projectId,
                    'session_id' => $this->sessionId,
                    'api_keys' => [],
                ],
                'quota_context' => [
                    'mode' => 'strict',
                    'workflow_id' => $this->sessionId,
                    'workflow_kind' => 'advisor_chat',
                ],
            ];

            Log::info('Advisor stream started', [
                'chat_id' => $this->chatId,
                'session_id' => $this->sessionId,
                'model' => $payload['model'],
            ]);

            $lineBuffer = '';
            $ch = curl_init("{$pythonApiUrl}/api/advisor/chat");
            curl_setopt_array($ch, [
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => json_encode($payload),
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Accept: text/event-stream',
                ],
                CURLOPT_RETURNTRANSFER => false,
                CURLOPT_TIMEOUT => 300,
                CURLOPT_WRITEFUNCTION => function ($ch, $data) use (&$fullResponse, &$lineBuffer, &$chunkIndex, &$cancelled) {
                    if ($this->isCancelled()) {
                        $cancelled = true;

                        return 0;
                    }

                    $lineBuffer .= $data;

                    while (($pos = strpos($lineBuffer, "\n")) !== false) {
                        $line = trim(substr($lineBuffer, 0, $pos));
                        $lineBuffer = substr($lineBuffer, $pos + 1);

                        if ($line === '' || ! str_starts_with($line, 'data: ')) {
                            continue;
                        }

                        $eventData = substr($line, 6);
                        if ($eventData === '[DONE]') {
                            continue;
                        }

                        $decoded = json_decode($eventData, true);
                        if (! is_array($decoded)) {
                            continue;
                        }

                        if (isset($decoded['error'])) {
                            throw new \RuntimeException((string) $decoded['error']);
                        }

                        if (! isset($decoded['chunk'])) {
                            continue;
                        }

                        $chunk = (string) $decoded['chunk'];
                        $fullResponse .= $chunk;

                        broadcast(new AdvisorStreamChunk(
                            $this->workspaceId,
                            $this->projectId,
                            $this->chatId,
                            $this->sessionId,
                            $chunk,
                            $chunkIndex++,
                        ));
                    }

                    return strlen($data);
                },
            ]);

            $result = curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $curlError = curl_error($ch);
            curl_close($ch);

            if ($cancelled || $this->isCancelled()) {
                Log::info('Advisor stream cancelled', [
                    'chat_id' => $this->chatId,
                    'session_id' => $this->sessionId,
                ]);

                return;
            }

            if ($result === false || $httpCode !== 200) {
                throw new \RuntimeException($curlError ?: "Advisor API error: HTTP {$httpCode}");
            }

            $assistantMessageId = null;
            if ($fullResponse !== '') {
                $assistantMessage = AdvisorMessage::create([
                    'chat_id' => $this->chatId,
                    'role' => 'assistant',
                    'content' => $fullResponse,
                    'metadata' => [
                        'model' => $payload['model'],
                        'story_context_tokens' => $this->estimateTokens($this->storyContext),
                    ],
                ]);
                $assistantMessageId = $assistantMessage->id;

                if ($chat->title === 'New Chat' && $chat->messages()->count() <= 2) {
                    $this->autoGenerateTitle($chat);
                }
            }

            broadcast(new AdvisorStreamCompleted(
                $this->workspaceId,
                $this->projectId,
                $this->chatId,
                $this->sessionId,
                true,
                $assistantMessageId,
                $this->userMessageId,
            ));
        } catch (\Throwable $e) {
            Log::error('Advisor stream failed', [
                'chat_id' => $this->chatId,
                'session_id' => $this->sessionId,
                'error' => $e->getMessage(),
            ]);

            if ($this->isCancelled()) {
                return;
            }

            broadcast(new AdvisorStreamCompleted(
                $this->workspaceId,
                $this->projectId,
                $this->chatId,
                $this->sessionId,
                false,
                null,
                $this->userMessageId,
                $e->getMessage(),
            ));
        } finally {
            Cache::forget(self::cancellationCacheKey($this->sessionId));
        }
    }

    private function isCancelled(): bool
    {
        return Cache::get(self::cancellationCacheKey($this->sessionId), false) === true;
    }

    private function autoGenerateTitle(AdvisorChat $chat): void
    {
        $firstMessage = $chat->messages()
            ->where('role', 'user')
            ->orderBy('created_at', 'asc')
            ->first();

        if (! $firstMessage) {
            return;
        }

        $title = Str::limit($firstMessage->content, 50, '...');
        $chat->update(['title' => $title]);
    }

    private function estimateTokens(string $text): int
    {
        return (int) ceil(strlen($text) / 4);
    }

    private function getDefaultSystemInstructions(): string
    {
        return <<<'EOT'
You are an expert writing advisor and creative assistant. You have access to the full story context and can help with:

1. **Story Analysis**: Analyze plot, characters, pacing, themes, and narrative structure
2. **Writing Suggestions**: Offer improvements for dialogue, descriptions, and prose style
3. **Continuity Checking**: Identify inconsistencies in the story
4. **Brainstorming**: Help develop ideas, plot points, and character arcs
5. **Editing**: Suggest specific text changes when asked

When suggesting edits to the text, use this format:
<<<EDIT>>>
CHAPTER: [chapter name or number - chapters are numbered starting from 1, NOT 0]
LOCATION: [brief description of where in the text]
OLD: [exact text to replace]
NEW: [suggested replacement text]
REASON: [why this change improves the story]
<<<END_EDIT>>>

IMPORTANT RULES:
- Always provide thorough, detailed responses. When analyzing story content, quote relevant passages and provide comprehensive analysis.
- Do not give overly brief answers - be helpful and expansive in your responses.
- Reference specific parts of the story when relevant.
- Chapters are numbered starting from 1 (Chapter 1, Chapter 2, etc.). There is NO Chapter 0.
- When referencing chapters, use the chapter name if available, or "Chapter N" where N starts at 1.
EOT;
    }
}
