<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PresenceChannel;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class LLMStreamCompleted implements ShouldBroadcastNow
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int $chapterOrder;
    public string $sessionId;
    public string $fullText;
    public bool $success;
    public ?string $error;
    public ?string $errorType;

    /**
     * Create a new event instance.
     */
    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $sessionId,
        string $fullText,
        bool $success,
        ?string $error = null,
        ?string $errorType = null
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->sessionId = $sessionId;
        $this->fullText = $fullText;
        $this->success = $success;
        $this->error = $error;
        $this->errorType = $errorType;
    }

    /**
     * Get the channels the event should broadcast on.
     *
     * @return array<int, \Illuminate\Broadcasting\Channel>
     */
    public function broadcastOn(): array
    {
        return [
            new Channel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    /**
     * The event's broadcast name.
     */
    public function broadcastAs(): string
    {
        return 'llm.stream.completed';
    }

    /**
     * Get the data to broadcast.
     */
    public function broadcastWith(): array
    {
        // Don't send full_text in completion event - frontend already has it from chunks
        // This prevents "payload too large" errors for long generations (>10KB Pusher limit)
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'session_id' => $this->sessionId,
            'full_text' => '', // Empty - frontend already has full text from streamed chunks
            'success' => $this->success,
            'error' => $this->error,
            'error_type' => $this->errorType,
            'timestamp' => now()->toISOString(),
        ];
    }
}
