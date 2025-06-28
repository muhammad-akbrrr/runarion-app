// ========================= Imports =========================
// External libraries
import { useState, useEffect } from "react";
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

export function SidebarContent() {
    // UI State
    const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

    // Main Settings
    const [currentPreset, setCurrentPreset] = useState("story-telling");
    const [authorProfile, setAuthorProfile] = useState("tolkien");
    const [aiModel, setAiModel] = useState("chatgpt-4o");
    const [memory, setMemory] = useState("");
    const [storyGenre, setStoryGenre] = useState("");
    const [storyTone, setStoryTone] = useState("");
    const [storyPov, setStoryPov] = useState("");

    // Advanced Settings - Sliders
    const [temperature, setTemperature] = useState([1]);
    const [repetitionPenalty, setRepetitionPenalty] = useState([0]);
    const [outputLength, setOutputLength] = useState([300]);
    const [minOutputToken, setMinOutputToken] = useState([50]);

    // Sampling values
    const [topP, setTopP] = useState([0.85]);
    const [tailFree, setTailFree] = useState([0.85]);
    const [topA, setTopA] = useState([0.85]);
    const [topK, setTopK] = useState([0.85]);

    // Phrase Bias Settings
    const [phraseBiasInput, setPhraseBiasInput] = useState("");
    const [phraseBiasValue, setPhraseBiasValue] = useState([0]);
    const [phraseBias, setPhraseBias] = useState<Array<{ [key: string]: number }>>([]);

    // Banned Tokens
    const [bannedTokensInput, setBannedTokensInput] = useState("");
    const [bannedPhrases, setBannedPhrases] = useState<string[]>([]);

    // Stop Sequence
    const [stopSequenceInput, setStopSequenceInput] = useState("");
    const [stopSequences, setStopSequences] = useState<string[]>([]);

    // Function to get all settings as JSON and log to console
    const logSettings = () => {
        const settings = {
            // Main Settings
            currentPreset,
            authorProfile,
            aiModel,
            memory,
            storyGenre,
            storyTone,
            storyPov,
            
            // Advanced Settings
            temperature: temperature[0],
            repetitionPenalty: repetitionPenalty[0],
            outputLength: outputLength[0],
            minOutputToken: minOutputToken[0],
            
            // Sampling
            topP: topP[0],
            tailFree: tailFree[0],
            topA: topA[0],
            topK: topK[0],
            
            // Phrase Bias
            phraseBias,
            
            // Banned Tokens
            bannedPhrases,
            
            // Stop Sequence
            stopSequences,
            
            // UI State
            isAdvancedOpen
        };
        
        console.log("Editor Settings:", JSON.stringify(settings, null, 2));
        return settings;
    };

    // Log settings whenever any value changes
    useEffect(() => {
        logSettings();
    }, [
        currentPreset, authorProfile, aiModel, memory, storyGenre, storyTone, storyPov,
        temperature, repetitionPenalty, outputLength, minOutputToken,
        topP, tailFree, topA, topK, phraseBias, bannedPhrases, stopSequences
    ]);

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
                <Select value={currentPreset} onValueChange={setCurrentPreset}>
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
                <Select value={authorProfile} onValueChange={setAuthorProfile}>
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
                <Select value={aiModel} onValueChange={setAiModel}>
                    <SelectTrigger className="w-full">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="chatgpt-4o">ChatGPT 4o</SelectItem>
                        <SelectItem value="gemini-4.0">Gemini 4.0</SelectItem>
                        <SelectItem value="deepseek-chat">
                            DeepSeek V3
                        </SelectItem>
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
                        value={memory}
                        onChange={(e) => setMemory(e.target.value)}
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
                        value={storyGenre}
                        onChange={(e) => setStoryGenre(e.target.value)}
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
                        value={storyTone}
                        onChange={(e) => setStoryTone(e.target.value)}
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
                        value={storyPov}
                        onChange={(e) => setStoryPov(e.target.value)}
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
                                Default: 1
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
                                Default: 0
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
                                max={2}
                                min={-2}
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
                                <span className="text-sm">
                                    Nucleus: {topP[0]}
                                </span>
                                <span className="text-sm text-gray-500">
                                    Default: 0.85
                                </span>
                            </div>
                            <Slider
                                value={topP}
                                onValueChange={setTopP}
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
                                onValueChange={setTailFree}
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
                                onValueChange={setTopA}
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
                                onValueChange={setTopK}
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
                                Type in the area below, then press the add button to save
                            </p>

                            <div className="flex flex-row items-center gap-2">
                                <Input 
                                    placeholder="Enter phrase to bias" 
                                    value={phraseBiasInput}
                                    onChange={(e) => setPhraseBiasInput(e.target.value)}
                                />

                                <Button
                                    variant="outline"
                                    className="h-9 w-9 p-0"
                                    onClick={() => {
                                        if (phraseBiasInput.trim()) {
                                            const updatedBias = [...phraseBias];
                                            updatedBias.push({ [phraseBiasInput]: phraseBiasValue[0] });
                                            setPhraseBias(updatedBias);
                                            setPhraseBiasInput('');
                                        }
                                    }}
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm">
                                        Bias: {phraseBiasValue[0]}
                                    </span>
                                    <span className="text-sm text-gray-500">
                                        Default: 0
                                    </span>
                                </div>
                                <Slider
                                    value={phraseBiasValue}
                                    onValueChange={setPhraseBiasValue}
                                    max={1}
                                    min={-1}
                                    step={0.01}
                                    className="w-full"
                                />
                            </div>

                            {/* List of phrase biases */}
                            {phraseBias.length > 0 && (
                                <div className="space-y-2 mt-2">
                                    <Label>Current Phrase Biases:</Label>
                                    {phraseBias.map((biasItem, index) => {
                                        const phrase = Object.keys(biasItem)[0];
                                        const biasValue = biasItem[phrase];
                                        return (
                                            <div key={index} className="flex items-center justify-between bg-gray-100 px-3 py-2 rounded">
                                                <span className="text-sm">
                                                    "{phrase}" (Bias: {biasValue})
                                                </span>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-6 w-6 p-0"
                                                    onClick={() => {
                                                        const updatedBias = [...phraseBias];
                                                        updatedBias.splice(index, 1);
                                                        setPhraseBias(updatedBias);
                                                    }}
                                                >
                                                    <X className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
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
                            <Checkbox 
                                id="enabled"
                            />
                            <Label htmlFor="enabled" className="text-sm">
                                Enabled
                            </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox 
                                id="completion"
                            />
                            <Label htmlFor="completion" className="text-sm">
                                Ensure Completion After Start
                            </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox 
                                id="unbias"
                            />
                            <Label htmlFor="unbias" className="text-sm">
                                Unbias When Generated
                            </Label>
                        </div>
                    </div>

                    {/* Banned Phrases */}
                    <div className="space-y-3">
                        <Label>Banned Phrases</Label>
                        <p className="text-xs text-gray-500">
                            Words or phrases the AI should avoid using
                        </p>
                        <div className="flex flex-row items-center gap-2">
                            <Select defaultValue="empty">
                                <SelectTrigger className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="empty">
                                        Empty
                                    </SelectItem>
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
                            Type in the area below, then press the add button to save
                        </p>

                        {/* Add new banned token */}
                        <div className="flex flex-row items-center gap-2">
                            <Input 
                                placeholder="Enter phrase to ban" 
                                value={bannedTokensInput}
                                onChange={(e) => setBannedTokensInput(e.target.value)}
                            />

                            <Button
                                variant="outline"
                                className="h-9 w-9 p-0"
                                onClick={() => {
                                    if (bannedTokensInput.trim()) {
                                        const updatedTokens = [...bannedPhrases, bannedTokensInput];
                                        setBannedPhrases(updatedTokens);
                                        setBannedTokensInput('');
                                    }
                                }}
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* List of banned tokens */}
                    {bannedPhrases.length > 0 && (
                        <div className="space-y-2 mt-2">
                            <Label>Current Banned Tokens:</Label>
                            <div className="flex flex-wrap gap-2">
                                {bannedPhrases.map((token, index) => (
                                    <div key={index} className="flex items-center bg-gray-100 px-2 py-1 rounded">
                                        <span className="text-sm mr-1">{token}</span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-5 w-5 p-0"
                                            onClick={() => {
                                                const updatedTokens = [...bannedPhrases];
                                                updatedTokens.splice(index, 1);
                                                setBannedPhrases(updatedTokens);
                                            }}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

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
                            <Checkbox 
                                id="sequences-enabled"
                            />
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
                            Sequences that will cause the AI to stop generating text
                        </p>

                        <div className="flex flex-row items-center gap-2">
                            <Input 
                                placeholder="Enter stop sequence" 
                                value={stopSequenceInput}
                                onChange={(e) => setStopSequenceInput(e.target.value)}
                            />

                            <Button
                                variant="outline"
                                className="h-9 w-9 p-0"
                                onClick={() => {
                                    if (stopSequenceInput.trim()) {
                                        const updatedSequences = [...stopSequences, stopSequenceInput];
                                        setStopSequences(updatedSequences);
                                        setStopSequenceInput('');
                                    }
                                }}
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* List of stop sequences */}
                        {stopSequences.length > 0 && (
                            <div className="space-y-2 mt-2">
                                <Label>Current Stop Sequences:</Label>
                                {stopSequences.map((sequence, index) => (
                                    <div key={index} className="flex items-center justify-between bg-gray-100 px-3 py-2 rounded">
                                        <span className="text-sm">"{sequence}"</span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 w-6 p-0"
                                            onClick={() => {
                                                const updatedSequences = [...stopSequences];
                                                updatedSequences.splice(index, 1);
                                                setStopSequences(updatedSequences);
                                            }}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}

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
