<?php

use App\Models\PipelineRun;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Tests\Support\NovelPipelineTestSupport;

beforeEach(function () {
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('locked project mutations return 423 for json requests', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();

    NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_1_2_RUNNING,
        'phase_1_status' => 'running',
        'phase_2_status' => 'pending',
        'phase_3_status' => 'pending',
    ]);

    $response = $this
        ->actingAs($context['user'])
        ->patchJson(route('editor.project.updateName', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'name' => 'Blocked Rename',
        ]);

    $response
        ->assertStatus(423)
        ->assertJsonPath('message', 'This project is locked by an active operation. Please wait for it to finish before making changes.')
        ->assertJsonPath('lock.isLocked', true);
});

test('locked project mutations redirect back with errors for form requests', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();

    NovelPipelineTestSupport::createPipelineRun([
        'workspace_id' => $context['workspace']->id,
        'project_id' => $context['project']->id,
        'user_id' => $context['user']->id,
        'status' => PipelineRun::STATUS_PHASE_3_RUNNING,
        'phase_1_status' => 'completed',
        'phase_2_status' => 'completed',
        'phase_3_status' => 'running',
    ]);

    $response = $this
        ->from('/editor')
        ->actingAs($context['user'])
        ->patch(route('editor.project.updateName', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'name' => 'Blocked Rename',
        ]);

    $response
        ->assertRedirect('/editor')
        ->assertSessionHasErrors('project_lock');
});
