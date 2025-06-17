// ========================= Imports =========================
// External libraries
import { useState } from "react";
import { Label } from "@/Components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { Textarea } from "@/Components/ui/textarea";
import { Input } from "@/Components/ui/input";
import { Button } from "@/Components/ui/button";
import { Slider } from "@/Components/ui/slider";
import { Checkbox } from "@/Components/ui/checkbox";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/Components/ui/collapsible";
import {
    ChevronDown,
    ChevronUp,
    Maximize2,
    Plus,
    Trash2,
    X,
} from "lucide-react";

export function SidebarContent() {
    const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
    const [temperature, setTemperature] = useState([1.35]);
    const [repetitionPenalty, setRepetitionPenalty] = useState([2.8]);
    const [outputLength, setOutputLength] = useState([300]);
    const [phraseBias, setPhraseBias] = useState([0]);
    const [minOutputToken, setMinOutputToken] = useState([50]);

    return (
        <div
            className="
                space-y-6
                px-3 pt-3 pb-6
            "
        >
            {/* Current Preset */}
            <div className="space-y-2">
                <Label htmlFor="preset">Current Preset</Label>
                <Select defaultValue="story-telling">
                    <SelectTrigger className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="story-telling">
                            Story Telling
                        </SelectItem>
                        <SelectItem value="creative-writing">
                            Creative Writing
                        </SelectItem>
                        <SelectItem value="technical">Technical</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Author Profile */}
            <div className="space-y-2">
                <Label htmlFor="author">Author Profile</Label>
                <Select defaultValue="tolkien">
                    <SelectTrigger className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="tolkien">Tolkien</SelectItem>
                        <SelectItem value="hemingway">Hemingway</SelectItem>
                        <SelectItem value="shakespeare">Shakespeare</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* AI Model */}
            <div className="space-y-2">
                <Label htmlFor="model">AI Model</Label>
                <Select defaultValue="chatgpt-4.5">
                    <SelectTrigger className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="chatgpt-4.5">ChatGPT 4.5</SelectItem>
                        <SelectItem value="chatgpt-4">ChatGPT 4</SelectItem>
                        <SelectItem value="claude">Claude</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Memory */}
            <div className="space-y-2">
                <Label htmlFor="memory">Memory</Label>
                <p className="text-xs text-gray-500">
                    The AI will better remember info placed here
                </p>
                <div className="relative">
                    <Textarea
                        id="memory"
                        placeholder="Type here..."
                        className="min-h-[80px] pr-8"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-2 right-2 h-6 w-6 p-0"
                    >
                        <Maximize2 className="h-3 w-3" />
                    </Button>
                </div>
            </div>

            {/* Story Genre */}
            <div className="space-y-2">
                <Label htmlFor="genre">Story Genre</Label>
                <p className="text-xs text-gray-500">
                    The AI will better remember info placed here
                </p>
                <div className="relative">
                    <Textarea
                        id="genre"
                        placeholder="Type here..."
                        className="min-h-[80px] pr-8"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-2 right-2 h-6 w-6 p-0"
                    >
                        <Maximize2 className="h-3 w-3" />
                    </Button>
                </div>
            </div>

            {/* Story Tone */}
            <div className="space-y-2">
                <Label htmlFor="tone">Story Tone</Label>
                <p className="text-xs text-gray-500">
                    The AI will better remember info placed here
                </p>
                <div className="relative">
                    <Textarea
                        id="tone"
                        placeholder="Type here..."
                        className="min-h-[80px] pr-8"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-2 right-2 h-6 w-6 p-0"
                    >
                        <Maximize2 className="h-3 w-3" />
                    </Button>
                </div>
            </div>

            {/* Story POV */}
            <div className="space-y-2">
                <Label htmlFor="pov">Story POV</Label>
                <div className="relative">
                    <Input
                        id="pov"
                        placeholder="Search for an entry"
                        className="pr-8"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-1/2 right-2 -translate-y-1/2 h-6 w-6 p-0"
                    >
                        <Maximize2 className="h-3 w-3" />
                    </Button>
                </div>
            </div>

            {/* Advanced Section */}
            <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
                <CollapsibleTrigger asChild>
                    <Button
                        variant="ghost"
                        className="
                            w-full justify-between !p-0
                            rounded-none h-auto
                            hover:bg-transparent
                        "
                    >
                        <span className="font-medium">Advanced</span>
                        {isAdvancedOpen ? (
                            <ChevronUp className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </Button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-6 mt-4">
                    {/* Temperature */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Temperature</Label>
                            <span className="text-sm text-gray-500">
                                Default: 1.35
                            </span>
                        </div>
                        <p className="text-xs text-gray-500">
                            The higher the value, the more random the output
                        </p>
                        <div className="space-y-2">
                            <span className="text-sm">{temperature[0]}</span>
                            <Slider
                                value={temperature}
                                onValueChange={setTemperature}
                                max={2}
                                min={0}
                                step={0.01}
                                className="w-full"
                            />
                        </div>
                    </div>

                    {/* Repetition Penalty */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Repetition Penalty</Label>
                            <span className="text-sm text-gray-500">
                                Default: 2.8
                            </span>
                        </div>
                        <p className="text-xs text-gray-500">
                            Higher values make the output less repetitive
                        </p>
                        <div className="space-y-2">
                            <span className="text-sm">
                                {repetitionPenalty[0]}
                            </span>
                            <Slider
                                value={repetitionPenalty}
                                onValueChange={setRepetitionPenalty}
                                max={5}
                                min={1}
                                step={0.1}
                                className="w-full"
                            />
                        </div>
                    </div>

                    {/* Output Length */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Output Length</Label>
                            <span className="text-sm text-gray-500">
                                Default: 300
                            </span>
                        </div>
                        <p className="text-xs text-gray-500">
                            Increase the length of the generated responses
                        </p>
                        <div className="space-y-2">
                            <span className="text-sm">~{outputLength[0]}</span>
                            <Slider
                                value={outputLength}
                                onValueChange={setOutputLength}
                                max={1000}
                                min={50}
                                step={10}
                                className="w-full"
                            />
                        </div>
                    </div>

                    {/* Sampling */}
                    <div className="space-y-3">
                        <Label>Sampling</Label>
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <span className="text-sm">Nucleus: 0.85</span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                defaultValue={[0.85]}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">Tail-Free: 0.85</span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                defaultValue={[0.85]}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">Top-A: 0.85</span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                defaultValue={[0.85]}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">Top-K: 0.85</span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                defaultValue={[0.85]}
                                max={1}
                                min={0}
                                step={0.01}
                            />
                        </div>
                    </div>

                    {/* Phrase Bias */}
                    <div className="space-y-3">
                        <Label>Phrase Bias</Label>
                        <p className="text-xs text-gray-500">
                            Weigh the AI's chance of generating certain words or
                            phrases
                        </p>
                        <div className="space-y-3">
                            <Select defaultValue="none">
                                <SelectTrigger className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">
                                        Bias 0 | (none)
                                    </SelectItem>
                                    <SelectItem value="positive">
                                        Positive Bias
                                    </SelectItem>
                                    <SelectItem value="negative">
                                        Negative Bias
                                    </SelectItem>
                                </SelectContent>
                            </Select>

                            <div className="flex space-x-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>

                            <Input placeholder="Enter phrase you want to bias" />
                            <Button
                                variant="ghost"
                                size="sm"
                                className="w-full justify-start"
                            >
                                <Plus className="mr-2 h-4 w-4" />
                                Add phrase
                            </Button>

                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm">
                                        Bias: {phraseBias[0]}
                                    </span>
                                    <span className="text-sm text-gray-500">
                                        Default: 0
                                    </span>
                                </div>
                                <Slider
                                    value={phraseBias}
                                    onValueChange={setPhraseBias}
                                    max={1}
                                    min={-1}
                                    step={0.01}
                                    className="w-full"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Phrases */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Phrases</Label>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-xs"
                            >
                                Click the phrase to edit
                            </Button>
                        </div>
                        <div className="relative">
                            <Textarea
                                placeholder="Type here..."
                                className="min-h-[80px] pr-8"
                            />
                            <Button
                                variant="ghost"
                                size="sm"
                                className="absolute top-2 right-2 h-6 w-6 p-0"
                            >
                                <Maximize2 className="h-3 w-3" />
                            </Button>
                        </div>
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-3">
                        <div className="flex items-center space-x-2">
                            <Checkbox id="enabled" />
                            <Label htmlFor="enabled" className="text-sm">
                                Enabled
                            </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="completion" />
                            <Label htmlFor="completion" className="text-sm">
                                Ensure Completion After Start
                            </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="unbias" />
                            <Label htmlFor="unbias" className="text-sm">
                                Unbias When Generated
                            </Label>
                        </div>
                    </div>

                    {/* Banned Tokens */}
                    <div className="space-y-3">
                        <Label>Banned Tokens</Label>
                        <p className="text-xs text-gray-500">
                            Weigh the AI's chance of generating certain words or
                            phrases
                        </p>
                        <Select defaultValue="empty">
                            <SelectTrigger className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="empty">Empty</SelectItem>
                                <SelectItem value="common">
                                    Common Words
                                </SelectItem>
                                <SelectItem value="custom">
                                    Custom List
                                </SelectItem>
                            </SelectContent>
                        </Select>
                        <div className="flex space-x-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                        <Input placeholder="Enter phrase you want to ban" />
                        <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start"
                        >
                            <Plus className="mr-2 h-4 w-4" />
                            Add phrase
                        </Button>
                    </div>

                    {/* Sequences */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Sequences</Label>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-xs"
                            >
                                Click the phrase to edit
                            </Button>
                        </div>
                        <div className="relative">
                            <Textarea
                                placeholder="Type here..."
                                className="min-h-[80px] pr-8"
                            />
                            <Button
                                variant="ghost"
                                size="sm"
                                className="absolute top-2 right-2 h-6 w-6 p-0"
                            >
                                <Maximize2 className="h-3 w-3" />
                            </Button>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox id="sequences-enabled" />
                            <Label
                                htmlFor="sequences-enabled"
                                className="text-sm"
                            >
                                Enabled
                            </Label>
                        </div>
                    </div>

                    {/* Stop Sequence */}
                    <div className="space-y-3">
                        <Label>Stop Sequence</Label>
                        <p className="text-xs text-gray-500">
                            Weigh the AI's chance of generating certain words or
                            phrases
                        </p>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between bg-gray-100 px-3 py-2 rounded">
                                <span className="text-sm">
                                    {"{while |a|k|bar}"}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0"
                                >
                                    <X className="h-3 w-3" />
                                </Button>
                            </div>
                            <div className="flex items-center justify-between bg-gray-100 px-3 py-2 rounded">
                                <span className="text-sm">
                                    {"{while |a|k|bar}"}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0"
                                >
                                    <X className="h-3 w-3" />
                                </Button>
                            </div>
                        </div>
                        <Input placeholder="Enter phrase you want to ban" />
                        <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start"
                        >
                            <Plus className="mr-2 h-4 w-4" />
                            Add phrase
                        </Button>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-sm">
                                    Min Output Token: {minOutputToken[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 1
                                </span>
                            </div>
                            <Slider
                                value={minOutputToken}
                                onValueChange={setMinOutputToken}
                                max={100}
                                min={1}
                                step={1}
                                className="w-full"
                            />
                        </div>
                    </div>
                </CollapsibleContent>
            </Collapsible>
        </div>
    );
}
