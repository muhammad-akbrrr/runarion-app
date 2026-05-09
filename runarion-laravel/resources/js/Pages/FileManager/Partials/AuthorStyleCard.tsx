import React from "react";
import { AuthorStyle } from "@/types/files";
import { Button } from "@/Components/ui/button";
import { CirclePlus, Loader2, CheckCircle2, AlertCircle, Pencil, Trash2 } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/Components/ui/tooltip";

interface AuthorStyleCardProps {
  authorStyles: AuthorStyle[];
  onAddClick: () => void;
  onEditClick?: (style: AuthorStyle) => void;
  onDeleteClick?: (style: AuthorStyle) => void;
}

function getStatusInfo(status: string) {
  switch (status) {
    case 'profiling_completed':
      return {
        icon: CheckCircle2,
        color: 'text-green-500',
        bgColor: 'bg-green-50',
        label: 'Ready to use',
      };
    case 'init_completed':
    case 'sampling_completed':
      return {
        icon: Loader2,
        color: 'text-amber-500',
        bgColor: 'bg-amber-50',
        label: 'Processing...',
        animate: true,
      };
    case 'sampling_failed':
    case 'init_failed':
    case 'profiling_failed':
      return {
        icon: AlertCircle,
        color: 'text-red-500',
        bgColor: 'bg-red-50',
        label: 'Processing failed',
      };
    default:
      return {
        icon: Loader2,
        color: 'text-gray-400',
        bgColor: 'bg-gray-50',
        label: 'Unknown status',
      };
  }
}

export default function AuthorStyleCard({ 
  authorStyles, 
  onAddClick,
  onEditClick,
  onDeleteClick,
}: AuthorStyleCardProps) {
  return (
    <div className="space-y-4">
        <div className="flex justify-between items-center">
            <h2 className="text-xl">Author Styles</h2>
            <Button
              variant="default"
              onClick={onAddClick}
            >
                <CirclePlus className="h-4 w-4" />
                Add Author Style
            </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {authorStyles.length > 0 ? (
                authorStyles.map((style) => {
                    const statusInfo = getStatusInfo(style.status);
                    const StatusIcon = statusInfo.icon;
                    const isReady = style.status === 'profiling_completed';
                    
                    return (
                    <div
                        key={style.id}
                            className={`w-full bg-white rounded-md border hover:shadow-md transition-shadow ${!isReady ? 'opacity-80' : ''}`}
                    >
                            <div className="p-4 relative flex flex-col items-stretch justify-between gap-3">
                                {/* Header row with avatar and status */}
                            <div className="flex flex-row items-start justify-between gap-3">
                                <div
                                        className={`${style.color} p-2 rounded-full flex items-center justify-center font-medium text-sm`}
                                >
                                        {style.avatar}
                                    </div>
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <div className={`${statusInfo.bgColor} px-2 py-0.5 rounded flex items-center gap-1`}>
                                                    <StatusIcon 
                                                        className={`h-3 w-3 ${statusInfo.color} ${statusInfo.animate ? 'animate-spin' : ''}`} 
                                                    />
                                                    <span className={`text-xs ${statusInfo.color}`}>
                                                        {isReady ? 'Ready' : 'Processing'}
                                                    </span>
                                                </div>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>{statusInfo.label}</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                                
                                {/* Name */}
                            <div className="truncate">
                                <p className="font-medium text-sm">
                                    {style.name}
                                </p>
                                </div>
                                
                                {/* Action buttons */}
                                <div className="flex flex-row items-center justify-end gap-1 pt-1 border-t">
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-7 w-7 p-0"
                                                    onClick={() => onEditClick?.(style)}
                                                    disabled={!isReady}
                                                >
                                                    <Pencil className="h-3.5 w-3.5" />
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>{isReady ? 'Edit style' : 'Wait for processing to complete'}</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                    
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                                                    onClick={() => onDeleteClick?.(style)}
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>Delete style</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                            </div>
                        </div>
                    );
                })
            ) : (
                <div className="w-full col-span-4 text-center py-8 text-muted-foreground">
                    You don't have any author styles yet.
                </div>
            )}
        </div>
    </div>
  );
}
