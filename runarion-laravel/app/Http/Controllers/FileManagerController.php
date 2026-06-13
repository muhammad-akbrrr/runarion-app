<?php

namespace App\Http\Controllers;

use App\Jobs\AuthorStyleJob;
use App\Models\AuthorStyle;
use App\Models\Projects;
use App\Models\Workspace;
use App\Services\AuthorStyleFormatter;
use App\Services\ProjectOperationStateService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Validator;
use Inertia\Inertia;

class FileManagerController extends Controller
{
    public function __construct(
        private readonly AuthorStyleFormatter $authorStyleFormatter,
        private readonly ProjectOperationStateService $operationStateService,
    ) {}

    public function show($workspace_id)
    {
        $workspace = Workspace::findOrFail($workspace_id);
        $authorStyles = $this->getAuthorStyles($workspace_id);
        $projects = $this->getProjects($workspace_id);

        return Inertia::render('FileManager/Main', [
            'workspaceId' => $workspace_id,
            'workspaceName' => $workspace->name,
            'authorStyles' => $authorStyles,
            'projects' => $projects,
        ]);
    }

    /**
     * Create a new author style.
     *
     * @param  string  $workspace_id
     * @return \Illuminate\Http\RedirectResponse
     */
    public function storeAuthorStyle(Request $request, $workspace_id)
    {
        // Validate the request
        $validator = Validator::make($request->all(), [
            'author_name' => ['required', 'string', 'max:255'],
            'project_id' => ['required', 'string', 'exists:projects,id'],
            'author_files' => ['required', 'array', 'min:1'],
            'author_files.*' => ['required', 'file', 'mimes:pdf,doc,docx,txt', 'max:102400'], // 100MB max
        ]);

        if ($validator->fails()) {
            \Log::warning('Validation failed in storeAuthorStyle', [
                'errors' => $validator->errors()->toArray(),
            ]);

            return back()->withErrors($validator)->withInput();
        }

        // Check if author style name already exists for this workspace
        $existingStyle = AuthorStyle::where('workspace_id', $workspace_id)
            ->where('author_name', $request->author_name)
            ->first();

        if ($existingStyle) {
            \Log::info('Author style name already exists', [
                'workspace_id' => $workspace_id,
                'author_name' => $request->author_name,
            ]);

            return back()->withErrors(['author_name' => 'An author style with this name already exists.'])->withInput();
        }

        // Check if project belongs to the workspace
        $project = Projects::where('id', $request->project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            \Log::warning('Project does not belong to workspace', [
                'project_id' => $request->project_id,
                'workspace_id' => $workspace_id,
            ]);

            return back()->withErrors(['project_id' => 'The selected project does not belong to this workspace.'])->withInput();
        }

        if ($this->operationStateService->getProjectLock($workspace_id, $project->id)) {
            return back()->withErrors([
                'project_id' => 'This project is currently locked by an active operation.',
            ])->withInput();
        }

        // Store the uploaded files
        $filePaths = [];
        foreach ($request->file('author_files') as $file) {
            $path = $file->store('author_styles/'.$workspace_id, 'local');
            $filePaths[] = Storage::disk('local')->path($path);
        }

        // Dispatch the job to analyze the author style
        AuthorStyleJob::dispatch(
            Auth::id(),
            $workspace_id,
            $request->project_id,
            $request->author_name,
            $filePaths
        );
        \Log::info('AuthorStyleJob dispatched', [
            'user_id' => Auth::id(),
            'workspace_id' => $workspace_id,
            'project_id' => $request->project_id,
            'author_name' => $request->author_name,
            'file_paths' => $filePaths,
        ]);

        return redirect()->route('workspace.artifacts', ['workspace_id' => $workspace_id])
            ->with('success', 'Author style creation has been initiated. This may take a few minutes to complete.');
    }

    /**
     * Delete an author style.
     *
     * @param  string  $workspace_id
     * @param  string  $author_style_id
     * @return \Illuminate\Http\JsonResponse|\Illuminate\Http\RedirectResponse
     */
    public function deleteAuthorStyle(Request $request, $workspace_id, $author_style_id)
    {
        try {
            $authorStyle = AuthorStyle::where('workspace_id', $workspace_id)
                ->where('id', $author_style_id)
                ->first();

            if (! $authorStyle) {
                if ($request->wantsJson()) {
                    return response()->json(['error' => 'Author style not found.'], 404);
                }

                return back()->withErrors(['error' => 'Author style not found.']);
            }

            if ($authorStyle->project_id && $this->operationStateService->getProjectLock($workspace_id, $authorStyle->project_id)) {
                if ($request->wantsJson()) {
                    return response()->json(['error' => 'This author style is attached to a project that is currently locked.'], 423);
                }

                return back()->withErrors(['error' => 'This author style is attached to a project that is currently locked.']);
            }

            // Clean up related data in Python's tables
            DB::table('author_styles_to_samples')
                ->where('author_style_id', $author_style_id)
                ->delete();

            DB::table('author_style_chunks')
                ->where('author_style_id', $author_style_id)
                ->delete();

            // Delete the author style
            $authorStyle->delete();

            \Log::info('Author style deleted', [
                'author_style_id' => $author_style_id,
                'workspace_id' => $workspace_id,
            ]);

            if ($request->wantsJson()) {
                return response()->json(['success' => true, 'message' => 'Author style deleted successfully.']);
            }

            return redirect()->route('workspace.artifacts', ['workspace_id' => $workspace_id])
                ->with('success', 'Author style deleted successfully.');

        } catch (\Exception $e) {
            \Log::error('Failed to delete author style', [
                'author_style_id' => $author_style_id,
                'error' => $e->getMessage(),
            ]);

            if ($request->wantsJson()) {
                return response()->json(['error' => 'Failed to delete author style.'], 500);
            }

            return back()->withErrors(['error' => 'Failed to delete author style.']);
        }
    }

    /**
     * Update an author style.
     *
     * @param  string  $workspace_id
     * @param  string  $author_style_id
     * @return \Illuminate\Http\JsonResponse|\Illuminate\Http\RedirectResponse
     */
    public function updateAuthorStyle(Request $request, $workspace_id, $author_style_id)
    {
        try {
            $authorStyle = AuthorStyle::where('workspace_id', $workspace_id)
                ->where('id', $author_style_id)
                ->first();

            if (! $authorStyle) {
                if ($request->wantsJson()) {
                    return response()->json(['error' => 'Author style not found.'], 404);
                }

                return back()->withErrors(['error' => 'Author style not found.']);
            }

            if ($authorStyle->project_id && $this->operationStateService->getProjectLock($workspace_id, $authorStyle->project_id)) {
                if ($request->wantsJson()) {
                    return response()->json(['error' => 'This author style is attached to a project that is currently locked.'], 423);
                }

                return back()->withErrors(['error' => 'This author style is attached to a project that is currently locked.']);
            }

            // Update allowed fields
            $updateData = [];

            if ($request->has('author_name')) {
                // Check for duplicate name
                $existing = AuthorStyle::where('workspace_id', $workspace_id)
                    ->where('author_name', $request->author_name)
                    ->where('id', '!=', $author_style_id)
                    ->first();

                if ($existing) {
                    if ($request->wantsJson()) {
                        return response()->json(['error' => 'An author style with this name already exists.'], 400);
                    }

                    return back()->withErrors(['author_name' => 'An author style with this name already exists.']);
                }

                $updateData['author_name'] = $request->author_name;
            }

            if ($request->has('techniques_json')) {
                $updateData['techniques_json'] = $request->techniques_json;
            }

            if ($request->has('examples_json')) {
                $updateData['examples_json'] = $request->examples_json;
            }

            if ($request->has('adaptation_json')) {
                $updateData['adaptation_json'] = $request->adaptation_json;
            }

            if ($request->has('project_ids')) {
                // For now, we store the first project_id (multi-project will be a separate table later)
                // TODO: Implement author_style_projects pivot table for true multi-project support
                $projectIds = $request->project_ids;
                if (! empty($projectIds) && is_array($projectIds)) {
                    $updateData['project_id'] = $projectIds[0];
                }
            }

            $authorStyle->update($updateData);

            \Log::info('Author style updated', [
                'author_style_id' => $author_style_id,
                'updates' => array_keys($updateData),
            ]);

            if ($request->wantsJson()) {
                return response()->json([
                    'success' => true,
                    'message' => 'Author style updated successfully.',
                    'author_style' => $this->authorStyleFormatter->format($authorStyle->fresh()),
                ]);
            }

            return redirect()->route('workspace.artifacts', ['workspace_id' => $workspace_id])
                ->with('success', 'Author style updated successfully.');

        } catch (\Exception $e) {
            \Log::error('Failed to update author style', [
                'author_style_id' => $author_style_id,
                'error' => $e->getMessage(),
            ]);

            if ($request->wantsJson()) {
                return response()->json(['error' => 'Failed to update author style.'], 500);
            }

            return back()->withErrors(['error' => 'Failed to update author style.']);
        }
    }

    /**
     * Get a single author style with full details.
     *
     * @param  string  $workspace_id
     * @param  string  $author_style_id
     * @return \Illuminate\Http\JsonResponse
     */
    public function getAuthorStyle(Request $request, $workspace_id, $author_style_id)
    {
        $authorStyle = AuthorStyle::where('workspace_id', $workspace_id)
            ->where('id', $author_style_id)
            ->first();

        if (! $authorStyle) {
            return response()->json(['error' => 'Author style not found.'], 404);
        }

        return response()->json([
            'author_style' => $this->authorStyleFormatter->format($authorStyle, true),
        ]);
    }

    /**
     * Get author styles with their project counts.
     *
     * @param  string  $workspace_id
     * @return array
     */
    private function getAuthorStyles($workspace_id)
    {
        return $this->authorStyleFormatter->formatCollection(
            AuthorStyle::where('workspace_id', $workspace_id)->get()
        );
    }

    /**
     * Get projects with their shared users.
     *
     * @param  string  $workspace_id
     * @return array
     */
    private function getProjects($workspace_id)
    {
        $projects = Projects::where('workspace_id', $workspace_id)
            ->where('is_active', true)
            ->select('id', 'name', 'created_at', 'updated_at', 'access')
            ->get();

        $locks = $this->operationStateService->getLocksForProjects(
            $workspace_id,
            $projects->pluck('id')->all(),
        );

        $result = [];

        foreach ($projects as $project) {
            // Get shared users from the access JSON column
            $sharedWith = [];
            if ($project->access) {
                foreach ($project->access as $access) {
                    if (isset($access['user']['name'])) {
                        $sharedWith[] = $access['user']['name'];
                    }
                }
            }

            // Calculate a fake size for now
            $size = rand(1, 10).'.'.rand(1, 9).' MB';

            $result[] = [
                'id' => $project->id,
                'name' => $project->name,
                'size' => $size, // Fake size for now
                'createdAt' => $project->created_at->format('Y-m-d'),
                'sharedWith' => $sharedWith,
                'pipelineLock' => $locks[$project->id] ?? null,
            ];
        }

        return $result;
    }
}
