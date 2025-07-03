<?php

namespace App\Http\Controllers;

use App\Models\Workspace;
use Illuminate\Http\Request;
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
        $workspace = Workspace::findOrFail($workspace_id);
        
        return Inertia::render('FileManager/Index', [
            'workspaceId' => $workspace_id,
            'workspaceName' => $workspace->name,
        ]);
    }
}
