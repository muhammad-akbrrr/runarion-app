import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import { Button } from "@/Components/ui/button";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import { HelpCircle, FileText, Users, Heart, Wrench } from "lucide-react";
import SummarizerTab from "./SummarizerTab";
import EntityExtractorTab from "./EntityExtractorTab";
import AuditorToolsTab from "./AuditorToolsTab";
import SentimentTab from "./SentimentTab";

interface AuditorTabProps {
    workspaceId: string;
    projectId: string;
    onApplyStoryFix?: (oldText: string, newText: string) => boolean;
}

export default function AuditorTab({
    workspaceId,
    projectId,
    onApplyStoryFix,
}: AuditorTabProps) {
    const [selectedModel, setSelectedModel] =
        useState<string>("gemini-2.0-flash");

    // Available Gemini models for analysis (same as editor settings)
    const availableModels = [
        { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash (Stable)" },
        {
            value: "gemini-2.5-flash",
            label: "Gemini 2.5 Flash (Fast + Thinking)",
        },
        {
            value: "gemini-2.5-pro",
            label: "Gemini 2.5 Pro (Quality + Thinking)",
        },
        {
            value: "gemini-3-pro-preview",
            label: "Gemini 3.0 Pro (Paid API Key)",
        },
    ];

    return (
        <div className="flex flex-col h-full">
            {/* Model Selection */}
            <div className="p-4 border-b">
                <div className="space-y-2">
                    <Label
                        htmlFor="model-select"
                        className="text-sm font-medium"
                    >
                        Analysis Model:
                    </Label>
                    <div className="flex gap-2 items-center">
                        <Select
                            value={selectedModel}
                            onValueChange={setSelectedModel}
                        >
                            <SelectTrigger id="model-select" className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {availableModels.map((model) => (
                                    <SelectItem
                                        key={model.value}
                                        value={model.value}
                                    >
                                        {model.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                                <p>
                                    Select which Gemini model will perform the
                                    analysis. These are the same models
                                    available in Editor Settings. Gemini 3.0 Pro
                                    and 2.5 Pro provide the best quality with
                                    thinking capabilities. Gemini 2.0 Flash is
                                    the fastest and most stable option.
                                </p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                </div>
            </div>

            {/* Main Tabs - 2x2 Grid Layout */}
            <Tabs
                defaultValue="summarizer"
                className="flex-1 flex flex-col overflow-hidden"
            >
                <div className="border-b bg-gray-50">
                    <TabsList className="w-full h-auto p-1 grid grid-cols-2 grid-rows-2 gap-1 bg-transparent">
                        <TabsTrigger
                            value="summarizer"
                            className="flex items-center justify-center data-[state=active]:bg-foreground data-[state=active]:text-background"
                        >
                            <FileText className="h-4 w-4" />
                            <span className="text-sm font-medium">
                                Summarizer
                            </span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="extractor"
                            className="flex items-center justify-center data-[state=active]:bg-foreground data-[state=active]:text-background"
                        >
                            <Users className="h-4 w-4" />
                            <span className="text-sm font-medium">
                                Extractor
                            </span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="tools"
                            className="flex items-center justify-center data-[state=active]:bg-foreground data-[state=active]:text-background"
                        >
                            <Wrench className="h-4 w-4" />
                            <span className="text-sm font-medium">Tools</span>
                        </TabsTrigger>
                        <TabsTrigger
                            value="sentiment"
                            className="flex items-center justify-center data-[state=active]:bg-foreground data-[state=active]:text-background"
                        >
                            <Heart className="h-4 w-4" />
                            <span className="text-sm font-medium">
                                Sentiment
                            </span>
                        </TabsTrigger>
                    </TabsList>
                </div>

                {/* Summarizer Tab */}
                <TabsContent
                    value="summarizer"
                    className="flex-1 overflow-y-auto p-4"
                >
                    <SummarizerTab
                        workspaceId={workspaceId}
                        projectId={projectId}
                        selectedModel={selectedModel}
                    />
                </TabsContent>

                {/* Entity Extractor Tab */}
                <TabsContent
                    value="extractor"
                    className="flex-1 overflow-y-auto p-4"
                >
                    <EntityExtractorTab
                        workspaceId={workspaceId}
                        projectId={projectId}
                        selectedModel={selectedModel}
                    />
                </TabsContent>

                {/* Tools Tab */}
                <TabsContent
                    value="tools"
                    className="flex-1 overflow-y-auto p-4"
                >
                    <AuditorToolsTab
                        workspaceId={workspaceId}
                        projectId={projectId}
                        selectedModel={selectedModel}
                        onApplyStoryFix={onApplyStoryFix}
                    />
                </TabsContent>

                {/* Sentiment Analyzer Tab */}
                <TabsContent
                    value="sentiment"
                    className="flex-1 overflow-y-auto p-4"
                >
                    <SentimentTab
                        workspaceId={workspaceId}
                        projectId={projectId}
                        selectedModel={selectedModel}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}
