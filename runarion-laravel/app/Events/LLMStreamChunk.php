<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PresenceChannel;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class LLMStreamChunk implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int $chapterOrder;
    public string $sessionId;
    public string $chunk;
    public int $chunkIndex;

    /**
     * Create a new event instance.
     */
    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $sessionId,
        string $chunk,
        int $chunkIndex
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->sessionId = $sessionId;
        $this->chunk = $chunk;
        $this->chunkIndex = $chunkIndex;
    }

    /**
     * Get the channels the event should broadcast on.
     *
     * @return array<int, \Illuminate\Broadcasting\Channel>
     */
    public function broadcastOn(): array
    {
        return [
            new PrivateChannel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    /**
     * The event's broadcast name.
     */
    public function broadcastAs(): string
    {
        return 'llm.stream.chunk';
    }

    /**
     * Get the data to broadcast.
     */
    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'session_id' => $this->sessionId,
            'chunk' => $this->chunk,
            'chunk_index' => $this->chunkIndex,
            'timestamp' => now()->toISOString(),
        ];
    }
}
