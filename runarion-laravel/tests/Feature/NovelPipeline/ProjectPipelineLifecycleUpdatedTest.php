<?php

use App\Events\ProjectPipelineLifecycleUpdated;

test('pipeline lifecycle event exposes toast metadata in its broadcast payload', function () {
    $event = new ProjectPipelineLifecycleUpdated(
        'workspace-1',
        'project-1',
        'run-1',
        'phase_1_2_running',
        'deconstructor',
        true,
        'Still working.',
        false,
    );

    expect($event->broadcastAs())->toBe('project.pipeline.lifecycle.updated');
    expect($event->broadcastWith())->toMatchArray([
        'workspace_id' => 'workspace-1',
        'project_id' => 'project-1',
        'run_id' => 'run-1',
        'status' => 'phase_1_2_running',
        'phase' => 'deconstructor',
        'is_locked' => true,
        'message' => 'Still working.',
        'should_toast' => false,
    ]);
});
