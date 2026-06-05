<?php

namespace App\Http\Controllers\ProjectEditor;

use App\Http\Controllers\Controller;
use App\Models\ProjectContent;
use App\Models\Projects;
use App\Services\VersionControlService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ChainBuilderController extends Controller
{
    protected VersionControlService $versionControl;

    public function __construct(VersionControlService $versionControl)
    {
        $this->versionControl = $versionControl;
    }

    /**
     * Get Python service URL from environment.
     */
    private function getPythonServiceUrl(): string
    {
        return env('PYTHON_SERVICE_URL', 'http://python-app:5000');
    }

    /**
     * Get story context from project chapters
     */
    private function getStoryContext(string $project_id, int $limit = 500000): string
    {
        $projectContent = ProjectContent::where('project_id', $project_id)->first();

        if (! $projectContent || ! $projectContent->content) {
            return '';
        }

        $chapters = $projectContent->content;
        if (! is_array($chapters)) {
            return '';
        }

        // Sort by order
        usort($chapters, function ($a, $b) {
            return ($a['order'] ?? 0) - ($b['order'] ?? 0);
        });

        $contextParts = [];
        foreach ($chapters as $chapter) {
            $content = $chapter['content'] ?? '';
            if ($content) {
                $contextParts[] = "=== {$chapter['chapter_name']} ===\n{$content}";
            }
        }

        $fullContext = implode("\n\n", $contextParts);

        // Return last N characters for continuation context
        if (strlen($fullContext) > $limit) {
            return '...'.substr($fullContext, -$limit);
        }

        return $fullContext;
    }

    /**
     * Execute a single graph node
     */
    public function executeNode(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'node_prompt' => 'required|string',
            'inputs' => 'array',
            'story_context' => 'string',
            'ai_model' => 'string',
            'author_profile' => 'nullable|string',
            'settings' => 'nullable|array',
            'node_type' => 'nullable|in:prompt,logic', // Optional: specify if this is for a prompt or logic node
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            // Get story context if not provided
            $storyContext = $validated['story_context'] ?? $this->getStoryContext($project_id);

            // Format inputs
            $inputsText = '';
            if (! empty($validated['inputs'])) {
                $inputParts = [];
                foreach ($validated['inputs'] as $input) {
                    $typeLabel = ($input['type'] ?? '') === 'context' ? 'BACKGROUND DATA' : 'PREVIOUS STEP OUTPUT';
                    $inputParts[] = "--- {$typeLabel} ({$input['label']}) ---\n{$input['text']}\n-------------------";
                }
                $inputsText = implode("\n\n", $inputParts);
            }

            // Build prompt for chain builder node
            // StoryHandler will build instruction with author profile/style benefits
            // Our prompt contains node-specific instructions and context

            // Build the story context and node inputs section
            $prompt = "GLOBAL STORY CONTEXT (The story so far):\n\"\"\"\n{$storyContext}\n\"\"\"\n\n";

            if ($inputsText) {
                $prompt .= "INPUTS FROM CONNECTED NODES (Data/Logic):\n{$inputsText}\n\n";
            } else {
                $prompt .= "INPUTS FROM CONNECTED NODES: No upstream inputs.\n\n";
            }

            // Add node-specific instruction
            $prompt .= "YOUR NODE INSTRUCTION:\n{$validated['node_prompt']}\n\n";

            // Determine node type
            $nodeType = $validated['node_type'] ?? 'prompt'; // Default to prompt for backward compatibility

            // Add task-specific guidance based on node type
            $prompt .= "TASK GUIDELINES:\n";
            $prompt .= "- Execute the instruction above using the provided Data and Context.\n";

            if ($nodeType === 'logic') {
                // Logic nodes: Analysis and processing instructions
                $prompt .= "- You are a 'Logic' node - perform ANALYSIS, not story writing.\n";
                $prompt .= "- Analyze the story context, extract insights, evaluate elements, or provide critiques.\n";
                $prompt .= "- DO NOT write story prose or continue the narrative.\n";
                $prompt .= "- Return analytical insights, evaluations, or processed information.\n";
                $prompt .= "- Examples: 'The pacing is too fast in Chapter 5', 'Character motivations are unclear', 'The emotional impact is strong but could be enhanced by...'\n";
                $prompt .= "- Return ONLY the result of your specific node's task.\n";
                $prompt .= "- Maintain consistency with the story context and any style guidelines provided.\n";
                $prompt .= "- CRITICAL: DO NOT rewrite, repeat, or paraphrase the story context text.\n";
                $prompt .= "- CRITICAL: Output ONLY analytical content - no story prose, no meta-commentary.\n";
            } else {
                // Prompt nodes: Story writing instructions
                $prompt .= "- You are a 'Prompt' node - generate the actual story text requested.\n";
                $prompt .= "- Return ONLY the result of your specific node's task.\n";
                $prompt .= "- Maintain consistency with the story context and any style guidelines provided.\n";
                $prompt .= "- CRITICAL: DO NOT rewrite, repeat, or paraphrase the story context text.\n";
                $prompt .= "- CRITICAL: If continuing from existing story context, begin your generation immediately after the last word - do not repeat any sentences.\n";
                $prompt .= "- CRITICAL: Output ONLY new content that continues or fulfills the instruction - no meta-commentary or summaries.\n";
                $prompt .= "- CRITICAL: The story context above shows what has already been written. Your job is to CONTINUE from where it ends, not to repeat it.\n";
                $prompt .= "- CRITICAL: If the story context ends with a complete sentence, start your generation with the next sentence. If it ends mid-sentence, continue from that exact point.\n";
                $prompt .= "- CRITICAL: Preserve ALL existing content - your output will be appended to it, not replace it.\n";
            }

            // Call Python service with proper format
            $model = $validated['ai_model'] ?? 'gemini-2.5-flash';
            $provider = str_starts_with($model, 'gemini') ? 'gemini' : 'openai';

            // Build prompt_config for StoryHandler - includes author profile for style benefits
            $promptConfig = [
                'current_preset' => $validated['settings']['currentPreset'] ?? 'story-telling',
                'context' => $validated['settings']['memory'] ?? '',
                'genre' => $validated['settings']['storyGenre'] ?? '',
                'tone' => $validated['settings']['storyTone'] ?? '',
                'pov' => $validated['settings']['storyPov'] ?? '',
                'author_profile' => $validated['author_profile'] ?? null,
            ];

            // Build complete generation_config with all required fields
            // StoryHandler will build instruction from prompt_config, but our custom prompt
            // contains the node-specific instructions and will be used as the main content
            $generationConfig = array_merge([
                'temperature' => $validated['settings']['temperature'] ?? 0.7,
                'repetition_penalty' => $validated['settings']['repetitionPenalty'] ?? 0.0,
                'min_output_tokens' => $validated['settings']['minOutputToken'] ?? 50,
                'max_output_tokens' => $validated['settings']['outputLength'] ?? 1000,
                'nucleus_sampling' => $validated['settings']['topP'] ?? 1.0,
                'tail_free_sampling' => $validated['settings']['tailFree'] ?? 1.0,
                'top_a' => $validated['settings']['topA'] ?? 0.0,
                'top_k' => $validated['settings']['topK'] ?? 0.0,
                'phrase_bias' => $validated['settings']['phraseBias'] ?? null,
                'banned_tokens' => $validated['settings']['bannedPhrases'] ?? null,
                'stop_sequences' => $validated['settings']['stopSequences'] ?? null,
                'thinking_budget' => $validated['settings']['thinkingBudget'] ?? null,
                'include_thinking' => $validated['settings']['includeThinking'] ?? false,
                'stream' => false,
            ], $validated['settings'] ?? []);

            $response = Http::timeout(60)
                ->post($this->getPythonServiceUrl().'/api/generate', [
                    'usecase' => 'story',
                    'provider' => $provider,
                    'model' => $model,
                    'prompt' => $prompt, // Our custom prompt with node instructions + story context
                    'prompt_config' => $promptConfig, // Author profile + settings for StoryHandler's instruction builder
                    'generation_config' => $generationConfig,
                    'caller' => [
                        'user_id' => (string) auth()->id(),
                        'workspace_id' => $workspace_id,
                        'project_id' => $project_id,
                        'session_id' => 'chain-builder',
                        'api_keys' => (object) [],
                    ],
                ]);

            if ($response->successful()) {
                $result = $response->json();

                return response()->json([
                    'success' => true,
                    'result' => $result['text'] ?? $result['content'] ?? '',
                ]);
            } else {
                Log::error('Python service error executing node', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);

                return response()->json([
                    'error' => 'Failed to execute node',
                    'details' => $response->json(),
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception executing node', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to execute node: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Generate graph layout from user goal
     */
    public function generateGraphLayout(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'user_goal' => 'required|string',
            'story_context' => 'string',
            'entities' => 'array',
            'mode' => 'required|in:final-only,sequence',
            'ai_model' => 'required|string',
            'existing_nodes' => 'nullable|array',  // Current nodes on canvas
            'existing_edges' => 'nullable|array',  // Current edges on canvas
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $storyContext = $validated['story_context'] ?? $this->getStoryContext($project_id);

            // Limit story context to 500k chars for auto-build (to save tokens)
            if (strlen($storyContext) > 500000) {
                $storyContext = '...'.substr($storyContext, -500000);
            }

            $entities = $validated['entities'] ?? [];

            // Format entities
            $entitiesText = '';
            if (! empty($entities)) {
                $entityParts = [];
                foreach ($entities as $entity) {
                    $entityParts[] = "--- {$entity['name']} ({$entity['type']}) ---\n".
                        json_encode($entity['properties'] ?? [], JSON_PRETTY_PRINT);
                }
                $entitiesText = implode("\n\n", $entityParts);
            }

            $modeInstruction = $validated['mode'] === 'sequence'
                ? 'DESIGN FOR SEQUENCE MODE: Connect prompt nodes in a LINEAR chain (A -> B -> C) where each node writes a subsequent part of the story.'
                : 'DESIGN FOR FINAL-ONLY MODE: Design a flow where context and logic nodes feed into a FINAL prompt node. The intermediate nodes should process data, not write story segments.';

            $prompt = "You are an AI Graph Architect.\n";
            $prompt .= "Create a Logic Graph (Workflow) for a story writing app based on the user's goal.\n\n";
            $prompt .= "STORY CONTEXT (The story so far):\n\"\"\"\n{$storyContext}\n\"\"\"\n\n";
            $prompt .= "AVAILABLE RECORDS/ENTITIES:\n\"\"\"\n{$entitiesText}\n\"\"\"\n\n";

            // Include existing graph state if present (for building upon existing nodes)
            $existingNodes = $validated['existing_nodes'] ?? [];
            $existingEdges = $validated['existing_edges'] ?? [];

            if (! empty($existingNodes)) {
                $prompt .= "EXISTING GRAPH (build upon this):\n";
                $prompt .= 'Current Nodes: '.json_encode($existingNodes, JSON_PRETTY_PRINT)."\n";
                $prompt .= 'Current Edges: '.json_encode($existingEdges, JSON_PRETTY_PRINT)."\n";
                $prompt .= "Generate NEW nodes that connect to these existing nodes where appropriate.\n";
                $prompt .= "Do NOT recreate the existing nodes - only add new ones based on the user's goal.\n\n";
            }

            $prompt .= "USER GOAL: \"{$validated['user_goal']}\"\n\n";
            $prompt .= "OPTIMIZATION STRATEGY:\n{$modeInstruction}\n\n";
            $prompt .= "Available Node Types:\n";
            $prompt .= "- 'prompt': Contains INSTRUCTIONS for what should happen in a scene or passage. These are GUIDANCE for the AI, NOT the actual story text. Examples: 'Write a scene where Yurak faces his inner demons' or 'Continue the story showing Ericon's growing despair'. The actual story text is generated when the node is executed.\n";
            $prompt .= "- 'context': Static background info (Use Records/Entities if they match!). Contains factual information, character details, world-building elements, etc.\n";
            $prompt .= "- 'logic': Performs checks, critiques, or brainstorming (does not write final story text). Contains analytical instructions like 'Analyze the emotional impact' or 'Determine pacing requirements'.\n\n";
            $prompt .= "CRITICAL RULES FOR PROMPT NODES:\n";
            $prompt .= "- Prompt node 'content' field must contain INSTRUCTIONS/GUIDANCE, not actual prose.\n";
            $prompt .= "- Use imperative language: 'Write...', 'Continue...', 'Describe...', 'Show...'\n";
            $prompt .= "- Be specific about what should happen: 'Write a scene where [character] faces [challenge]'\n";
            $prompt .= "- Do NOT write actual story text in the prompt node content.\n";
            $prompt .= "- The story text will be generated later when the node is executed.\n\n";
            $prompt .= "Return a JSON object with 'nodes' and 'edges'.\n";
            $prompt .= "- Assign strict string IDs (e.g., 'n1', 'n2').\n";
            $prompt .= "- Position nodes visually in a logical flow (Top to Bottom). Start at x:0, y:0 and space them out by y+250.\n";
            $prompt .= "- Connect them logically.\n";
            $prompt .= "- IMPORTANT: If the user goal involves an entity from Records, create a 'context' node pre-filled with that entity's data.\n";
            $prompt .= "- CRITICAL RULE: Create separate 'context' nodes for each specific entity involved. Do NOT create a single 'Records Context' lump node.\n\n";
            $prompt .= "Example Structure:\n";
            $prompt .= "{\n";
            $prompt .= '  "nodes": [\n';
            $prompt .= '    { "id": "n1", "type": "context", "position": {"x": 0, "y": 0}, "data": { "label": "Character Bio", "content": "Yurak is a barbarian warrior..." } },\n';
            $prompt .= '    { "id": "n2", "type": "prompt", "position": {"x": 0, "y": 200}, "data": { "label": "Scene 1: The Trial Begins", "content": "Write a scene where Yurak enters the trial chamber and faces the psychological torment of the winds. Show his internal struggle with his past failures and the weight of his greaves." } },\n';
            $prompt .= '    { "id": "n3", "type": "prompt", "position": {"x": 0, "y": 450}, "data": { "label": "Scene 2: Ericon\'s Despair", "content": "Continue the story from Scene 1, focusing on Ericon\'s perspective. Show how the abyss affects him differently, revealing the futility he sees in their mission." } }\n';
            $prompt .= "  ],\n";
            $prompt .= '  "edges": [ { "id": "e1", "source": "n1", "target": "n2" }, { "id": "e2", "source": "n2", "target": "n3" } ]\n';
            $prompt .= "}\n\n";
            $prompt .= 'Return ONLY the JSON.';

            // Call Python service with proper format
            $model = $validated['ai_model'];
            $provider = str_starts_with($model, 'gemini') ? 'gemini' : 'openai';

            // Log model selection for debugging
            Log::info('Generate graph layout model', [
                'requested_model' => $validated['ai_model'],
                'final_model' => $model,
                'provider' => $provider,
            ]);

            // Build prompt_config for StoryHandler
            $promptConfig = [
                'current_preset' => 'story-telling',
                'context' => '',
                'genre' => '',
                'tone' => '',
                'pov' => '',
                'author_profile' => null,
            ];

            // Build complete generation_config with all required fields
            // Increased max_output_tokens for complex graph layouts (graphs can be large with lots of context)
            $generationConfig = [
                'temperature' => 0.3,
                'repetition_penalty' => 0.0,
                'min_output_tokens' => 50,
                'max_output_tokens' => 8000, // Increased from 4000 to handle complex graphs
                'nucleus_sampling' => 1.0,
                'tail_free_sampling' => 1.0,
                'top_a' => 0.0,
                'top_k' => 0.0,
                'phrase_bias' => null,
                'banned_tokens' => null,
                'stop_sequences' => null,
                'thinking_budget' => null,
                'include_thinking' => false,
                'stream' => false,
            ];

            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/generate', [
                    'usecase' => 'graph-layout',  // Use graph-layout usecase to bypass conversation history
                    'provider' => $provider,
                    'model' => $model,
                    'prompt' => $prompt."\n\nIMPORTANT: Return ONLY valid JSON. Do not include markdown code blocks or explanations. Ensure the JSON is complete and properly closed.",
                    'prompt_config' => $promptConfig,
                    'generation_config' => $generationConfig,
                    'caller' => [
                        'user_id' => (string) auth()->id(),
                        'workspace_id' => $workspace_id,
                        'project_id' => $project_id,
                        'session_id' => 'chain-builder-auto-build',
                        'api_keys' => (object) [],
                    ],
                ]);

            if ($response->successful()) {
                $result = $response->json();
                $jsonText = $result['text'] ?? $result['content'] ?? '';

                if (empty($jsonText)) {
                    throw new \Exception('Empty response from Python service');
                }

                // Parse JSON (handle markdown code blocks)
                $jsonText = preg_replace('/```json\s*/', '', $jsonText);
                $jsonText = preg_replace('/```\s*/', '', $jsonText);
                $jsonText = trim($jsonText);

                // Try to extract JSON if wrapped in text - use a more robust approach
                // First, try to find the JSON object boundaries more accurately
                $firstBrace = strpos($jsonText, '{');
                if ($firstBrace !== false) {
                    // Find the matching closing brace by counting braces
                    $braceCount = 0;
                    $lastBrace = $firstBrace;
                    for ($i = $firstBrace; $i < strlen($jsonText); $i++) {
                        if ($jsonText[$i] === '{') {
                            $braceCount++;
                        } elseif ($jsonText[$i] === '}') {
                            $braceCount--;
                            if ($braceCount === 0) {
                                $lastBrace = $i;
                                break;
                            }
                        }
                    }
                    if ($braceCount === 0) {
                        $jsonText = substr($jsonText, $firstBrace, $lastBrace - $firstBrace + 1);
                    }
                }

                $graphData = json_decode($jsonText, true);

                if (json_last_error() !== JSON_ERROR_NONE) {
                    $errorMsg = json_last_error_msg();
                    // Check if JSON appears truncated (ends abruptly)
                    $isTruncated = ! str_ends_with(trim($jsonText), '}') && str_contains($jsonText, '{');
                    $truncatedHint = $isTruncated ? ' (Response appears truncated - may need more tokens)' : '';

                    Log::error('JSON decode error in generateGraphLayout', [
                        'error' => $errorMsg,
                        'json_length' => strlen($jsonText),
                        'appears_truncated' => $isTruncated,
                        'json_preview' => substr($jsonText, 0, 1000),
                        'json_end' => substr($jsonText, -200),
                    ]);
                    throw new \Exception('Invalid JSON response: '.$errorMsg.$truncatedHint.' (Response length: '.strlen($jsonText).' chars)');
                }

                // Check if decoded data is null (can happen with malformed JSON)
                if ($graphData === null) {
                    $isTruncated = ! str_ends_with(trim($jsonText), '}') && str_contains($jsonText, '{');
                    Log::error('JSON decode returned null in generateGraphLayout', [
                        'json_length' => strlen($jsonText),
                        'appears_truncated' => $isTruncated,
                        'json_preview' => substr($jsonText, 0, 1000),
                        'json_end' => substr($jsonText, -200),
                    ]);
                    throw new \Exception('Invalid JSON response: Decoded data is null'.($isTruncated ? ' (Response appears truncated - may need more tokens)' : ''));
                }

                if (! isset($graphData['nodes']) || ! is_array($graphData['nodes'])) {
                    Log::error('Invalid graph layout structure', [
                        'has_nodes' => isset($graphData['nodes']),
                        'nodes_type' => gettype($graphData['nodes'] ?? null),
                        'data_keys' => array_keys($graphData ?? []),
                    ]);
                    throw new \Exception('Invalid graph layout response: missing or invalid nodes array');
                }

                return response()->json([
                    'success' => true,
                    'nodes' => $graphData['nodes'] ?? [],
                    'edges' => $graphData['edges'] ?? [],
                ]);
            } else {
                $errorBody = $response->body();
                $errorData = $response->json();

                Log::error('Python service error generating graph layout', [
                    'status' => $response->status(),
                    'body' => $errorBody,
                    'error_data' => $errorData,
                ]);

                $errorMessage = $errorData['error'] ?? $errorData['message'] ?? 'Failed to generate graph layout';

                return response()->json([
                    'error' => $errorMessage,
                    'details' => $errorData,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception generating graph layout', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to generate graph layout: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Generate instruction using Magic Wand
     */
    public function generateInstruction(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'seed' => 'required|string',
            'inputs' => 'array',
            'story_context' => 'string',
            'ai_model' => 'required|string',
            'node_type' => 'nullable|in:prompt,logic', // Optional: specify if this is for a prompt or logic node
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $storyContext = $validated['story_context'] ?? $this->getStoryContext($project_id);

            $inputsText = '';
            if (! empty($validated['inputs'])) {
                $inputParts = [];
                foreach ($validated['inputs'] as $input) {
                    $inputParts[] = "SOURCE: {$input['label']}\nCONTENT: {$input['text']}";
                }
                $inputsText = implode("\n\n", $inputParts);
            }

            // Limit story context to last 20k chars for magic wand (to save tokens)
            $limitedStoryContext = strlen($storyContext) > 20000 ? '...'.substr($storyContext, -20000) : $storyContext;

            $nodeType = $validated['node_type'] ?? 'prompt'; // Default to prompt for backward compatibility

            if ($nodeType === 'logic') {
                // Logic node: Generate analytical/processing instructions
                $prompt = "You are an \"Analysis Director AI\". Your job is to write precise, effective Logic/Analysis Instructions for another AI to execute.\n\n";
                $prompt .= "USER GOAL (Seed Idea): \"{$validated['seed']}\"\n\n";

                if ($inputsText) {
                    $prompt .= "AVAILABLE CONTEXT/RESOURCES:\n{$inputsText}\n\n";
                } else {
                    $prompt .= "AVAILABLE CONTEXT/RESOURCES: No upstream inputs.\n\n";
                }

                $prompt .= "STORY CONTEXT:\n{$limitedStoryContext}\n\n";
                $prompt .= "Based on the user's goal and the available resources, write a robust paragraph of ANALYSIS or LOGIC instructions.\n";
                $prompt .= "Logic nodes perform analytical tasks like:\n";
                $prompt .= "- Analyzing emotional impact, pacing, or narrative structure\n";
                $prompt .= "- Determining character motivations or relationships\n";
                $prompt .= "- Evaluating scene effectiveness or suggesting improvements\n";
                $prompt .= "- Extracting specific information or patterns\n";
                $prompt .= "- Brainstorming or critiquing story elements\n\n";
                $prompt .= "Tell the AI exactly what analysis to perform, what to examine, and what insights to provide.\n";
                $prompt .= "Do NOT write story text - only analytical instructions.\n\n";
                $prompt .= 'Return ONLY the instruction text.';
            } else {
                // Prompt node: Generate story writing instructions
                $prompt = "You are a \"Director AI\". Your job is to write a precise, effective Prompt Instruction for another AI to execute.\n\n";
                $prompt .= "USER GOAL (Seed Idea): \"{$validated['seed']}\"\n\n";

                if ($inputsText) {
                    $prompt .= "AVAILABLE CONTEXT/RESOURCES:\n{$inputsText}\n\n";
                } else {
                    $prompt .= "AVAILABLE CONTEXT/RESOURCES: No upstream inputs.\n\n";
                }

                $prompt .= "STORY CONTEXT:\n{$limitedStoryContext}\n\n";
                $prompt .= "Based on the user's goal and the available resources (Characters, Locations, Logic), write a robust paragraph of instructions.\n";
                $prompt .= "Tell the AI exactly what to write, how to incorporate the characters provided, and how to advance the plot.\n\n";
                $prompt .= 'Return ONLY the instruction text.';
            }

            $model = $validated['ai_model'];
            $provider = str_starts_with($model, 'gemini') ? 'gemini' : 'openai';

            // Build prompt_config for StoryHandler
            $promptConfig = [
                'current_preset' => 'story-telling',
                'context' => '',
                'genre' => '',
                'tone' => '',
                'pov' => '',
                'author_profile' => null,
            ];

            // Build complete generation_config with all required fields
            $generationConfig = [
                'temperature' => 0.7,
                'repetition_penalty' => 0.0,
                'min_output_tokens' => 50,
                'max_output_tokens' => 2000,
                'nucleus_sampling' => 1.0,
                'tail_free_sampling' => 1.0,
                'top_a' => 0.0,
                'top_k' => 0.0,
                'phrase_bias' => null,
                'banned_tokens' => null,
                'stop_sequences' => null,
                'thinking_budget' => null,
                'include_thinking' => false,
                'stream' => false,
            ];

            $response = Http::timeout(60)
                ->post($this->getPythonServiceUrl().'/api/generate', [
                    'usecase' => 'story',
                    'provider' => $provider,
                    'model' => $model,
                    'prompt' => $prompt,
                    'prompt_config' => $promptConfig,
                    'generation_config' => $generationConfig,
                    'caller' => [
                        'user_id' => (string) auth()->id(),
                        'workspace_id' => $workspace_id,
                        'project_id' => $project_id,
                        'session_id' => 'chain-builder-wand',
                        'api_keys' => (object) [],
                    ],
                ]);

            if ($response->successful()) {
                $result = $response->json();
                $instruction = $result['text'] ?? $result['content'] ?? '';

                // Clean up instruction (remove markdown code blocks if present)
                $instruction = preg_replace('/```.*?\n/', '', $instruction);
                $instruction = preg_replace('/```/', '', $instruction);
                $instruction = trim($instruction);

                // If empty, fallback to seed
                if (empty($instruction)) {
                    $instruction = $validated['seed'];
                }

                return response()->json([
                    'success' => true,
                    'instruction' => $instruction,
                ]);
            } else {
                $errorBody = $response->body();
                $errorData = $response->json();

                Log::error('Python service error generating instruction', [
                    'status' => $response->status(),
                    'body' => $errorBody,
                    'error_data' => $errorData,
                ]);

                $errorMessage = $errorData['error'] ?? $errorData['message'] ?? 'Failed to generate instruction';

                return response()->json([
                    'error' => $errorMessage,
                    'details' => $errorData,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception generating instruction', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to generate instruction: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Refine selected nodes
     */
    public function refineSelection(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'selected_nodes' => 'required|array',
            'selected_edges' => 'array',
            'instruction' => 'required|string',
            'story_context' => 'string',
            'ai_model' => 'required|string',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->first();

        if (! $project) {
            return response()->json(['error' => 'Project not found'], 404);
        }

        try {
            $storyContext = $validated['story_context'] ?? $this->getStoryContext($project_id);

            // Limit story context to 500k chars for refine (to save tokens)
            if (strlen($storyContext) > 500000) {
                $storyContext = '...'.substr($storyContext, -500000);
            }

            $prompt = "You are an expert Story Logic Engineer.\n";
            $prompt .= "You are provided with a SUBSET of a node graph.\n\n";
            $prompt .= "STORY CONTEXT:\n\"\"\"\n{$storyContext}\n\"\"\"\n\n";
            $prompt .= "YOUR TASK: Refine, Expand, or Modify this subset based on the user's instruction.\n\n";
            $prompt .= "USER INSTRUCTION: \"{$validated['instruction']}\"\n\n";
            $prompt .= "CURRENT SUBSET JSON:\n".json_encode([
                'nodes' => $validated['selected_nodes'],
                'edges' => $validated['selected_edges'] ?? [],
            ], JSON_PRETTY_PRINT)."\n\n";
            $prompt .= "RULES:\n";
            $prompt .= "1. Return a NEW JSON object with 'nodes' and 'edges' representing the improved flow.\n";
            $prompt .= "2. You can add new nodes (e.g., breaking a prompt into 3 steps), remove nodes, or change node content.\n";
            $prompt .= "3. Use specific names/details from the Story Context in your new nodes.\n";
            $prompt .= "4. Use unique IDs for new nodes (e.g., 'new_1', 'new_2').\n";
            $prompt .= "5. Keep the general position coordinates similar but adjust spacing so they don't overlap.\n\n";
            $prompt .= 'Return ONLY the JSON.';

            $model = $validated['ai_model'];
            $provider = str_starts_with($model, 'gemini') ? 'gemini' : 'openai';

            // Build prompt_config for StoryHandler
            $promptConfig = [
                'current_preset' => 'story-telling',
                'context' => '',
                'genre' => '',
                'tone' => '',
                'pov' => '',
                'author_profile' => null,
            ];

            // Build complete generation_config with all required fields
            $generationConfig = [
                'temperature' => 0.3,
                'repetition_penalty' => 0.0,
                'min_output_tokens' => 50,
                'max_output_tokens' => 4000,
                'nucleus_sampling' => 1.0,
                'tail_free_sampling' => 1.0,
                'top_a' => 0.0,
                'top_k' => 0.0,
                'phrase_bias' => null,
                'banned_tokens' => null,
                'stop_sequences' => null,
                'thinking_budget' => null,
                'include_thinking' => false,
                'stream' => false,
            ];

            $response = Http::timeout(120)
                ->post($this->getPythonServiceUrl().'/api/generate', [
                    'usecase' => 'story',
                    'provider' => $provider,
                    'model' => $model,
                    'prompt' => $prompt."\n\nIMPORTANT: Return ONLY valid JSON. Do not include markdown code blocks or explanations.",
                    'prompt_config' => $promptConfig,
                    'generation_config' => $generationConfig,
                    'caller' => [
                        'user_id' => (string) auth()->id(),
                        'workspace_id' => $workspace_id,
                        'project_id' => $project_id,
                        'session_id' => 'chain-builder-refine',
                        'api_keys' => (object) [],
                    ],
                ]);

            if ($response->successful()) {
                $result = $response->json();
                $jsonText = $result['text'] ?? $result['content'] ?? '';

                if (empty($jsonText)) {
                    throw new \Exception('Empty response from Python service');
                }

                // Parse JSON (handle markdown code blocks)
                $jsonText = preg_replace('/```json\s*/', '', $jsonText);
                $jsonText = preg_replace('/```\s*/', '', $jsonText);
                $jsonText = trim($jsonText);

                // Try to extract JSON if wrapped in text
                if (preg_match('/\{.*\}/s', $jsonText, $matches)) {
                    $jsonText = $matches[0];
                }

                $refinedData = json_decode($jsonText, true);

                if (json_last_error() !== JSON_ERROR_NONE) {
                    Log::error('JSON decode error in refineSelection', [
                        'error' => json_last_error_msg(),
                        'json_preview' => substr($jsonText, 0, 500),
                    ]);
                    throw new \Exception('Invalid JSON response: '.json_last_error_msg());
                }

                if (! $refinedData || ! isset($refinedData['nodes']) || ! is_array($refinedData['nodes'])) {
                    Log::error('Invalid refined graph structure', [
                        'has_nodes' => isset($refinedData['nodes']),
                        'nodes_type' => gettype($refinedData['nodes'] ?? null),
                        'data_keys' => array_keys($refinedData ?? []),
                    ]);
                    throw new \Exception('Invalid refined graph response: missing or invalid nodes array');
                }

                return response()->json([
                    'success' => true,
                    'nodes' => $refinedData['nodes'] ?? [],
                    'edges' => $refinedData['edges'] ?? [],
                ]);
            } else {
                $errorBody = $response->body();
                $errorData = $response->json();

                Log::error('Python service error refining selection', [
                    'status' => $response->status(),
                    'body' => $errorBody,
                    'error_data' => $errorData,
                ]);

                $errorMessage = $errorData['error'] ?? $errorData['message'] ?? 'Failed to refine selection';

                return response()->json([
                    'error' => $errorMessage,
                    'details' => $errorData,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception refining selection', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to refine selection: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Apply chain builder result to story
     * Saves content server-side before redirect to avoid URL parameter limitations
     */
    public function applyToStory(Request $request, string $workspace_id, string $project_id)
    {
        $validated = $request->validate([
            'result_text' => 'required|string',
            'chapter_order' => 'nullable|integer',
        ]);

        $project = Projects::where('id', $project_id)
            ->where('workspace_id', $workspace_id)
            ->firstOrFail();

        try {
            $projectContent = ProjectContent::where('project_id', $project_id)->firstOrFail();
            $chapters = $projectContent->content ?? [];

            if (empty($chapters)) {
                return response()->json(['error' => 'No chapters found'], 400);
            }

            // Find target chapter (default to last by order)
            $targetOrder = $validated['chapter_order'] ?? null;
            if ($targetOrder === null) {
                $maxOrder = 0;
                foreach ($chapters as $chapter) {
                    if (($chapter['order'] ?? 0) > $maxOrder) {
                        $maxOrder = $chapter['order'];
                    }
                }
                $targetOrder = $maxOrder;
            }

            // Update target chapter
            $chapterFound = false;
            $updatedContent = '';

            foreach ($chapters as &$chapter) {
                if (($chapter['order'] ?? null) === $targetOrder) {
                    $existingContent = $chapter['content'] ?? '';

                    // Handle based on content format
                    if ($this->isLexicalJson($existingContent)) {
                        // Append to Lexical JSON structure properly
                        $chapter['content'] = $this->appendToLexicalJson(
                            $existingContent,
                            $validated['result_text'],
                            'ai'  // Mark as AI-generated for color coding
                        );
                    } else {
                        // Plain text: simple concatenation
                        $separator = $this->determineSeparator($existingContent, $validated['result_text']);
                        $chapter['content'] = $existingContent.$separator.$validated['result_text'];
                    }

                    $updatedContent = $chapter['content'];
                    $chapterFound = true;
                    break;
                }
            }
            unset($chapter);

            if (! $chapterFound) {
                return response()->json(['error' => 'Chapter not found'], 404);
            }

            // Save to database
            $projectContent->content = $chapters;
            $projectContent->save();

            // Create version control node
            try {
                $this->versionControl->createNode(
                    $project_id,
                    $targetOrder,
                    $updatedContent,
                    [],
                    null,
                    null
                );
            } catch (\Exception $e) {
                Log::warning('Version node creation failed', ['error' => $e->getMessage()]);
            }

            Log::info('Applied chain builder result', [
                'project_id' => $project_id,
                'chapter_order' => $targetOrder,
                'content_length' => strlen($updatedContent),
                'format' => $this->isLexicalJson($updatedContent) ? 'lexical' : 'plain',
            ]);

            return response()->json([
                'success' => true,
                'chapter_order' => $targetOrder,
            ]);

        } catch (\Exception $e) {
            Log::error('Apply to story failed', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed: '.$e->getMessage(),
            ], 500);
        }
    }

    /**
     * Determine the appropriate separator between existing content and new content
     */
    private function determineSeparator(string $existingContent, string $newContent): string
    {
        // If existing content is empty, no separator needed
        if (empty(trim($existingContent))) {
            return '';
        }

        // If existing content ends with newlines, just add one more
        if (preg_match('/\n{2,}$/', $existingContent)) {
            return '';
        }
        if (preg_match('/\n$/', $existingContent)) {
            return "\n";
        }

        // Otherwise, add double newline for paragraph separation
        return "\n\n";
    }

    /**
     * Check if content is Lexical JSON format
     */
    private function isLexicalJson(string $content): bool
    {
        if (empty($content) || ! str_starts_with(trim($content), '{')) {
            return false;
        }

        try {
            $parsed = json_decode($content, true);

            return isset($parsed['root']['type']) && $parsed['root']['type'] === 'root';
        } catch (\Exception $e) {
            return false;
        }
    }

    /**
     * Create a Lexical origin-text node
     */
    private function createOriginTextNode(string $text, string $origin = 'ai'): array
    {
        return [
            'type' => 'origin-text',
            'version' => 1,
            'text' => $text,
            'origin' => $origin,
            'detail' => 0,
            'format' => 0,
            'mode' => 'normal',
            'style' => '',
        ];
    }

    /**
     * Append text to Lexical JSON content
     *
     * NOTE: This matches StreamingPlugin behavior where each newline creates
     * a new paragraph (see StreamingPlugin.tsx lines 220-233).
     */
    private function appendToLexicalJson(string $existingContent, string $newText, string $origin = 'ai'): string
    {
        $doc = json_decode($existingContent, true);

        if (! $doc || ! isset($doc['root']['children'])) {
            // Fallback: create fresh document
            $doc = [
                'root' => [
                    'type' => 'root',
                    'version' => 1,
                    'direction' => 'ltr',
                    'format' => '',
                    'indent' => 0,
                    'children' => [],
                ],
            ];
        }

        // Add blank paragraph for spacing if there's existing content
        if (! empty($doc['root']['children'])) {
            $doc['root']['children'][] = [
                'type' => 'paragraph',
                'version' => 1,
                'direction' => null,
                'format' => '',
                'indent' => 0,
                'textStyle' => '',
                'textFormat' => 0,
                'children' => [],
            ];
        }

        // Split on SINGLE newlines (matching StreamingPlugin behavior)
        // Each line becomes its own paragraph
        $lines = explode("\n", $newText);

        foreach ($lines as $line) {
            // Create paragraph for each line (empty lines = empty paragraphs for spacing)
            $children = [];
            $trimmed = trim($line);
            if (! empty($trimmed)) {
                $children[] = $this->createOriginTextNode($trimmed, $origin);
            }

            $doc['root']['children'][] = [
                'type' => 'paragraph',
                'version' => 1,
                'direction' => 'ltr',
                'format' => '',
                'indent' => 0,
                'textStyle' => '',
                'textFormat' => 0,
                'children' => $children,
            ];
        }

        return json_encode($doc, JSON_UNESCAPED_UNICODE);
    }

    /**
     * Enhance Auto-Build prompt using story context
     */
    public function enhanceAutoBuildPrompt(Request $request, string $workspace_id, string $project_id)
    {
        try {
            $validated = $request->validate([
                'text' => 'required|string|min:1|max:10000',
                'story_context' => 'nullable|string|max:500000',
                'model' => 'nullable|string',
            ]);

            $project = Projects::where('id', $project_id)
                ->where('workspace_id', $workspace_id)
                ->firstOrFail();

            // Get model from request, then project settings, then default
            $model = $validated['model']
                ?? ($project->settings && isset($project->settings['aiModel']) ? $project->settings['aiModel'] : null)
                ?? 'gemini-2.5-flash'; // Default to 2.5 flash
            $provider = str_starts_with($model, 'gemini') ? 'gemini' : 'openai';

            // Log for debugging
            Log::info('Auto-Build enhancement model selection', [
                'requested_model' => $validated['model'] ?? 'not provided',
                'project_settings_aiModel' => $project->settings['aiModel'] ?? 'not set',
                'final_model' => $model,
            ]);

            // Create a prompt that helps enhance the user's goal into a better pipeline description
            $storyContext = $validated['story_context'] ?? '';
            $userGoal = $validated['text'];

            // Limit story context to 100k chars for this enhancement
            if (strlen($storyContext) > 100000) {
                $storyContext = '...'.substr($storyContext, -100000);
            }

            $enhancementPrompt = "You are a technical assistant helping create a WORKFLOW DESCRIPTION for an AI story generation pipeline builder.\n\n";
            $enhancementPrompt .= "STORY CONTEXT (for reference only - DO NOT write story text):\n";
            $enhancementPrompt .= $storyContext ? "---\n{$storyContext}\n---\n\n" : "(No story context provided)\n\n";
            $enhancementPrompt .= "USER'S GOAL:\n";
            $enhancementPrompt .= "{$userGoal}\n\n";
            $enhancementPrompt .= "CRITICAL INSTRUCTIONS:\n";
            $enhancementPrompt .= "1. Your task is to ENHANCE the user's goal into a detailed WORKFLOW DESCRIPTION that describes what pipeline should be built\n";
            $enhancementPrompt .= "2. DO NOT write story passages, narrative text, or dialogue\n";
            $enhancementPrompt .= "3. DO NOT continue the story or write what happens next\n";
            $enhancementPrompt .= "4. Instead, describe WHAT NODES AND WORKFLOW should be created (e.g., 'Create context nodes for character states, add logic nodes for emotional analysis, build prompt nodes that...')\n";
            $enhancementPrompt .= "5. If the user's goal is vague (like 'yurak is breaking apart'), expand it into a clear workflow description:\n";
            $enhancementPrompt .= "   - What context nodes are needed? (character states, settings, etc.)\n";
            $enhancementPrompt .= "   - What logic nodes should analyze? (emotional beats, internal conflicts, etc.)\n";
            $enhancementPrompt .= "   - What should the final prompt node generate? (the scene description, continuation, etc.)\n";
            $enhancementPrompt .= "6. Use story context ONLY to understand what details to include in the workflow description\n";
            $enhancementPrompt .= "7. Output ONLY the enhanced workflow description prompt - NO story text, NO narrative, NO dialogue\n\n";
            $enhancementPrompt .= "EXAMPLE:\n";
            $enhancementPrompt .= "Input: 'yurak is breaking apart'\n";
            $enhancementPrompt .= "Output: 'Create a workflow to depict Yurak's psychological breakdown. Include context nodes for his current transformed state, the greaves' influence, and Ericon's presence. Add logic nodes analyzing the internal conflict between his warrior persona and suppressed cowardice. The final prompt should generate a scene showing his mental fragmentation, physical manifestations of his breakdown, and the moment of recognition or collapse.'\n\n";
            $enhancementPrompt .= 'Enhanced workflow description:';

            $generationConfig = [
                'temperature' => 0.5, // Lower temperature for more focused output
                'repetition_penalty' => 0.0,
                'min_output_tokens' => 50,
                'max_output_tokens' => 2000,
                'nucleus_sampling' => 1.0,
                'tail_free_sampling' => 1.0,
                'top_a' => 0.0,
                'top_k' => 0.0,
                'phrase_bias' => null,
                'banned_tokens' => null,
                'stop_sequences' => null, // Removed stop sequences - they might be causing empty responses
                'thinking_budget' => null,
                'include_thinking' => false,
                'stream' => false,
            ];

            $response = Http::timeout(60)->post($this->getPythonServiceUrl().'/api/generate', [
                'usecase' => 'story', // Keep story usecase but with explicit instructions
                'provider' => $provider,
                'model' => $model,
                'prompt' => $enhancementPrompt,
                'prompt_config' => [
                    'current_preset' => 'story-telling', // Keep story preset
                    'context' => '',
                    'genre' => '',
                    'tone' => '',
                    'pov' => '',
                    'author_profile' => null,
                ],
                'generation_config' => $generationConfig,
                'caller' => [
                    'user_id' => (string) auth()->id(),
                    'workspace_id' => $workspace_id,
                    'project_id' => $project_id,
                    'session_id' => 'chain-builder-auto-build-enhance',
                    'api_keys' => (object) [],
                ],
            ]);

            if ($response->successful()) {
                $result = $response->json();

                // Check if the Python service itself reported failure
                if (isset($result['success']) && $result['success'] === false) {
                    $errorMessage = $result['error_message'] ?? $result['error'] ?? 'Python service reported failure';
                    Log::error('Auto-Build enhancement Python service failure', [
                        'error_message' => $errorMessage,
                        'full_result' => $result,
                    ]);

                    // Check for quota errors and provide helpful message
                    if (str_contains($errorMessage, '429') || str_contains($errorMessage, 'RESOURCE_EXHAUSTED') || str_contains($errorMessage, 'quota')) {
                        return response()->json([
                            'error' => 'API quota exceeded. Please wait a moment and try again, or check your API usage limits.',
                            'details' => $errorMessage,
                        ], 429);
                    }

                    return response()->json([
                        'error' => 'Enhancement failed: '.$errorMessage,
                        'details' => $errorMessage,
                    ], 500);
                }

                // Log the full response for debugging
                Log::info('Auto-Build enhancement response', [
                    'result_keys' => array_keys($result ?? []),
                    'has_text' => isset($result['text']),
                    'has_content' => isset($result['content']),
                    'text_preview' => substr($result['text'] ?? '', 0, 200),
                ]);

                $enhancedText = $result['text'] ?? $result['content'] ?? $result['output'] ?? '';

                if (empty($enhancedText)) {
                    Log::error('Auto-Build enhancement empty response', [
                        'full_result' => $result,
                        'response_status' => $response->status(),
                    ]);

                    return response()->json([
                        'error' => 'Empty response from Python service',
                        'details' => 'The service returned a successful response but no text content. Check logs for details.',
                    ], 500);
                }

                return response()->json([
                    'success' => true,
                    'enhanced_text' => trim($enhancedText),
                ]);
            } else {
                $errorBody = $response->body();
                $errorData = $response->json();
                $errorMessage = $errorData['error'] ?? $errorData['message'] ?? 'Failed to enhance prompt';

                Log::error('Auto-Build prompt enhancement error', [
                    'status' => $response->status(),
                    'error' => $errorMessage,
                ]);

                return response()->json([
                    'error' => $errorMessage,
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception enhancing auto-build prompt', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            return response()->json([
                'error' => 'Failed to enhance prompt: '.$e->getMessage(),
            ], 500);
        }
    }
}
