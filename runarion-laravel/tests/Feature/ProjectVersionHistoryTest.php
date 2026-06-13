<?php

use App\Models\AdvisorChat;
use App\Models\AdvisorMessage;
use App\Models\ProjectNodeEditor;
use App\Models\ProjectOperation;
use App\Models\ProjectSnapshot;
use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use App\Jobs\RestoreProjectSnapshotJob;
use App\Services\ProjectOperationStateService;
use App\Services\ProjectSnapshotService;
use Illuminate\Foundation\Http\Middleware\ValidateCsrfToken;
use Illuminate\Support\Facades\Bus;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\Support\NovelPipelineTestSupport;

beforeEach(function () {
    $this->withoutMiddleware(ValidateCsrfToken::class);
});

test('creating a project creates an immutable anchor snapshot', function () {
    $user = User::factory()->create();
    $workspace = Workspace::factory()->create();

    WorkspaceMember::query()->create([
        'workspace_id' => $workspace->id,
        'user_id' => $user->id,
        'role' => 'owner',
    ]);

    $response = $this
        ->actingAs($user)
        ->post(route('workspace.projects.store', [
            'workspace_id' => $workspace->id,
        ]), [
            'name' => 'Anchor Snapshot Project',
        ]);

    $response->assertRedirect();

    $snapshot = ProjectSnapshot::query()
        ->where('snapshot_kind', ProjectSnapshot::KIND_ANCHOR)
        ->first();

    expect($snapshot)->not->toBeNull();
    expect($snapshot->name)->toBe('Original Version');
    expect($snapshot->is_immutable)->toBeTrue();
});

test('version history snapshot captures project settings multiprompt and advisor history', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Initial chapter content',
    ]);

    $context['project']->settings = [
        'aiModel' => 'gemini-2.5-flash',
        'advisorTemperature' => 0.4,
    ];
    $context['project']->save();

    ProjectNodeEditor::query()
        ->where('project_id', $context['project']->id)
        ->update([
            'graph_state' => [
                'nodes' => [['id' => 'root', 'type' => 'prompt']],
                'edges' => [],
                'pan' => ['x' => 10, 'y' => 20],
                'zoom' => 1.2,
            ],
            'templates' => [['id' => 'tpl-1', 'name' => 'Template 1']],
        ]);

    $chat = AdvisorChat::query()->create([
        'project_id' => $context['project']->id,
        'title' => 'Story Chat',
        'system_instructions' => 'Be strict.',
        'model' => 'gemini-2.5-flash',
    ]);

    AdvisorMessage::query()->create([
        'chat_id' => $chat->id,
        'role' => 'user',
        'content' => 'Hello advisor',
        'metadata' => ['chapter' => 1],
    ]);

    $response = $this
        ->actingAs($context['user'])
        ->postJson(route('version-history.snapshots.create', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'name' => 'Manual Snapshot',
        ]);

    $response->assertOk()->assertJsonPath('success', true);

    $snapshotId = $response->json('snapshot.id');
    $snapshot = ProjectSnapshot::query()->findOrFail($snapshotId);
    $data = $snapshot->snapshot_data;

    expect($snapshot->snapshot_kind)->toBe(ProjectSnapshot::KIND_MANUAL);
    expect(data_get($data, 'project.settings.aiModel'))->toBe('gemini-2.5-flash');
    expect(data_get($data, 'advisor.chats.0.title'))->toBe('Story Chat');
    expect(data_get($data, 'advisor.messages.0.content'))->toBe('Hello advisor');
    expect(data_get($data, 'multiprompt.graph_state.pan.x'))->toBe(10);
    expect(data_get($data, 'multiprompt.templates.0.name'))->toBe('Template 1');
});

test('snapshots cannot be deleted through the API', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();

    $snapshotId = ProjectSnapshot::query()
        ->where('project_id', $context['project']->id)
        ->where('snapshot_kind', ProjectSnapshot::KIND_ANCHOR)
        ->value('id');

    $response = $this
        ->actingAs($context['user'])
        ->deleteJson(route('version-history.snapshots.delete', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
            'snapshot_id' => $snapshotId,
        ]));

    $response
        ->assertStatus(405)
        ->assertJsonPath('error', 'Snapshots are immutable and cannot be deleted.');
});

test('restoring a snapshot queues an async restore and creates a pre restore snapshot', function () {
    Bus::fake();

    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Version A',
    ]);

    $context['project']->settings = ['aiModel' => 'gemini-2.5-flash'];
    $context['project']->save();

    $snapshotResponse = $this
        ->actingAs($context['user'])
        ->postJson(route('version-history.snapshots.create', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]), [
            'name' => 'Rollback Point',
        ]);

    $snapshotId = $snapshotResponse->json('snapshot.id');

    $context['project']->settings = ['aiModel' => 'gemini-2.5-pro'];
    $context['project']->save();

    $restoreResponse = $this
        ->actingAs($context['user'])
        ->postJson(route('version-history.snapshots.restore', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
            'snapshot_id' => $snapshotId,
        ]));

    $restoreResponse
        ->assertAccepted()
        ->assertJsonPath('success', true)
        ->assertJsonPath('operation.type', ProjectOperation::TYPE_SNAPSHOT_RESTORE)
        ->assertJsonPath('operation.is_locked', true);

    expect(
        ProjectSnapshot::query()
            ->where('project_id', $context['project']->id)
            ->where('snapshot_kind', ProjectSnapshot::KIND_PRE_RESTORE)
            ->count()
    )->toBe(1);

    Bus::assertDispatched(RestoreProjectSnapshotJob::class);
});

test('backups settings page renders project snapshots', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Version A',
    ]);

    app(ProjectSnapshotService::class)->createSnapshot(
        $context['project']->id,
        'Manual Snapshot',
        'Snapshot description',
        $context['user']->id,
    );

    $this
        ->actingAs($context['user'])
        ->get(route('workspace.projects.edit.backups', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]))
        ->assertInertia(fn (Assert $page) => $page
            ->component('Projects/Backups')
            ->where('projectId', $context['project']->id)
            ->where('summary.snapshot_count', 2)
            ->where('snapshots.0.name', 'Manual Snapshot'));
});

test('editor version history route redirects to backups settings page', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext();

    $this
        ->actingAs($context['user'])
        ->get(route('workspace.projects.editor.version-history', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]))
        ->assertRedirect(route('workspace.projects.edit.backups', [
            'workspace_id' => $context['workspace']->id,
            'project_id' => $context['project']->id,
        ]));
});

test('restore job rolls project state back and completes the operation', function () {
    $context = NovelPipelineTestSupport::createWorkspaceContext([
        'initial_content' => 'Version A',
    ]);

    $context['project']->settings = ['aiModel' => 'gemini-2.5-flash'];
    $context['project']->save();

    $snapshotId = app(ProjectSnapshotService::class)->createSnapshot(
        $context['project']->id,
        'Rollback Point',
        null,
        $context['user']->id,
    );

    $context['project']->settings = ['aiModel' => 'gemini-2.5-pro'];
    $context['project']->save();

    $operation = app(ProjectOperationStateService::class)->createRestoreOperation(
        $context['workspace']->id,
        $context['project']->id,
        $snapshotId,
        $context['user']->id,
    );

    $job = new RestoreProjectSnapshotJob(
        $context['workspace']->id,
        $context['project']->id,
        $snapshotId,
        $operation->id,
    );

    $job->handle(
        app(ProjectSnapshotService::class),
        app(ProjectOperationStateService::class),
    );

    expect($context['project']->fresh()->settings['aiModel'])->toBe('gemini-2.5-flash');
    expect($operation->fresh()->status)->toBe(ProjectOperation::STATUS_COMPLETED);
});
