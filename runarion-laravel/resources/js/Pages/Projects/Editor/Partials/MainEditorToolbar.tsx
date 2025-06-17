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
    Trash2,
    Send,
    Book,
    SlidersHorizontal,
} from "lucide-react";

export function EditorToolbar() {
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
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8">
                                Auto
                                <ChevronUp className="ml-1 h-3 w-3" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent side="top" align="start">
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
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button size="sm">
                        Send
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
