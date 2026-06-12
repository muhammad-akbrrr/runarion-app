<?php

use App\Models\PipelineRun;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\Support\NovelPipelineTestSupport;

test('project list exposes pipeline lock props', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_1_2_RUNNING,
        'phase_1_status' => 'running',
    ]);

    $this
        ->actingAs($context['user'])
        ->get(route('workspace.projects', ['workspace_id' => $context['workspace']->id]))
        ->assertInertia(fn (Assert $page) => $page
            ->component('Projects/ProjectList')
            ->where('projects.0.id', $context['project']->id)
            ->where('projects.0.pipelineLock.runId', $run->id)
            ->where('projects.0.pipelineLock.isLocked', true));
});

test('project artifacts exposes project pipeline lock props', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_3_RUNNING,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'running',
    ]);

    $this
        ->actingAs($context['user'])
        ->get(route('workspace.artifacts', ['workspace_id' => $context['workspace']->id]))
        ->assertInertia(fn (Assert $page) => $page
            ->component('FileManager/Main')
            ->where('projects.0.id', $context['project']->id)
            ->where('projects.0.pipelineLock.runId', $run->id));
});

test('editor page exposes the current project pipeline lock prop', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();
    $run = NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PENDING,
        'phase_1_status' => 'pending',
        'phase_2_status' => 'pending',
        'phase_3_status' => 'pending',
    ]);

    $this
        ->actingAs($context['user'])
        ->get(route('workspace.projects.editor', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]))
        ->assertInertia(fn (Assert $page) => $page
            ->component('Projects/Editor/Main')
            ->where('projectPipelineLock.runId', $run->id)
            ->where('projectPipelineLock.isLocked', true));
});
