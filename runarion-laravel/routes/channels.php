<?php

use Illuminate\Support\Facades\Broadcast;
use App\Models\Projects;
use App\Models\WorkspaceMember;

/*
|--------------------------------------------------------------------------
| Broadcast Channels
|--------------------------------------------------------------------------
|
| Here you may register all of the event broadcasting channels that your
| application supports. The given channel authorization callbacks are
| used to check if an authenticated user can listen to the channel.
|
*/

Broadcast::channel('project.{workspaceId}.{projectId}', function ($user, $workspaceId, $projectId) {
    $isMember = WorkspaceMember::where('workspace_id', $workspaceId)
        ->where('user_id', $user->id)
        ->exists();
    
    if (!$isMember) {
        return false;
    }
    
    // Check if project exists and belongs to the workspace
    $project = Projects::where('id', $projectId)
        ->where('workspace_id', $workspaceId)
        ->first();
    
    if (!$project) {
        return false;
    }
    
    // Check if user has access to the project
    if ($project->access) {
        $hasAccess = collect($project->access)->contains(function ($access) use ($user) {
            return $access['user']['id'] == $user->id;
        });
        
        if (!$hasAccess) {
            return false;
        }
    }
    
    return true;
});
