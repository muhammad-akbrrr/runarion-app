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
    Book,
} from "lucide-react";
import { useEditor } from "../../EditorContext";

export function SidebarContent() {
    const { editorState, updateEditorState } = useEditor();
    const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
    
    // Use state from context for sliders, but keep as arrays for the Slider component
    const [temperature, setTemperature] = useState([editorState.temperature]);
    const [repetitionPenalty, setRepetitionPenalty] = useState([editorState.repetitionPenalty]);
    const [outputLength, setOutputLength] = useState([editorState.outputLength]);
    const [phraseBias, setPhraseBias] = useState([0]);
    const [minOutputToken, setMinOutputToken] = useState([editorState.minOutputToken]);

    // Sampling values
    const [topP, setTopP] = useState([editorState.topP]);
    const [tailFree, setTailFree] = useState([editorState.tailFree]);
    const [topA, setTopA] = useState([editorState.topA]);
    const [topK, setTopK] = useState([editorState.topK]);

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
                <Select 
                    value={editorState.preset}
                    onValueChange={(value) => updateEditorState('preset', value)}
                >
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
                <Select 
                    value={editorState.authorProfile}
                    onValueChange={(value) => updateEditorState('authorProfile', value)}
                >
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
                <Select 
                    value={editorState.aiModel}
                    onValueChange={(value) => updateEditorState('aiModel', value)}
                >
                    <SelectTrigger className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="gpt-4o-mini">ChatGPT 4o</SelectItem>
                        <SelectItem value="gemini-2.0-flash">Gemini 2.0</SelectItem>
                        <SelectItem value="deepseek-chat">DeepSeek V3</SelectItem>
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
                        value={editorState.memory}
                        onChange={(e) => updateEditorState('memory', e.target.value)}
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
                        value={editorState.storyGenre}
                        onChange={(e) => updateEditorState('storyGenre', e.target.value)}
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
                        value={editorState.storyTone}
                        onChange={(e) => updateEditorState('storyTone', e.target.value)}
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
                <div className="flex flex-row items-center gap-2">
                    <Input
                        id="pov"
                        placeholder="Search for an entry"
                        className="pr-8"
                        value={editorState.storyPOV}
                        onChange={(e) => updateEditorState('storyPOV', e.target.value)}
                    />
                    <Button variant="outline" className="h-9 w-9 p-0">
                        <Book className="h-3 w-3" />
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
                                onValueChange={(value) => {
                                    setTemperature(value);
                                    updateEditorState('temperature', value[0]);
                                }}
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
                                onValueChange={(value) => {
                                    setRepetitionPenalty(value);
                                    updateEditorState('repetitionPenalty', value[0]);
                                }}
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
                                onValueChange={(value) => {
                                    setOutputLength(value);
                                    updateEditorState('outputLength', value[0]);
                                }}
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
                                <span className="text-sm">
                                    Nucleus: {topP[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                value={topP}
                                onValueChange={(value) => {
                                    setTopP(value);
                                    updateEditorState('topP', value[0]);
                                }}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">
                                    Tail-Free: {tailFree[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                value={tailFree}
                                onValueChange={(value) => {
                                    setTailFree(value);
                                    updateEditorState('tailFree', value[0]);
                                }}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">
                                    Top-A: {topA[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                value={topA}
                                onValueChange={(value) => {
                                    setTopA(value);
                                    updateEditorState('topA', value[0]);
                                }}
                                max={1}
                                min={0}
                                step={0.01}
                            />

                            <div className="flex justify-between items-center">
                                <span className="text-sm">
                                    Top-K: {topK[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                value={topK}
                                onValueChange={(value) => {
                                    setTopK(value);
                                    updateEditorState('topK', value[0]);
                                }}
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
                            <div className="flex flex-row items-center gap-2">
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

                                <Button
                                    variant="outline"
                                    className="h-9 w-9 p-0"
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                                <Button
                                    variant="outline"
                                    className="h-9 w-9 p-0"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>

                            <p className="text-xs text-gray-500">
                                Type in the area below, then press enter to save
                            </p>

                            <div className="flex flex-row items-center gap-2">
                                <Input placeholder="Enter phrase you want to bias" />

                                <Button
                                    variant="outline"
                                    className="h-9 w-9 p-0"
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                            </div>

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
                            <p className="text-xs text-gray-500">
                                Click the phrase to edit
                            </p>
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
                        <div className="flex flex-row items-center gap-2">
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

                            <Button variant="outline" className="h-9 w-9 p-0">
                                <Plus className="h-4 w-4" />
                            </Button>
                            <Button variant="outline" className="h-9 w-9 p-0">
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>

                        <p className="text-xs text-gray-500">
                            Type in the area below, then press enter to save
                        </p>

                        <div className="flex flex-row items-center gap-2">
                            <Input placeholder="Enter phrase you want to ban" />

                            <Button variant="outline" className="h-9 w-9 p-0">
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Sequences */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-center">
                            <Label>Sequences</Label>
                            <p className="text-xs text-gray-500">
                                Click the phrase to edit
                            </p>
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

                        <div className="flex flex-row items-center gap-2">
                            <Input placeholder="Enter phrase you want to ban" />

                            <Button variant="outline" className="h-9 w-9 p-0">
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>

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
                                onValueChange={(value) => {
                                    setMinOutputToken(value);
                                    updateEditorState('minOutputToken', value[0]);
                                }}
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
