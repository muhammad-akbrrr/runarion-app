<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class AdvisorStreamChunk implements ShouldBroadcastNow
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(
        public string $workspaceId,
        public string $projectId,
        public string $chatId,
        public string $sessionId,
        public string $chunk,
        public int $chunkIndex,
    ) {}

    public function broadcastOn(): array
    {
        return [
            new Channel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'advisor.stream.chunk';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chat_id' => $this->chatId,
            'session_id' => $this->sessionId,
            'chunk' => $this->chunk,
            'chunk_index' => $this->chunkIndex,
            'timestamp' => now()->toISOString(),
        ];
    }
}
