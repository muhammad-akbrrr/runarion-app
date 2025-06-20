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

export function EditorToolbar() {
    const { editorState } = useEditor();

    const handleSendClick = () => {
        // Log all sidebar parameters to the console, including advanced parameters
        console.log("Editor Parameters:", {
            // Basic parameters
            preset: editorState.preset,
            authorProfile: editorState.authorProfile,
            aiModel: editorState.aiModel,
            memory: editorState.memory,
            storyGenre: editorState.storyGenre,
            storyTone: editorState.storyTone,
            storyPOV: editorState.storyPOV,
            
            // Advanced parameters
            temperature: editorState.temperature,
            repetitionPenalty: editorState.repetitionPenalty,
            outputLength: editorState.outputLength,
            topP: editorState.topP, // Nucleus sampling
            tailFree: editorState.tailFree,
            topA: editorState.topA,
            topK: editorState.topK,
            minOutputToken: editorState.minOutputToken
        });
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
                    <Button size="sm" onClick={handleSendClick}>
                        Send
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
