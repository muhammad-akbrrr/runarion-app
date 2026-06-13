<?php

use App\Models\ProjectOperation;
use App\Services\ProjectOperationStateService;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Tests\Support\NovelPipelineTestSupport;

beforeEach(function () {
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('snapshot restore operation lock blocks project mutations', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();

    app(ProjectOperationStateService::class)->createRestoreOperation(
        $context['workspace']->id,
        $context['project']->id,
        'snapshot-test-id',
        $context['user']->id,
    );

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
        ->assertJsonPath('lock.operationType', ProjectOperation::TYPE_SNAPSHOT_RESTORE)
        ->assertJsonPath('lock.isLocked', true);
});
