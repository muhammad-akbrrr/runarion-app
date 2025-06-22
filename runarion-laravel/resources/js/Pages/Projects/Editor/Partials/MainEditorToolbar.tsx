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
    Save,
} from "lucide-react";
import { useEditor } from "../EditorContext";
import { router } from "@inertiajs/react";
import { useState } from "react";

interface EditorToolbarProps {
    lastSaved: Date | null;
}

export function EditorToolbar({ 
    lastSaved 
}: EditorToolbarProps) {
    const { editorState } = useEditor();
    const [isGenerating, setIsGenerating] = useState(false);

    const handleSendClick = () => {
        let provider = "";
        let model = "";

        if (editorState.aiModel.includes("gpt")) {
            provider = "openai";
            model = editorState.aiModel;
        } else if (editorState.aiModel.includes("gemini")) {
            provider = "gemini";
            model = editorState.aiModel;
        } else if (editorState.aiModel.includes("deepseek")) {
            provider = "deepseek";
            model = editorState.aiModel;
        } else {
            provider = "gemini";
            model = "gemini-2.0-flash";
        }

        const prompt = document.getElementById("editor-content")?.textContent || "";

        const formattedData = {
            usecase: "story",
            provider,
            model,
            prompt,
            instruction: "",
            generation_config: {
                temperature: editorState.temperature,
                repetition_penalty: editorState.repetitionPenalty,
                min_output_tokens: editorState.minOutputToken,
                max_output_tokens: editorState.outputLength,
                nucleus_sampling: editorState.topP,
                tail_free_sampling: editorState.tailFree,
                top_a: editorState.topA,
                top_k: editorState.topK,
                phrase_bias: editorState.phraseBias,
                banned_tokens: editorState.bannedTokens,
                stop_sequences: editorState.stopSequences,
            },
            prompt_config: {
                author_profile: editorState.authorProfile,
                context: editorState.memory,
                genre: editorState.storyGenre,
                tone: editorState.storyTone,
                pov: editorState.storyPOV,
            },
            caller: {
                user_id: String(editorState.userId),
                workspace_id: editorState.workspaceId,
                project_id: editorState.projectId,
                api_keys: editorState.apiKeys,
            },
        };

        console.log("Formatted Data:", formattedData);

        setIsGenerating(true);

        const interactionKey = `editorInteracted_${editorState.workspaceId}_${editorState.projectId}_${editorState.userId}`;
        sessionStorage.setItem(interactionKey, 'true');

        router.post(
            route("workspace.projects.editor.generate", {
                workspace_id: editorState.workspaceId,
                project_id: editorState.projectId,
            }),
            formattedData,
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsGenerating(false);
                },
                onError: (errors) => {
                    setIsGenerating(false);
                    console.error("Generation errors:", errors);
                },
            }
        );
    };

    const formatLastSaved = () => {
        if (!lastSaved) return "Not saved yet";

        const now = new Date();
        const diffMs = now.getTime() - lastSaved.getTime();
        const diffMins = Math.round(diffMs / 60000);

        if (diffMins < 1) return "Just now";
        if (diffMins === 1) return "1 minute ago";
        if (diffMins < 60) return `${diffMins} minutes ago`;

        const hours = Math.floor(diffMins / 60);
        return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
    };

    const calculateWordCount = () => {
        const editorContent = document.getElementById("editor-content");
        if (!editorContent) return 0;

        const text = editorContent.textContent || "";
        if (!text.trim()) return 0;

        return text.trim().split(/\s+/).length;
    };

    const editorStateJson = JSON.stringify(editorState);

    return (
        <div
            className="bg-white rounded-lg shadow-sm border p-2"
            data-editor-context
            data-editor-state={editorStateJson}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Book className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <SlidersHorizontal className="h-4 w-4" />
                    </Button>
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
                    <span className="text-sm text-gray-500">
                        {lastSaved && <>Last saved: {formatLastSaved()}</>}
                    </span>
                    <span className="text-sm text-gray-500 ml-2">
                        {calculateWordCount()} words
                    </span>
                </div>

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
