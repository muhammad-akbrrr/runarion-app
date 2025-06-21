<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class StoryGeneratorController extends Controller
{
    /**
     * Generate story content using the Python API.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  string  $workspace_id
     * @param  string  $project_id
     * @return \Illuminate\Http\RedirectResponse
     */
    public function generate(Request $request, string $workspace_id, string $project_id)
    {
        try {
            // Validate the request data
            $validated = $request->validate([
                'usecase' => 'required|string',
                'provider' => 'required|string',
                'model' => 'required|string',
                'prompt' => 'required|string',
                'instruction' => 'nullable|string',
                'generation_config' => 'required|array',
                'prompt_config' => 'required|array',
                'caller' => 'required|array',
            ]);

            // Make the API call to the Python service
            $response = Http::post('http://python-app:5000/api/generate', $validated);

            // Log the response for debugging
            Log::info('Python API Response', ['response' => $response->json()]);

            // Check if the request was successful
            if ($response->successful()) {
                $responseData = $response->json();
                
                // Make sure the response has the expected structure
                if (!isset($responseData['success'])) {
                    $responseData['success'] = true;
                }
                
                // Store the response data in the session
                session(['data' => $responseData]);
                
                // Return to the previous page
                return redirect()->back();
            }

            // If the request failed, store the error in the session
            session(['data' => [
                'success' => false,
                'error_message' => 'Failed to generate story: ' . $response->body(),
            ]]);
            
            // Return to the previous page
            return redirect()->back();
        } catch (\Exception $e) {
            Log::error('Story generation error: ' . $e->getMessage());
            
            // Store the error in the session
            session(['data' => [
                'success' => false,
                'error_message' => 'An error occurred while generating the story: ' . $e->getMessage(),
            ]]);
            
            // Return to the previous page
            return redirect()->back();
        }
    }
}
