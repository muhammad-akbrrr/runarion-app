<?php

namespace App\Http\Controllers\ProjectEditor;

use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use App\Models\Projects;
use App\Models\ProjectContent;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Inertia\Inertia;

class ImageGeneratorController extends Controller
{
    /**
     * Get Python service URL from environment.
     * Handles both Docker (python-app) and local development (localhost) scenarios.
     */
    private function getPythonServiceUrl(): string
    {
        $url = env('PYTHON_SERVICE_URL');
        
        if ($url) {
            return $url;
        }
        
        // Auto-detect: Check if we're in Docker by looking for .dockerenv or container hostname
        // If in Docker, use service name; otherwise use localhost
        $isDocker = file_exists('/.dockerenv') || 
                   gethostname() !== php_uname('n') ||
                   getenv('container') !== false;
        
        return $isDocker ? 'http://python-app:5000' : 'http://localhost:5000';
    }

    /**
     * Show the image editor page inside of the project editor.
     */
    public function imageGenerator(Request $request, string $workspace_id, string $project_id)
    {
        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (!$project) {
            return redirect()->route('workspace.projects', ['workspace_id' => $workspace_id]);
        }

        // Get chapters for the project
        $projectContent = ProjectContent::where('project_id', $project_id)->first();
        $chapters = [];
        if ($projectContent && $projectContent->content && is_array($projectContent->content)) {
            $chapters = $projectContent->content;
            // Sort by order
            usort($chapters, function ($a, $b) {
                return ($a['order'] ?? 0) - ($b['order'] ?? 0);
            });
        }

        return Inertia::render('Projects/Editor/ImgGenerator/Main', [
            'workspaceId' => $workspace_id,
            'projectId' => $project_id,
            'project' => $project,
            'chapters' => $chapters,
        ]);
    }

    /**
     * Generate a chapter cover image.
     */
    public function generateChapterCover(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'prompt' => 'required|string|max:2000',
            'negative_prompt' => 'nullable|string|max:2000',
            'chapter_id' => 'nullable|integer',
            'width' => 'integer|min:256|max:2048',
            'height' => 'integer|min:256|max:2048',
            'num_inference_steps' => 'nullable|integer|min:10|max:50',
            'guidance_scale' => 'nullable|numeric|min:1|max:20',
            'seed' => 'nullable|integer',
            'transparent_background' => 'boolean',
            'border_template_path' => 'nullable|string',
        ]);

        try {
            $pythonApiUrl = $this->getPythonServiceUrl();

            Log::info('Generating chapter cover', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_id' => $validated['chapter_id'] ?? null,
                'prompt' => substr($validated['prompt'], 0, 100),
            ]);

            $response = Http::timeout(600) // 10 minutes for SDXL image generation
                ->withOptions([
                    'stream' => false, // Ensure we get the full response
                    'verify' => false, // Skip SSL verification for internal services
                ])
                ->post("{$pythonApiUrl}/api/generate-chapter-cover", [
                    'prompt' => $validated['prompt'],
                    'negative_prompt' => $validated['negative_prompt'] ?? 'text, watermark, signature, low quality, blurry, deformed',
                    'width' => $validated['width'] ?? 768,
                    'height' => $validated['height'] ?? 768,
                    'num_inference_steps' => $validated['num_inference_steps'] ?? 20,
                    'guidance_scale' => $validated['guidance_scale'] ?? 5,
                    'seed' => $validated['seed'] ?? null,
                    'transparent_background' => $validated['transparent_background'] ?? false,
                    'border_template_path' => $validated['border_template_path'] ?? null,
                ]);

            if (!$response->successful()) {
                // Try to get error message - might be JSON or plain text
                $error = 'Failed to generate chapter cover';
                try {
                    $errorData = $response->json();
                    $error = $errorData['error'] ?? $errorData['details'] ?? $error;
                } catch (\Exception $e) {
                    $errorText = $response->body();
                    if (!empty($errorText) && strlen($errorText) < 1000) {
                        $error = $errorText;
                    }
                }
                
                Log::error('Chapter cover generation error', [
                    'status' => $response->status(),
                    'error' => $error,
                    'content_type' => $response->header('Content-Type'),
                ]);
                return response()->json(['error' => $error], $response->status());
            }

            // Check if response is actually an image
            $contentType = $response->header('Content-Type', '');
            $isImage = strpos($contentType, 'image/') !== false;
            
            if (!$isImage) {
                // Might be an error response in JSON format
                try {
                    $errorData = $response->json();
                    $error = $errorData['error'] ?? $errorData['details'] ?? 'Invalid response from image service';
                    Log::error('Non-image response from Python service', [
                        'content_type' => $contentType,
                        'error' => $error,
                        'body_preview' => substr($response->body(), 0, 500),
                    ]);
                    return response()->json(['error' => $error], 500);
                } catch (\Exception $e) {
                    Log::error('Failed to parse error response', [
                        'content_type' => $contentType,
                        'exception' => $e->getMessage(),
                    ]);
                    return response()->json(['error' => 'Invalid response from image service'], 500);
                }
            }

            // Return image as base64 for frontend
            $imageBytes = $response->body();
            
            // Validate image response
            if (empty($imageBytes) || strlen($imageBytes) < 100) {
                // Response is too small to be a valid image
                Log::error('Invalid image response - too small', [
                    'size' => strlen($imageBytes),
                    'content_type' => $contentType,
                    'body_preview' => substr($imageBytes, 0, 200),
                ]);
                return response()->json(['error' => 'Invalid image response from service - image too small'], 500);
            }
            
            // Validate PNG header (should start with PNG signature)
            $pngSignature = "\x89PNG\r\n\x1a\n";
            if (substr($imageBytes, 0, 8) !== $pngSignature) {
                Log::error('Invalid image response - not a valid PNG', [
                    'size' => strlen($imageBytes),
                    'content_type' => $contentType,
                    'header' => bin2hex(substr($imageBytes, 0, 16)),
                ]);
                // Still try to encode it, might be valid but corrupted header
            }
            
            $base64Image = base64_encode($imageBytes);
            
            Log::info('Image generated successfully', [
                'size' => strlen($imageBytes),
                'content_type' => $contentType,
                'base64_length' => strlen($base64Image),
            ]);

            return response()->json([
                'success' => true,
                'image' => 'data:image/png;base64,' . $base64Image,
                'image_bytes' => $base64Image, // For PDF generation later
            ]);

        } catch (\Exception $e) {
            Log::error('Exception generating chapter cover', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return response()->json([
                'error' => 'Failed to generate chapter cover: ' . $e->getMessage()
            ], 500);
        }
    }

    /**
     * Generate PDF book from chapters.
     */
    public function generatePDF(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'chapters' => 'required|array|min:1',
            'chapters.*.title' => 'required|string',
            'chapters.*.content' => 'required|string',
            'chapters.*.cover_image_bytes' => 'nullable|string', // base64 encoded
            'paper_size' => 'string|in:a4,letter',
            'margins' => 'nullable|array',
            'margins.top' => 'nullable|numeric|min:0|max:3',
            'margins.bottom' => 'nullable|numeric|min:0|max:3',
            'margins.left' => 'nullable|numeric|min:0|max:3',
            'margins.right' => 'nullable|numeric|min:0|max:3',
            'font_name' => 'nullable|string',
            'font_size' => 'nullable|integer|min:8|max:24',
            'line_spacing' => 'nullable|numeric|min:1|max:3',
            'include_covers' => 'boolean',
            // New PDF features
            'drop_cap' => 'boolean',
            'drop_cap_font' => 'nullable|string',
            'drop_cap_uppercase' => 'boolean',
            'chapter_borders' => 'boolean',
            'include_toc' => 'boolean',
        ]);

        try {
            $pythonApiUrl = $this->getPythonServiceUrl();

            Log::info('Generating PDF', [
                'workspace_id' => $workspace_id,
                'project_id' => $project_id,
                'chapter_count' => count($validated['chapters']),
            ]);

            $response = Http::timeout(600) // 10 minutes for PDF generation (may include image generation)
                ->post("{$pythonApiUrl}/api/generate-pdf", [
                    'chapters' => $validated['chapters'],
                    'paper_size' => $validated['paper_size'] ?? 'a4',
                    'margins' => $validated['margins'] ?? null,
                    'font_name' => $validated['font_name'] ?? 'Times-Roman',
                    'font_size' => $validated['font_size'] ?? 12,
                    'line_spacing' => $validated['line_spacing'] ?? 1.5,
                    'include_covers' => $validated['include_covers'] ?? true,
                    // New PDF features
                    'drop_cap' => $validated['drop_cap'] ?? true,
                    'drop_cap_font' => $validated['drop_cap_font'] ?? 'UnifrakturCook',
                    'drop_cap_uppercase' => $validated['drop_cap_uppercase'] ?? true,
                    'chapter_borders' => $validated['chapter_borders'] ?? false,
                    'include_toc' => $validated['include_toc'] ?? true,
                ]);

            if (!$response->successful()) {
                $error = $response->json('error') ?? 'Failed to generate PDF';
                Log::error('PDF generation error', [
                    'status' => $response->status(),
                    'error' => $error,
                ]);
                return response()->json(['error' => $error], $response->status());
            }

            // Return PDF as base64 for frontend
            $pdfBytes = $response->body();
            $base64Pdf = base64_encode($pdfBytes);

            return response()->json([
                'success' => true,
                'pdf' => 'data:application/pdf;base64,' . $base64Pdf,
                'pdf_bytes' => $base64Pdf,
            ]);

        } catch (\Exception $e) {
            Log::error('Exception generating PDF', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return response()->json([
                'error' => 'Failed to generate PDF: ' . $e->getMessage()
            ], 500);
        }
    }

    /**
     * Generate a border template using Stable Diffusion ControlNet.
     */
    public function generateBorderTemplate(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'prompt' => 'nullable|string|max:2000',
            'width' => 'integer|min:256|max:2048',
            'height' => 'integer|min:256|max:2048',
            'border_thickness' => 'integer|min:20|max:200',
            'border_style' => 'string|in:rectangular,circular,ornate',
            'template_name' => 'required|string|max:100',
            'num_inference_steps' => 'nullable|integer|min:10|max:50',
            'guidance_scale' => 'nullable|numeric|min:1|max:20',
            'seed' => 'nullable|integer',
        ]);

        try {
            $pythonApiUrl = $this->getPythonServiceUrl();

            $response = Http::timeout(600) // 10 minutes for SDXL border generation
                ->post("{$pythonApiUrl}/api/generate-border-template", [
                    'prompt' => $validated['prompt'] ?? 'ornate decorative border frame, intricate patterns, elegant design',
                    'width' => $validated['width'] ?? 1024,
                    'height' => $validated['height'] ?? 1024,
                    'border_thickness' => $validated['border_thickness'] ?? 80,
                    'border_style' => $validated['border_style'] ?? 'rectangular',
                    'template_name' => $validated['template_name'],
                    'num_inference_steps' => $validated['num_inference_steps'] ?? 30,
                    'guidance_scale' => $validated['guidance_scale'] ?? 7.5,
                    'seed' => $validated['seed'] ?? null,
                ]);

            if (!$response->successful()) {
                $error = $response->json('error') ?? 'Failed to generate border template';
                Log::error('Border template generation error', [
                    'status' => $response->status(),
                    'error' => $error,
                ]);
                return response()->json(['error' => $error], $response->status());
            }

            return response()->json($response->json());

        } catch (\Exception $e) {
            Log::error('Exception generating border template', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return response()->json([
                'error' => 'Failed to generate border template: ' . $e->getMessage()
            ], 500);
        }
    }

    /**
     * List available border templates.
     */
    public function listBorderTemplates(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $pythonApiUrl = $this->getPythonServiceUrl();

            $response = Http::timeout(30)
                ->get("{$pythonApiUrl}/api/border-templates");

            if (!$response->successful()) {
                return response()->json(['error' => 'Failed to list border templates'], $response->status());
            }

            return response()->json($response->json());

        } catch (\Exception $e) {
            Log::error('Exception listing border templates', [
                'error' => $e->getMessage(),
            ]);
            return response()->json([
                'error' => 'Failed to list border templates: ' . $e->getMessage()
            ], 500);
        }
    }
}
