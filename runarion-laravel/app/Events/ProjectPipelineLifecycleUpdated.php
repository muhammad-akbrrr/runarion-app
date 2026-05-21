<?php

namespace App\Events;

use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class ProjectPipelineLifecycleUpdated implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public function __construct(
        public readonly string $workspaceId,
        public readonly string $projectId,
        public readonly string $runId,
        public readonly string $status,
        public readonly string $phase,
        public readonly bool $isLocked,
        public readonly string $message,
        public readonly bool $shouldToast = true,
    ) {
    }

    public function broadcastOn(): array
    {
        return [
            new PrivateChannel("workspace.{$this->workspaceId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'project.pipeline.lifecycle.updated';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'run_id' => $this->runId,
            'status' => $this->status,
            'phase' => $this->phase,
            'is_locked' => $this->isLocked,
            'message' => $this->message,
            'should_toast' => $this->shouldToast,
            'timestamp' => now()->toISOString(),
        ];
    }
}
