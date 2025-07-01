<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class LLMStreamStarted implements ShouldBroadcast
{
    use Dispatchable, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int $chapterOrder;
    public string $sessionId;

    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $sessionId
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->sessionId = $sessionId;
    }

    /**
     * Explicitly use the Reverb broadcaster.
     */
    public function broadcastConnection(): string
    {
        return 'reverb';
    }

    /**
     * Channels for broadcast.
     */
    public function broadcastOn(): array
    {
        return [
            new PrivateChannel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'llm.stream.started';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id'  => $this->workspaceId,
            'project_id'    => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'session_id'    => $this->sessionId,
            'timestamp'     => now()->toISOString(),
        ];
    }
}

