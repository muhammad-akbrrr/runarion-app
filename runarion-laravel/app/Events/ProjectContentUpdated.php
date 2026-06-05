<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class ProjectContentUpdated implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    public string $workspaceId;

    public string $projectId;

    public int $chapterOrder;

    public string $content;

    public string $trigger;

    public ?int $versionIndex;

    public ?array $navigationInfo;

    /**
     * Create a new event instance.
     */
    public function __construct(
        string $workspaceId,
        string $projectId,
        int $chapterOrder,
        ?string $content,
        string $trigger = 'manual',
        ?int $versionIndex = null,
        ?array $navigationInfo = null
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->content = $content ?? '';
        $this->trigger = $trigger;
        $this->versionIndex = $versionIndex;
        $this->navigationInfo = $navigationInfo;
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
        return 'project.content.updated';
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
            'content' => $this->content,
            'trigger' => $this->trigger,
            'version_index' => $this->versionIndex,
            'navigation_info' => $this->navigationInfo,
            'timestamp' => now()->toISOString(),
        ];
    }
}
