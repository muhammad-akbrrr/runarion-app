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
            // Make the API call to the Python service
            $response = Http::post('http://python-app:5000/api/generate', $request);

            // Log the response for debugging
            Log::info('Python API Response', ['response' => $response->json()]);

            // Check if the request was successful
            if ($response->successful()) {
                $responseData = $response->json();

                // Ensure 'success' field exists
                if (!isset($responseData['success'])) {
                    $responseData['success'] = true;
                }

                // Flash the response data to the session
                return redirect()->back()->with('data', $responseData);
            }

            // Flash the failure response
            return redirect()->back()->with('data', [
                'success' => false,
                'error_message' => 'Failed to generate story: ' . $response->body(),
            ]);
        } catch (\Exception $e) {
            Log::error('Story generation error: ' . $e->getMessage());

            // Flash the exception error
            return redirect()->back()->with('data', [
                'success' => false,
                'error_message' => 'An error occurred while generating the story: ' . $e->getMessage(),
            ]);
        }
    }
}
