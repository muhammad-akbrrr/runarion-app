<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class LLMStreamChunk implements ShouldBroadcast
{
    use Dispatchable, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int    $chapterOrder;
    public string $sessionId;
    public string $chunk;
    public int    $chunkIndex;

    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $sessionId,
        string $chunk,
        int $chunkIndex
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId   = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->sessionId   = $sessionId;
        $this->chunk       = $chunk;
        $this->chunkIndex  = $chunkIndex;
    }

    /**
     * Force the Reverb broadcaster connection.
     */
    public function broadcastConnection(): string
    {
        return 'reverb';
    }

    public function broadcastOn(): array
    {
        return [
            new PrivateChannel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'llm.stream.chunk';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id'  => $this->workspaceId,
            'project_id'    => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'session_id'    => $this->sessionId,
            'chunk'         => $this->chunk,
            'chunk_index'   => $this->chunkIndex,
            'timestamp'     => now()->toISOString(),
        ];
    }
}
