<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class AdvisorStreamCompleted implements ShouldBroadcastNow
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(
        public string $workspaceId,
        public string $projectId,
        public string $chatId,
        public string $sessionId,
        public bool $success,
        public ?string $messageId = null,
        public ?string $userMessageId = null,
        public ?string $error = null,
        public bool $cancelled = false,
    ) {}

    public function broadcastOn(): array
    {
        return [
            new Channel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'advisor.stream.completed';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chat_id' => $this->chatId,
            'session_id' => $this->sessionId,
            'success' => $this->success,
            'message_id' => $this->messageId,
            'user_message_id' => $this->userMessageId,
            'error' => $this->error,
            'cancelled' => $this->cancelled,
            'timestamp' => now()->toISOString(),
        ];
    }
}
