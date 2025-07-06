<?php

namespace App\Http\Controllers;

use App\Jobs\AuthorStyleJob;
use App\Models\Projects;
use App\Models\StructuredAuthorStyle;
use App\Models\Workspace;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Validator;
use Inertia\Inertia;

class FileManagerController extends Controller
{
    /**
     * Display the file manager page.
     *
     * @param  string  $workspace_id
     * @return \Inertia\Response
     */
    public function show($workspace_id)
    {
        // Get the workspace with its cloud storage settings
        $workspace = Workspace::findOrFail($workspace_id);
        
        // Get storage providers from cloud_storage JSON column
        $storageProviders = $this->getStorageProviders($workspace);
        
        // Get author styles with their project counts
        $authorStyles = $this->getAuthorStyles($workspace_id);
        
        // Get projects with their shared users
        $projects = $this->getProjects($workspace_id);
        
        return Inertia::render('FileManager/Main', [
            'workspaceId' => $workspace_id,
            'workspaceName' => $workspace->name,
            'storageProviders' => $storageProviders,
            'authorStyles' => $authorStyles,
            'projects' => $projects,
        ]);
    }
    
    /**
     * Create a new author style.
     *
     * @param  \Illuminate\Http\Request  $request
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
        $existingStyle = StructuredAuthorStyle::where('workspace_id', $workspace_id)
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
            
        if (!$project) {
            \Log::warning('Project does not belong to workspace', [
                'project_id' => $request->project_id,
                'workspace_id' => $workspace_id,
            ]);
            return back()->withErrors(['project_id' => 'The selected project does not belong to this workspace.'])->withInput();
        }
        
        // Store the uploaded files
        $filePaths = [];
        foreach ($request->file('author_files') as $file) {
            $path = $file->store('author_styles/' . $workspace_id, 'local');
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
        
        return redirect()->route('workspace.files', ['workspace_id' => $workspace_id])
            ->with('success', 'Author style creation has been initiated. This may take a few minutes to complete.');
    }
    
    
    /**
     * Get storage providers from workspace cloud_storage JSON column.
     *
     * @param  \App\Models\Workspace  $workspace
     * @return array
     */
    private function getStorageProviders(Workspace $workspace)
    {
        $cloudStorage = $workspace->cloud_storage ?? [];
        $storageProviders = [];
        
        // Local Storage is always enabled and should be first
        $storageProviders[] = [
            'id' => 'local_storage',
            'name' => 'Local Storage',
            'icon' => 'HardDrive',
            'color' => 'text-gray-500',
            'used' => rand(50, 200), // Random usage for now
            'total' => 500,
            'percentage' => rand(10, 40), // Random percentage for now
            'enabled' => true,
        ];
        
        // Google Drive
        $googleDriveEnabled = isset($cloudStorage['google_drive']['enabled']) && $cloudStorage['google_drive']['enabled'];
        if (isset($cloudStorage['google_drive'])) {
            $storageProviders[] = [
                'id' => 'google_drive',
                'name' => 'Google Drive',
                'icon' => 'Cloud',
                'color' => 'text-blue-500',
                'used' => rand(100, 180), // Random usage for now
                'total' => 200,
                'percentage' => rand(50, 90), // Random percentage for now
                'enabled' => $googleDriveEnabled,
            ];
        }
        
        // Dropbox
        $dropboxEnabled = isset($cloudStorage['dropbox']['enabled']) && $cloudStorage['dropbox']['enabled'];
        if (isset($cloudStorage['dropbox'])) {
            $storageProviders[] = [
                'id' => 'dropbox',
                'name' => 'Dropbox',
                'icon' => 'Dropbox',
                'color' => 'text-indigo-500',
                'used' => rand(20, 40), // Random usage for now
                'total' => 50,
                'percentage' => rand(40, 80), // Random percentage for now
                'enabled' => $dropboxEnabled,
            ];
        }
        
        // OneDrive
        $oneDriveEnabled = isset($cloudStorage['onedrive']['enabled']) && $cloudStorage['onedrive']['enabled'];
        if (isset($cloudStorage['onedrive'])) {
            $storageProviders[] = [
                'id' => 'onedrive',
                'name' => 'OneDrive',
                'icon' => 'Cloud',
                'color' => 'text-sky-500',
                'used' => rand(30, 60), // Random usage for now
                'total' => 100,
                'percentage' => rand(30, 60), // Random percentage for now
                'enabled' => $oneDriveEnabled,
            ];
        }
        
        // If the cloud storage providers don't exist in the workspace settings,
        // add them as disabled by default
        if (!isset($cloudStorage['google_drive'])) {
            $storageProviders[] = [
                'id' => 'google_drive',
                'name' => 'Google Drive',
                'icon' => 'Cloud',
                'color' => 'text-blue-500',
                'used' => 0,
                'total' => 200,
                'percentage' => 0,
                'enabled' => false,
            ];
        }
        
        if (!isset($cloudStorage['dropbox'])) {
            $storageProviders[] = [
                'id' => 'dropbox',
                'name' => 'Dropbox',
                'icon' => 'Dropbox',
                'color' => 'text-indigo-500',
                'used' => 0,
                'total' => 50,
                'percentage' => 0,
                'enabled' => false,
            ];
        }
        
        if (!isset($cloudStorage['onedrive'])) {
            $storageProviders[] = [
                'id' => 'onedrive',
                'name' => 'OneDrive',
                'icon' => 'Cloud',
                'color' => 'text-sky-500',
                'used' => 0,
                'total' => 100,
                'percentage' => 0,
                'enabled' => false,
            ];
        }
        
        return $storageProviders;
    }
    
    /**
     * Get author styles with their project counts.
     *
     * @param  string  $workspace_id
     * @return array
     */
    private function getAuthorStyles($workspace_id)
    {
        $authorStyles = StructuredAuthorStyle::where('workspace_id', $workspace_id)
            ->select('id', 'author_name')
            ->get();
        
        $result = [];
        $colors = ['bg-blue-100', 'bg-purple-100', 'bg-green-100', 'bg-pink-100', 'bg-amber-100', 'bg-cyan-100'];
        
        foreach ($authorStyles as $index => $style) {
            // Count how many projects use this author style
            $projectCount = DB::table('projects')
                ->join('structured_author_styles', 'projects.id', '=', 'structured_author_styles.project_id')
                ->where('structured_author_styles.id', $style->id)
                ->count();
            
            // Get the first letter of the author name for the avatar
            $avatar = substr($style->author_name, 0, 1);
            
            // Assign a color from the colors array
            $colorIndex = $index % count($colors);
            $color = $colors[$colorIndex];
            
            $result[] = [
                'id' => $style->id,
                'name' => $style->author_name,
                'fileCount' => $projectCount,
                'avatar' => $avatar,
                'color' => $color,
            ];
        }
        
        return $result;
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
            ->select('id', 'name', 'created_at', 'access', 'saved_in')
            ->get();
        
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
            
            // Map saved_in codes to provider names
            $savedInMap = [
                '01' => 'Local Storage',
                '02' => 'Google Drive',
                '03' => 'Dropbox',
                '04' => 'OneDrive',
            ];
            
            $savedIn = $savedInMap[$project->saved_in] ?? 'Local Storage';
            
            // Calculate a fake size for now
            $size = rand(1, 10) . '.' . rand(1, 9) . ' MB';
            
            $result[] = [
                'id' => $project->id,
                'name' => $project->name,
                'size' => $size, // Fake size for now
                'createdAt' => $project->created_at->format('Y-m-d'),
                'sharedWith' => $sharedWith,
                'savedIn' => $savedIn,
            ];
        }
        
        return $result;
    }
}
