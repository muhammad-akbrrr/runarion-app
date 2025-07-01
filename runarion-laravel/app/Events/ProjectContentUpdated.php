<?php

namespace App\Events;

use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class ProjectContentUpdated implements ShouldBroadcast
{
    use Dispatchable, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int    $chapterOrder;
    public string $content;
    public string $trigger;

    public function __construct(
        string $workspaceId,
        string $projectId,
        int    $chapterOrder,
        string $content,
        string $trigger = 'manual'
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId   = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->content     = $content;
        $this->trigger     = $trigger;
    }

    /**
     * Force the use of Reverb as the broadcasting connection.
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
        return 'project.content.updated';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id'  => $this->workspaceId,
            'project_id'    => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'content'       => $this->content,
            'trigger'       => $this->trigger,
            'timestamp'     => now()->toISOString(),
        ];
    }
}

