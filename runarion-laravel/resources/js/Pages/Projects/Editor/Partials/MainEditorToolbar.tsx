import { Button } from "@/Components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/Components/ui/dropdown-menu";
import {
    ChevronUp,
    RotateCcw,
    RotateCw,
    Send,
    Book,
    SlidersHorizontal,
    RefreshCw,
} from "lucide-react";
import { useEditor } from "../EditorContext";
import { router } from "@inertiajs/react";
import { useState } from "react";
import { toast } from "sonner";

export function EditorToolbar() {
    const { editorState } = useEditor();
    const [isGenerating, setIsGenerating] = useState(false);

    const handleSendClick = () => {
        // Map AI model to provider
        let provider = "";
        let model = "";
        
        if (editorState.aiModel.includes("chatgpt")) {
            provider = "openai";
            model = editorState.aiModel;
        } else if (editorState.aiModel.includes("gemini")) {
            provider = "gemini";
            model = editorState.aiModel;
        } else if (editorState.aiModel.includes("deepseek")) {
            provider = "deepseek";
            model = editorState.aiModel;
        } else {
            // Default to gemini if no model is selected
            provider = "gemini";
            model = "gemini-2.0-flash";
        }
        
        // Get content from the editor
        let prompt = document.getElementById("editor-content")?.textContent || "";
        
        // Format the data according to the target JSON structure
        const formattedData = {
            "usecase": "story",
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "instruction": "",
            "generation_config": {
                "temperature": editorState.temperature,
                "repetition_penalty": editorState.repetitionPenalty,
                "min_output_tokens": editorState.minOutputToken,
                "max_output_tokens": editorState.outputLength,
                "nucleus_sampling": editorState.topP,
                "tail_free_sampling": editorState.tailFree,
                "top_a": editorState.topA,
                "top_k": editorState.topK,
                "phrase_bias": editorState.phraseBias,
                "banned_tokens": editorState.bannedTokens,
                "stop_sequences": editorState.stopSequences
            },
            "prompt_config": {
                "author_profile": editorState.authorProfile,
                "context": editorState.memory,
                "genre": editorState.storyGenre,
                "tone": editorState.storyTone,
                "pov": editorState.storyPOV,
            },
            "caller": {
                "user_id": String(editorState.userId),
                "workspace_id": editorState.workspaceId,
                "project_id": editorState.projectId,
                "api_keys": editorState.apiKeys
            }
        };
        
        // Log the formatted data to the console
        console.log("Formatted Data:", formattedData);
        
        // Set generating state
        setIsGenerating(true);
        
        // Create a unique key for this workspace, project, and user
        const interactionKey = `editorInteracted_${editorState.workspaceId}_${editorState.projectId}_${editorState.userId}`;
        
        // Mark that the user has interacted with the editor for this specific workspace/project/user
        sessionStorage.setItem(interactionKey, 'true');
        
        // Make the API call using Inertia
        router.post(
            route('workspace.projects.editor.generate', {
                workspace_id: editorState.workspaceId,
                project_id: editorState.projectId
            }),
            formattedData,
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsGenerating(false);
                    // We'll handle the response in the Main.tsx component using useEffect
                },
                onError: (errors) => {
                    setIsGenerating(false);
                    console.error("Generation errors:", errors);
                    toast.error("Failed to generate story. Please try again.");
                }
            }
        );
    };

    return (
        <div
            className="
                bg-white rounded-lg shadow-sm border
                p-2
            "
        >
            <div className="flex items-center justify-between">
                {/* Left side - Controls */}
                <div className="flex items-center space-x-2">
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Book className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <SlidersHorizontal className="h-4 w-4" />
                    </Button>
                    {/* Auto dropdown - opens upward */}
                    <DropdownMenu>
                        <DropdownMenuTrigger>
                            <Button variant="ghost" size="sm" className="h-8">
                                Auto
                                <ChevronUp className="h-3 w-3" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start" side="top">
                            <DropdownMenuItem>Auto Mode On</DropdownMenuItem>
                            <DropdownMenuItem>Auto Mode Off</DropdownMenuItem>
                            <DropdownMenuItem>Custom Settings</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <span className="text-sm text-gray-500">0 Words</span>
                </div>

                {/* Right side - Action buttons */}
                <div className="flex items-center space-x-2">
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <RotateCcw className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <RotateCw className="h-4 w-4" />
                    </Button>
                    <DropdownMenu>
                        <DropdownMenuTrigger>
                            <span className="text-lg h-8 w-8 flex items-center justify-center rounded-md hover:bg-gray-100">
                                0
                            </span>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="center" side="top">
                            <DropdownMenuItem>v1</DropdownMenuItem>
                            <DropdownMenuItem>v2</DropdownMenuItem>
                            <DropdownMenuItem>v3</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button 
                        size="sm" 
                        onClick={handleSendClick}
                        disabled={isGenerating}
                    >
                        {isGenerating ? "Generating..." : "Send"}
                        {!isGenerating && <Send className="h-4 w-4 ml-1" />}
                    </Button>
                </div>
            </div>
        </div>
    );
}
