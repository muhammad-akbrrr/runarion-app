<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class OperationStateChanged implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public string $workspaceId;

    public string $projectId;

    public int $chapterOrder;

    public string $operation;

    public bool $isLocked;

    public array $navigationInfo;

    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        string $operation,
        bool $isLocked,
        array $navigationInfo = []
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->operation = $operation;
        $this->isLocked = $isLocked;
        $this->navigationInfo = $navigationInfo;
    }

    public function broadcastOn(): array
    {
        return [
            new Channel("project.{$this->workspaceId}.{$this->projectId}"),
        ];
    }

    public function broadcastAs(): string
    {
        return 'operation.state.changed';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id' => $this->workspaceId,
            'project_id' => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'operation' => $this->operation,
            'is_locked' => $this->isLocked,
            'navigation_info' => $this->navigationInfo,
            'timestamp' => now()->toISOString(),
        ];
    }
}
