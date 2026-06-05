import React, { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { http } from "@/Lib/http";

interface AutoBuildMagicWandProps {
    text: string;
    onEnhanced: (enhanced: string) => void;
    storyContext: string;
    workspaceId: string;
    projectId: string;
    aiModel: string;
    disabled: boolean;
}

export const AutoBuildMagicWand: React.FC<AutoBuildMagicWandProps> = ({
    text,
    onEnhanced,
    storyContext,
    workspaceId,
    projectId,
    aiModel,
    disabled,
}) => {
    const [isEnhancing, setIsEnhancing] = useState(false);

    const handleEnhance = async () => {
        if (!text.trim() || isEnhancing || disabled) return;

        setIsEnhancing(true);
        try {
            const response = await http(
                `/${workspaceId}/projects/${projectId}/editor/enhance-auto-build-prompt`,
                {
                    method: "POST",
                    data: {
                        text: text.trim(),
                        story_context: storyContext,
                        model: aiModel,
                    },
                },
            );

            if (!(response.status >= 200 && response.status < 300)) {
                const error =
                    response.data && typeof response.data === "object"
                        ? response.data
                        : { error: "Unknown error" };
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            const data = response.data;
            if (data.success && data.enhanced_text) {
                onEnhanced(data.enhanced_text);
            } else {
                throw new Error(data.error || "No enhanced text returned");
            }
        } catch (error) {
            console.error("Auto-Build Magic Wand error:", error);
            alert(
                `Failed to enhance prompt: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
        } finally {
            setIsEnhancing(false);
        }
    };

    return (
        <button
            onClick={handleEnhance}
            disabled={disabled || isEnhancing || !text.trim()}
            className="h-8 w-8 border-purple-600 bg-purple-50 hover:bg-purple-100 hover:border-purple-700 text-purple-600 rounded-md flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Enhance prompt using story context"
        >
            {isEnhancing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
                <Sparkles className="w-4 h-4" />
            )}
        </button>
    );
};
