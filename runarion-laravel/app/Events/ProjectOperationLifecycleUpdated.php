<?php

namespace App\Events;

use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class ProjectOperationLifecycleUpdated implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(
        public string $workspaceId,
        public string $projectId,
        public string $operationId,
        public string $operationType,
        public string $status,
        public string $phase,
        public bool $isLocked,
        public ?string $message = null,
        public bool $shouldToast = true,
    ) {}

    public function broadcastOn(): array
    {
        return [
            new PrivateChannel("workspace.{$this->workspaceId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'project.operation.lifecycle.updated';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'operation_id' => $this->operationId,
            'operation_type' => $this->operationType,
            'status' => $this->status,
            'phase' => $this->phase,
            'is_locked' => $this->isLocked,
            'message' => $this->message,
            'should_toast' => $this->shouldToast,
            'timestamp' => now()->toISOString(),
        ];
    }
}
