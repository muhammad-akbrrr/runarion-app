<?php

namespace App\Events;

use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class LLMStreamCompleted implements ShouldBroadcast
{
    use Dispatchable, SerializesModels;

    public string $workspaceId;
    public string $projectId;
    public int    $chapterOrder;
    public string $sessionId;
    public string $fullText;
    public bool   $success;
    public ?string $error;

    public function __construct(
        string $workspaceId,
        string $projectId,
        int    $chapterOrder,
        string $sessionId,
        string $fullText,
        bool   $success,
        ?string $error = null
    ) {
        $this->workspaceId = $workspaceId;
        $this->projectId   = $projectId;
        $this->chapterOrder = $chapterOrder;
        $this->sessionId   = $sessionId;
        $this->fullText    = $fullText;
        $this->success     = $success;
        $this->error       = $error;
    }

    /**
     * Force the Reverb streamer connection.
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
        return 'llm.stream.completed';
    }

    public function broadcastWith(): array
    {
        return [
            'workspace_id'  => $this->workspaceId,
            'project_id'    => $this->projectId,
            'chapter_order' => $this->chapterOrder,
            'session_id'    => $this->sessionId,
            'full_text'     => $this->fullText,
            'success'       => $this->success,
            'error'         => $this->error,
            'timestamp'     => now()->toISOString(),
        ];
    }
}

