<?php

namespace App\Http\Controllers\ProjectEditor;

use App\Http\Controllers\Controller;
use App\Models\AdvisorChat;
use App\Models\AdvisorMessage;
use App\Models\Projects;
use App\Models\ProjectContent;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\StreamedResponse;

class AdvisorController extends Controller
{
    /**
     * List all chats for a project, ordered by most recent.
     */
    public function listChats(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $chats = AdvisorChat::where('project_id', $project_id)
                ->orderBy('updated_at', 'desc')
                ->get()
                ->map(function ($chat) {
                    return [
                        'id' => $chat->id,
                        'title' => $chat->title,
                        'model' => $chat->model,
                        'system_instructions' => $chat->system_instructions,
                        'message_count' => $chat->messages()->count(),
                        'created_at' => $chat->created_at->toISOString(),
                        'updated_at' => $chat->updated_at->toISOString(),
                    ];
                });

            return response()->json([
                'success' => true,
                'chats' => $chats,
            ]);
        } catch (\Exception $e) {
            Log::error('Error listing advisor chats', [
                'error' => $e->getMessage(),
                'project_id' => $project_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to list chats',
            ], 500);
        }
    }

    /**
     * Create a new chat.
     */
    public function createChat(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'title' => 'nullable|string|max:255',
                'system_instructions' => 'nullable|string|max:10000',
                'model' => 'nullable|string|max:100',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $chat = AdvisorChat::create([
                'project_id' => $project_id,
                'title' => $validated['title'] ?? 'New Chat',
                'system_instructions' => $validated['system_instructions'] ?? null,
                'model' => $validated['model'] ?? 'gemini-2.5-flash',
            ]);

            return response()->json([
                'success' => true,
                'chat' => [
                    'id' => $chat->id,
                    'title' => $chat->title,
                    'model' => $chat->model,
                    'system_instructions' => $chat->system_instructions,
                    'message_count' => 0,
                    'created_at' => $chat->created_at->toISOString(),
                    'updated_at' => $chat->updated_at->toISOString(),
                ],
            ]);
        } catch (\Exception $e) {
            Log::error('Error creating advisor chat', [
                'error' => $e->getMessage(),
                'project_id' => $project_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to create chat',
            ], 500);
        }
    }

    /**
     * Update a chat (title, system instructions, model).
     */
    public function updateChat(Request $request, string $workspace_id, string $project_id, string $chat_id)
    {
        try {
            $validated = $request->validate([
                'title' => 'nullable|string|max:255',
                'system_instructions' => 'nullable|string|max:10000',
                'model' => 'nullable|string|max:100',
            ]);

            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            $chat->update(array_filter($validated, fn($v) => $v !== null));

            return response()->json([
                'success' => true,
                'chat' => [
                    'id' => $chat->id,
                    'title' => $chat->title,
                    'model' => $chat->model,
                    'system_instructions' => $chat->system_instructions,
                    'message_count' => $chat->messages()->count(),
                    'created_at' => $chat->created_at->toISOString(),
                    'updated_at' => $chat->updated_at->toISOString(),
                ],
            ]);
        } catch (\Exception $e) {
            Log::error('Error updating advisor chat', [
                'error' => $e->getMessage(),
                'chat_id' => $chat_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to update chat',
            ], 500);
        }
    }

    /**
     * Delete a chat and all its messages.
     */
    public function deleteChat(Request $request, string $workspace_id, string $project_id, string $chat_id)
    {
        try {
            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            $chat->delete();

            return response()->json([
                'success' => true,
            ]);
        } catch (\Exception $e) {
            Log::error('Error deleting advisor chat', [
                'error' => $e->getMessage(),
                'chat_id' => $chat_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to delete chat',
            ], 500);
        }
    }

    /**
     * Delete a single message.
     */
    public function deleteMessage(Request $request, string $workspace_id, string $project_id, string $chat_id, string $message_id)
    {
        try {
            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            // Delete the specific message
            $deleted = AdvisorMessage::where('id', $message_id)
                ->where('chat_id', $chat_id)
                ->delete();

            return response()->json([
                'success' => $deleted > 0,
            ]);
        } catch (\Exception $e) {
            Log::error('Error deleting advisor message', [
                'error' => $e->getMessage(),
                'message_id' => $message_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to delete message',
            ], 500);
        }
    }

    /**
     * Clear all messages in a chat.
     */
    public function clearMessages(Request $request, string $workspace_id, string $project_id, string $chat_id)
    {
        try {
            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            // Delete all messages in this chat
            $chat->messages()->delete();

            return response()->json([
                'success' => true,
            ]);
        } catch (\Exception $e) {
            Log::error('Error clearing advisor messages', [
                'error' => $e->getMessage(),
                'chat_id' => $chat_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to clear messages',
            ], 500);
        }
    }

    /**
     * Get all messages for a chat.
     */
    public function getMessages(Request $request, string $workspace_id, string $project_id, string $chat_id)
    {
        try {
            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            $messages = $chat->messages()
                ->orderBy('created_at', 'asc')
                ->get()
                ->map(function ($msg) {
                    return [
                        'id' => $msg->id,
                        'role' => $msg->role,
                        'content' => $msg->content,
                        'metadata' => $msg->metadata,
                        'created_at' => $msg->created_at->toISOString(),
                    ];
                });

            return response()->json([
                'success' => true,
                'messages' => $messages,
                'chat' => [
                    'id' => $chat->id,
                    'title' => $chat->title,
                    'model' => $chat->model,
                    'system_instructions' => $chat->system_instructions,
                ],
            ]);
        } catch (\Exception $e) {
            Log::error('Error getting advisor messages', [
                'error' => $e->getMessage(),
                'chat_id' => $chat_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to get messages',
            ], 500);
        }
    }

    /**
     * Send a message and get a streaming AI response.
     * This includes full story context for the AI.
     */
    public function sendMessage(Request $request, string $workspace_id, string $project_id, string $chat_id)
    {
        try {
            $validated = $request->validate([
                'message' => 'required|string|max:50000',
                'include_story_context' => 'nullable|boolean',
                'is_retry' => 'nullable|boolean',
                'model' => 'nullable|string',
                'thinking_budget' => 'nullable|integer',
                'max_output_tokens' => 'nullable|integer',
                'temperature' => 'nullable|numeric',
            ]);

            $chat = AdvisorChat::where('id', $chat_id)
                ->whereHas('project', function ($q) use ($workspace_id) {
                    $q->where('workspace_id', $workspace_id);
                })
                ->firstOrFail();

            // Only save user message if this is NOT a retry
            // On retry, the message already exists in the database
            $isRetry = $validated['is_retry'] ?? false;
            $userMessageId = null;
            if (!$isRetry) {
                $userMessage = AdvisorMessage::create([
                    'chat_id' => $chat_id,
                    'role' => 'user',
                    'content' => $validated['message'],
                ]);
                $userMessageId = $userMessage->id;
            }

            // Update chat's updated_at
            $chat->touch();

            // Get story context if requested (default: true)
            $includeContext = $validated['include_story_context'] ?? true;
            $storyContext = '';
            
            if ($includeContext) {
                $storyContext = $this->getStoryContextText($project_id);
            }

            // Build conversation history for context
            $conversationHistory = $chat->messages()
                ->orderBy('created_at', 'asc')
                ->get()
                ->map(function ($msg) {
                    return [
                        'role' => $msg->role,
                        'content' => $msg->content,
                    ];
                })
                ->toArray();

            // Generation settings from request (with defaults from chat)
            $generationSettings = [
                'model' => $validated['model'] ?? $chat->model ?? 'gemini-2.5-flash',
                'thinking_budget' => $validated['thinking_budget'] ?? 4096,
                'max_output_tokens' => $validated['max_output_tokens'] ?? 4000,  // Increased for more detailed responses
                'temperature' => $validated['temperature'] ?? 0.8,
            ];

            // Call Python API for streaming response
            return $this->streamAIResponse(
                $chat,
                $storyContext,
                $conversationHistory,
                $project_id,
                $generationSettings,
                $userMessageId
            );

        } catch (\Exception $e) {
            Log::error('Error sending advisor message', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
                'chat_id' => $chat_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to send message: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get the full story context for the AI.
     */
    public function getStoryContext(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            $storyContext = $this->getStoryContextText($project_id);
            $tokenEstimate = $this->estimateTokens($storyContext);

            return response()->json([
                'success' => true,
                'context' => $storyContext,
                'token_estimate' => $tokenEstimate,
                'project_name' => $project->name,
            ]);
        } catch (\Exception $e) {
            Log::error('Error getting story context', [
                'error' => $e->getMessage(),
                'project_id' => $project_id,
            ]);

            return response()->json([
                'success' => false,
                'error' => 'Failed to get story context',
            ], 500);
        }
    }

    /**
     * Build the full story context text from all chapters.
     */
    private function getStoryContextText(string $project_id): string
    {
        $projectContent = ProjectContent::where('project_id', $project_id)->first();
        
        if (!$projectContent || !$projectContent->content) {
            return '';
        }

        $chapters = $projectContent->content;
        if (!is_array($chapters)) {
            return '';
        }

        // Sort chapters by order to ensure correct sequence
        usort($chapters, function ($a, $b) {
            return ($a['order'] ?? 0) - ($b['order'] ?? 0);
        });

        $contextParts = [];
        $project = Projects::find($project_id);
        
        if ($project) {
            $contextParts[] = "# Story: {$project->name}";
            $contextParts[] = "";
        }

        $totalChapters = count($chapters);
        $contextParts[] = "**IMPORTANT**: This story has {$totalChapters} chapter(s), numbered from Chapter 1 to Chapter {$totalChapters}.";
        $contextParts[] = "There is NO Chapter 0. Always reference chapters by their correct number (1, 2, 3, etc.) or by their name.\n";

        foreach ($chapters as $chapter) {
            // Use chapter_name if available, otherwise use 1-indexed chapter number
            // (order is 0-indexed internally, but users see 1-indexed chapters)
            $chapterOrder = ($chapter['order'] ?? 0) + 1;
            $chapterName = !empty($chapter['chapter_name']) 
                ? $chapter['chapter_name'] 
                : "Chapter {$chapterOrder}";
            $chapterContent = $chapter['content'] ?? '';
            
            if (!empty($chapterContent)) {
                $contextParts[] = "## {$chapterName}";
                $contextParts[] = "";
                $contextParts[] = $chapterContent;
                $contextParts[] = "";
                $contextParts[] = "---";
                $contextParts[] = "";
            } else {
                // Still include empty chapters so AI knows they exist
                $contextParts[] = "## {$chapterName}";
                $contextParts[] = "";
                $contextParts[] = "[This chapter is currently empty]";
                $contextParts[] = "";
                $contextParts[] = "---";
                $contextParts[] = "";
            }
        }

        return implode("\n", $contextParts);
    }

    /**
     * Estimate token count for text (rough approximation: 4 chars per token).
     */
    private function estimateTokens(string $text): int
    {
        return (int) ceil(strlen($text) / 4);
    }

    /**
     * Stream AI response from Python service using cURL for true streaming.
     */
    private function streamAIResponse(
        AdvisorChat $chat,
        string $storyContext,
        array $conversationHistory,
        string $project_id,
        array $generationSettings = [],
        ?string $userMessageId = null
    ): StreamedResponse {
        return response()->stream(function () use ($chat, $storyContext, $conversationHistory, $project_id, $generationSettings, $userMessageId) {
            $pythonApiUrl = env('PYTHON_SERVICE_URL', 'http://python-app:5000');
            $fullResponse = '';
            $lineBuffer = ''; // Buffer for incomplete SSE lines

            try {
                // Build the request payload with generation settings
                $payload = [
                    'model' => $generationSettings['model'] ?? $chat->model,
                    'system_instructions' => $chat->system_instructions ?? $this->getDefaultSystemInstructions(),
                    'story_context' => $storyContext,
                    'conversation_history' => $conversationHistory,
                    'project_id' => $project_id,
                    'stream' => true,
                    // Generation settings
                    'thinking_budget' => $generationSettings['thinking_budget'] ?? 4096,
                    'max_output_tokens' => $generationSettings['max_output_tokens'] ?? 4000,
                    'temperature' => $generationSettings['temperature'] ?? 0.8,
                ];

                Log::info('Advisor streaming request', [
                    'chat_id' => $chat->id,
                    'model' => $payload['model'],
                    'story_context_length' => strlen($storyContext),
                    'history_count' => count($conversationHistory),
                    'thinking_budget' => $payload['thinking_budget'],
                    'max_output_tokens' => $payload['max_output_tokens'],
                    'temperature' => $payload['temperature'],
                ]);

                // Use cURL for TRUE streaming (not buffered like Http::withOptions)
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
                    CURLOPT_WRITEFUNCTION => function ($ch, $data) use (&$fullResponse, &$lineBuffer) {
                        // Append new data to buffer
                        $lineBuffer .= $data;
                        
                        // Process complete lines only (SSE lines end with \n\n)
                        while (($pos = strpos($lineBuffer, "\n")) !== false) {
                            $line = substr($lineBuffer, 0, $pos);
                            $lineBuffer = substr($lineBuffer, $pos + 1);
                            
                            $line = trim($line);
                            if (empty($line)) continue;
                            
                            if (strpos($line, 'data: ') === 0) {
                                $eventData = substr($line, 6);
                                
                                if ($eventData === '[DONE]') {
                                    continue;
                                }

                                $decoded = json_decode($eventData, true);
                                if ($decoded && isset($decoded['chunk'])) {
                                    $fullResponse .= $decoded['chunk'];
                                    
                                    // Forward the chunk to the client immediately
                                    echo "data: " . json_encode([
                                        'chunk' => $decoded['chunk'],
                                        'type' => 'content',
                                    ]) . "\n\n";
                                    if (ob_get_level() > 0) {
                                        ob_flush();
                                    }
                                    flush();
                                } elseif ($decoded && isset($decoded['error'])) {
                                    Log::error('Advisor stream error from Python', ['error' => $decoded['error']]);
                                    echo "data: " . json_encode(['error' => $decoded['error']]) . "\n\n";
                                    if (ob_get_level() > 0) {
                                        ob_flush();
                                    }
                                    flush();
                                }
                            }
                        }
                        return strlen($data);
                    },
                ]);

                $result = curl_exec($ch);
                $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                $curlError = curl_error($ch);
                curl_close($ch);

                // Process any remaining buffered content
                if (!empty($lineBuffer)) {
                    $line = trim($lineBuffer);
                    if (strpos($line, 'data: ') === 0) {
                        $eventData = substr($line, 6);
                        if ($eventData !== '[DONE]') {
                            $decoded = json_decode($eventData, true);
                            if ($decoded && isset($decoded['chunk'])) {
                                $fullResponse .= $decoded['chunk'];
                                echo "data: " . json_encode([
                                    'chunk' => $decoded['chunk'],
                                    'type' => 'content',
                                ]) . "\n\n";
                                if (ob_get_level() > 0) {
                                    ob_flush();
                                }
                                flush();
                            }
                        }
                    }
                }

                if ($httpCode !== 200 || $result === false) {
                    $error = $curlError ?: "API error: HTTP {$httpCode}";
                    Log::error('Advisor API error', ['error' => $error, 'http_code' => $httpCode]);
                    echo "data: " . json_encode(['error' => $error]) . "\n\n";
                    if (ob_get_level() > 0) {
                        ob_flush();
                    }
                    flush();
                    return;
                }

                Log::info('Advisor stream completed', [
                    'chat_id' => $chat->id,
                    'full_response_length' => strlen($fullResponse),
                    'http_code' => $httpCode,
                ]);

                // Save the assistant's response AFTER streaming completes
                $assistantMessageId = null;
                if (!empty($fullResponse)) {
                    try {
                        $assistantMessage = AdvisorMessage::create([
                            'chat_id' => $chat->id,
                            'role' => 'assistant',
                            'content' => $fullResponse,
                            'metadata' => [
                                'model' => $generationSettings['model'] ?? $chat->model,
                                'story_context_tokens' => $this->estimateTokens($storyContext),
                            ],
                        ]);
                        $assistantMessageId = $assistantMessage->id;

                        // Auto-generate title from first message if still default
                        if ($chat->title === 'New Chat' && $chat->messages()->count() <= 2) {
                            $this->autoGenerateTitle($chat);
                        }
                        
                        Log::info('Advisor response saved successfully', [
                            'chat_id' => $chat->id,
                            'message_id' => $assistantMessageId,
                            'response_length' => strlen($fullResponse),
                        ]);
                    } catch (\Exception $saveError) {
                        Log::error('Failed to save advisor response', [
                            'chat_id' => $chat->id,
                            'error' => $saveError->getMessage(),
                            'response_length' => strlen($fullResponse),
                        ]);
                    }
                } else {
                    Log::warning('Advisor stream completed but fullResponse is empty', [
                        'chat_id' => $chat->id,
                    ]);
                }

                // Send completion signal with both message IDs
                echo "data: " . json_encode([
                    'type' => 'done',
                    'message_id' => $assistantMessageId,
                    'user_message_id' => $userMessageId,
                    'response_length' => strlen($fullResponse),
                ]) . "\n\n";
                if (ob_get_level() > 0) {
                    ob_flush();
                }
                flush();

            } catch (\Exception $e) {
                Log::error('Error in advisor stream', [
                    'error' => $e->getMessage(),
                    'trace' => $e->getTraceAsString(),
                    'chat_id' => $chat->id,
                ]);

                echo "data: " . json_encode(['error' => $e->getMessage()]) . "\n\n";
                if (ob_get_level() > 0) {
                    ob_flush();
                }
                flush();
            }
        }, 200, [
            'Content-Type' => 'text/event-stream',
            'Cache-Control' => 'no-cache',
            'Connection' => 'keep-alive',
            'X-Accel-Buffering' => 'no',
        ]);
    }

    /**
     * Auto-generate a chat title based on the first user message.
     */
    private function autoGenerateTitle(AdvisorChat $chat): void
    {
        $firstMessage = $chat->messages()
            ->where('role', 'user')
            ->orderBy('created_at', 'asc')
            ->first();

        if ($firstMessage) {
            // Take first 50 chars of the message as title
            $title = substr($firstMessage->content, 0, 50);
            if (strlen($firstMessage->content) > 50) {
                $title .= '...';
            }
            $chat->update(['title' => $title]);
        }
    }

    /**
     * Get default system instructions for the advisor.
     */
    private function getDefaultSystemInstructions(): string
    {
        return <<<EOT
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

