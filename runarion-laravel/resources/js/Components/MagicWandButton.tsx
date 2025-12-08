import { useState } from "react";
import { Button } from "@/Components/ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";

export type EnhancementMode = 
    | 'story_text' 
    | 'chat_message' 
    | 'property' 
    | 'custom_instruction'
    | 'entity_name'
    | 'chapter_name'
    | 'description'
    | 'summary';

interface MagicWandButtonProps {
    text: string;  // The unsent text to enhance
    onEnhanced: (enhancedText: string) => void;  // Callback with enhanced text
    enhancementMode: EnhancementMode;
    workspaceId?: string;
    projectId?: string;
    aiModel?: string;
    disabled?: boolean;
    size?: 'sm' | 'md' | 'lg' | 'icon';
    variant?: 'default' | 'ghost' | 'outline';
    className?: string;
    showLabel?: boolean;
    chapterContent?: string;  // Optional chapter content for chapter_name mode
}

export function MagicWandButton({
    text,
    onEnhanced,
    enhancementMode,
    workspaceId,
    projectId,
    aiModel = 'gemini-2.5-flash',
    disabled = false,
    size = 'icon',
    variant = 'ghost',
    className = '',
    showLabel = false,
    chapterContent,
}: MagicWandButtonProps) {
    const [isEnhancing, setIsEnhancing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleEnhance = async () => {
        console.log('Magic Wand clicked', { text: text.trim(), isEnhancing, disabled, workspaceId, projectId });
        
        if (!text.trim() || isEnhancing || disabled) {
            console.log('Magic Wand blocked:', { hasText: !!text.trim(), isEnhancing, disabled });
            return;
        }

        setIsEnhancing(true);
        setError(null);

        if (!workspaceId || !projectId) {
            const errorMsg = 'Workspace ID and Project ID are required';
            setError(errorMsg);
            setIsEnhancing(false);
            console.error('Magic Wand error:', errorMsg);
            return;
        }

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            const url = `/${workspaceId}/projects/${projectId}/editor/enhance-text`;
            
            console.log('Magic Wand API call:', { url, enhancementMode, model: aiModel });
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': csrfToken,
                },
                body: JSON.stringify({
                    text: text.trim(),
                    enhancement_mode: enhancementMode,
                    model: aiModel,
                    chapter_content: chapterContent || undefined,
                }),
            });

            console.log('Magic Wand response status:', response.status);

            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                let errorDetails = null;
                
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorData.details || errorMessage;
                    errorDetails = errorData;
                    console.error('Magic Wand API error response:', errorData);
                } catch (e) {
                    // Try to get text response if JSON parsing fails
                    try {
                        const textResponse = await response.text();
                        console.error('Magic Wand error text response:', textResponse);
                        if (textResponse) {
                            errorMessage = textResponse.length > 200 ? textResponse.substring(0, 200) + '...' : textResponse;
                        }
                    } catch (textError) {
                        console.error('Magic Wand error - could not parse response:', textError);
                    }
                }
                
                // Provide more specific error messages
                if (response.status === 503) {
                    errorMessage = 'Enhancement service is unavailable. Please check if the Python service is running.';
                } else if (response.status === 500) {
                    errorMessage = errorMessage || 'Server error occurred during enhancement. Please try again.';
                } else if (response.status === 422) {
                    errorMessage = errorMessage || 'Invalid request. Please check your input.';
                }
                
                throw new Error(errorMessage);
            }

            let data;
            try {
                data = await response.json();
                console.log('Magic Wand response data:', data);
            } catch (parseError) {
                console.error('Magic Wand JSON parse error:', parseError);
                const textResponse = await response.text();
                console.error('Magic Wand raw response:', textResponse);
                throw new Error('Invalid response format from server');
            }
            
            if (data.success && data.enhanced_text) {
                console.log('Magic Wand success, enhanced text length:', data.enhanced_text.length);
                onEnhanced(data.enhanced_text);
            } else {
                const errorMsg = data.error || data.message || 'No enhanced text returned';
                console.error('Magic Wand no enhanced text:', data);
                throw new Error(errorMsg);
            }
        } catch (err) {
            let errorMessage = 'Failed to enhance text';
            
            if (err instanceof Error) {
                errorMessage = err.message;
            } else if (typeof err === 'string') {
                errorMessage = err;
            } else if (err && typeof err === 'object' && 'message' in err) {
                errorMessage = String(err.message);
            }
            
            // Handle network errors
            if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError') || errorMessage.includes('Network request failed')) {
                errorMessage = 'Network error: Could not connect to the server. Please check your connection.';
            }
            
            setError(errorMessage);
            console.error('Magic Wand enhancement error:', {
                error: err,
                message: errorMessage,
                text: text.substring(0, 50) + '...',
                enhancementMode,
                workspaceId,
                projectId
            });
            
            // Show user-friendly error
            alert(`Enhancement failed: ${errorMessage}`);
        } finally {
            setIsEnhancing(false);
        }
    };

    const buttonSize = size === 'icon' ? 'icon' : size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : 'default';
    const iconSize = size === 'sm' ? 'h-2.5 w-2.5' : size === 'lg' ? 'h-5 w-5' : 'h-2.5 w-2.5';

    const button = (
        <Button
            type="button"
            variant={variant}
            size={buttonSize}
            onClick={handleEnhance}
            disabled={disabled || isEnhancing || !text.trim()}
            className={className}
            title={error || "Enhance with AI"}
        >
            {isEnhancing ? (
                <Loader2 className={`${iconSize} animate-spin ${className.includes('text-white') ? 'text-white' : className.includes('green') ? 'text-green-300' : ''}`} />
            ) : (
                <Sparkles className={`${iconSize} ${className.includes('text-white') ? 'text-white' : className.includes('green') ? 'text-green-300' : ''}`} />
            )}
            {showLabel && !isEnhancing && <span className="ml-1">Enhance</span>}
            {showLabel && isEnhancing && <span className="ml-1">Enhancing...</span>}
        </Button>
    );

    if (error) {
        return (
            <Tooltip>
                <TooltipTrigger asChild>
                    {button}
                </TooltipTrigger>
                <TooltipContent>
                    <p className="text-destructive">{error}</p>
                </TooltipContent>
            </Tooltip>
        );
    }

    return button;
}

