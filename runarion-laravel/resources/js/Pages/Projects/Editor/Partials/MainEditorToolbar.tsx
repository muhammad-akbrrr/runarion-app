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
    Loader2,
} from "lucide-react";
import { useState, useEffect } from "react";

interface VersionControlState {
    currentVersionIndex: number;
    totalVersions: number;
    canUndo: boolean;
    canRedo: boolean;
    canRegenerate: boolean;
    isLoading: boolean;
    versionDisplayText: string;
    onUndo: () => void;
    onRedo: () => void;
    onSwitchVersion: (index: number) => void;
    onRegenerate: () => void;
}

interface EditorToolbarProps {
    onSend?: () => void;
    isGenerating?: boolean;
    wordCount?: number;
    versionControl?: VersionControlState;
}

export function EditorToolbar({
    onSend,
    isGenerating = false,
    wordCount = 0,
    versionControl,
}: EditorToolbarProps) {
    const [isButtonDisabled, setIsButtonDisabled] = useState(false);

    // Add a cooldown period after generation to prevent accidental double-clicks
    useEffect(() => {
        if (!isGenerating) {
            const timer = setTimeout(() => {
                setIsButtonDisabled(false);
            }, 1000);
            return () => clearTimeout(timer);
        } else {
            setIsButtonDisabled(true);
        }
    }, [isGenerating]);

    const handleSendClick = () => {
        if (onSend && !isButtonDisabled) {
            setIsButtonDisabled(true);
            onSend();
        }
    };

    const handleRegenerateClick = () => {
        if (versionControl?.onRegenerate && !isButtonDisabled && versionControl.canRegenerate) {
            setIsButtonDisabled(true);
            versionControl.onRegenerate();
        }
    };

    const handleUndoClick = () => {
        if (versionControl?.onUndo && versionControl.canUndo && !versionControl.isLoading) {
            versionControl.onUndo();
        }
    };

    const handleRedoClick = () => {
        if (versionControl?.onRedo && versionControl.canRedo && !versionControl.isLoading) {
            versionControl.onRedo();
        }
    };

    const handleVersionSwitch = (versionIndex: number) => {
        if (versionControl?.onSwitchVersion && !versionControl.isLoading) {
            versionControl.onSwitchVersion(versionIndex);
        }
    };

    // Calculate word count
    const displayWordCount = wordCount || 0;

    // Generate version options for dropdown
    const versionOptions = [];
    if (versionControl && versionControl.totalVersions > 0) {
        for (let i = 0; i < versionControl.totalVersions; i++) {
            versionOptions.push({
                index: i,
                label: `Version ${i}`,
                isSelected: i === versionControl.currentVersionIndex,
            });
        }
    }

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
                        <SlidersHorizontal className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-gray-500">
                        {displayWordCount} Words
                    </span>
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
                </div>

                {/* Right side - Action buttons */}
                <div className="flex items-center space-x-2">
                    {/* Undo Button */}
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 w-8 p-0"
                        onClick={handleUndoClick}
                        disabled={!versionControl?.canUndo || versionControl?.isLoading || isGenerating}
                        title="Undo to previous step"
                    >
                        {versionControl?.isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <RotateCcw className="h-4 w-4" />
                        )}
                    </Button>

                    {/* Redo Button */}
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 w-8 p-0"
                        onClick={handleRedoClick}
                        disabled={!versionControl?.canRedo || versionControl?.isLoading || isGenerating}
                        title={
                            !versionControl?.canRedo 
                                ? "No valid redo steps available for current version" 
                                : "Redo to next step"
                        }
                    >
                        {versionControl?.isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <RotateCw className="h-4 w-4" />
                        )}
                    </Button>

                    {/* Version Dropdown */}
                    <DropdownMenu>
                        <DropdownMenuTrigger disabled={versionControl?.isLoading || isGenerating}>
                            <span 
                                className={`
                                    text-lg h-8 w-8 flex items-center justify-center rounded-md 
                                    ${versionControl?.isLoading || isGenerating 
                                        ? 'text-gray-400 cursor-not-allowed' 
                                        : 'hover:bg-gray-100 cursor-pointer'
                                    }
                                `}
                                title={`Current version: ${versionControl?.versionDisplayText || '0'} of ${versionControl?.totalVersions || 1}`}
                            >
                                {versionControl?.isLoading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    versionControl?.versionDisplayText || "0"
                                )}
                            </span>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="center" side="top">
                            {versionOptions.length > 0 ? (
                                versionOptions.map((option) => (
                                    <DropdownMenuItem
                                        key={option.index}
                                        onClick={() => handleVersionSwitch(option.index)}
                                        className={option.isSelected ? "bg-blue-50 text-blue-700" : ""}
                                    >
                                        {option.label}
                                        {option.isSelected && " (Current)"}
                                    </DropdownMenuItem>
                                ))
                            ) : (
                                <DropdownMenuItem disabled>
                                    No versions available
                                </DropdownMenuItem>
                            )}
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Regenerate Button */}
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 w-8 p-0"
                        onClick={handleRegenerateClick}
                        disabled={!versionControl?.canRegenerate || isButtonDisabled || versionControl?.isLoading}
                        title="Regenerate current step"
                    >
                        {isGenerating || versionControl?.isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <RefreshCw className="h-4 w-4" />
                        )}
                    </Button>

                    {/* Send Button */}
                    <Button
                        size="sm"
                        onClick={handleSendClick}
                        disabled={isButtonDisabled || versionControl?.isLoading}
                        className={isGenerating ? "animate-pulse" : ""}
                    >
                        {isGenerating ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Generating...
                            </>
                        ) : (
                            <>
                                Send
                                <Send className="h-4 w-4 ml-2" />
                            </>
                        )}
                    </Button>
                </div>
            </div>
        </div>
    );
}
