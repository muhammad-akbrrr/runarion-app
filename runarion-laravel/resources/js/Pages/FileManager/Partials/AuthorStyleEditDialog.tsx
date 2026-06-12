import * as React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Textarea } from "@/Components/ui/textarea";
import { Label } from "@/Components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import { router } from "@inertiajs/react";
import { Save, X } from "lucide-react";
import { AuthorStyle } from "@/types/files";

interface AuthorStyleEditDialogProps {
    open: boolean;
    onClose: () => void;
    authorStyle: AuthorStyle | null;
    workspaceId: string;
}

type TechniqueCategory =
    | "voice"
    | "dialogue"
    | "description"
    | "exposition"
    | "pacing"
    | "narrative";

const TECHNIQUE_FIELDS: Record<
    TechniqueCategory,
    { key: string; label: string }[]
> = {
    voice: [
        { key: "diction", label: "Diction" },
        { key: "syntax", label: "Syntax" },
        { key: "rhythm", label: "Rhythm" },
        { key: "register", label: "Register" },
        { key: "figurative_language", label: "Figurative Language" },
    ],
    dialogue: [
        { key: "conversation_style", label: "Conversation Style" },
        { key: "speaker_differentiation", label: "Speaker Differentiation" },
        { key: "dialogue_narration_balance", label: "Dialogue-Narration Balance" },
    ],
    description: [
        { key: "description_density", label: "Description Density" },
        { key: "sensory_focus", label: "Sensory Focus" },
        { key: "atmosphere_strategy", label: "Atmosphere Strategy" },
    ],
    exposition: [
        { key: "exposition_strategy", label: "Exposition Strategy" },
        { key: "context_integration", label: "Context Integration" },
        { key: "terminology_handling", label: "Terminology Handling" },
    ],
    pacing: [
        { key: "scene_tempo", label: "Scene Tempo" },
        { key: "transition_style", label: "Transition Style" },
        { key: "tension_pattern", label: "Tension Pattern" },
    ],
    narrative: [
        { key: "pov_tendency", label: "POV Tendency" },
        { key: "narrative_distance", label: "Narrative Distance" },
        { key: "redundancy_avoidance", label: "Redundancy Avoidance" },
    ],
};

const CATEGORY_LABELS: Record<TechniqueCategory, string> = {
    voice: "Voice",
    dialogue: "Dialogue",
    description: "Description",
    exposition: "Exposition",
    pacing: "Pacing",
    narrative: "Narrative",
};

type AdaptationField =
    | "portable_traits"
    | "non_portable_markers"
    | "transfer_risks"
    | "suppression_guidance";

const ADAPTATION_FIELDS: { key: AdaptationField; label: string }[] = [
    { key: "portable_traits", label: "Portable Traits" },
    { key: "non_portable_markers", label: "Non-Portable Markers" },
    { key: "transfer_risks", label: "Transfer Risks" },
    { key: "suppression_guidance", label: "Suppression Guidance" },
];

type ExampleCategory = "voice" | "dialogue" | "description" | "exposition" | "pacing";

const EXAMPLE_CATEGORY_LABELS: Record<ExampleCategory, string> = {
    voice: "Voice",
    dialogue: "Dialogue",
    description: "Description",
    exposition: "Exposition",
    pacing: "Pacing",
};

export default function AuthorStyleEditDialog({
    open,
    onClose,
    authorStyle,
    workspaceId,
}: AuthorStyleEditDialogProps) {
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [authorName, setAuthorName] = React.useState("");
    const [techniques, setTechniques] = React.useState<
        AuthorStyle["techniques"]
    >({});
    const [examples, setExamples] = React.useState<AuthorStyle["examples"]>({});
    const [adaptation, setAdaptation] = React.useState<
        AuthorStyle["adaptation"]
    >({});
    const [error, setError] = React.useState<string | null>(null);

    // Load data when dialog opens
    React.useEffect(() => {
        if (open && authorStyle) {
            setAuthorName(authorStyle.name);
            setTechniques(authorStyle.techniques || {});
            setExamples(authorStyle.examples || {});
            setAdaptation(authorStyle.adaptation || {});
            setError(null);
        }
    }, [open, authorStyle]);

    // Update a technique field
    const updateTechnique = (
        category: TechniqueCategory,
        field: string,
        value: string,
    ) => {
        setTechniques((prev) => ({
            ...prev,
            [category]: {
                ...(prev?.[category] || {}),
                [field]: value,
            },
        }));
    };

    // Update examples for a category
    const updateExamples = (category: ExampleCategory, value: string) => {
        // Split by newlines to create array
        const examplesArray = value.split("\n").filter((line) => line.trim());
        setExamples((prev) => ({
            ...prev,
            [category]: examplesArray,
        }));
    };

    // Get examples as string for textarea
    const getExamplesString = (category: ExampleCategory): string => {
        return examples?.[category]?.join("\n") || "";
    };

    const updateAdaptation = (field: AdaptationField, value: string) => {
        const lines = value.split("\n").filter((line) => line.trim());
        setAdaptation((prev) => ({
            ...prev,
            [field]: lines,
        }));
    };

    const getAdaptationString = (field: AdaptationField): string => {
        return adaptation?.[field]?.join("\n") || "";
    };

    // Handle save
    const handleSave = () => {
        if (!authorStyle) return;

        setIsProcessing(true);
        setError(null);

        router.patch(
            route("workspace.artifacts.author-styles.update", {
                workspace_id: workspaceId,
                author_style_id: authorStyle.id,
            }),
            {
                author_name: authorName,
                techniques_json: techniques,
                examples_json: examples,
                adaptation_json: adaptation,
            },
            {
                preserveScroll: true,
                onSuccess: () => {
                    setIsProcessing(false);
                    onClose();
                },
                onError: (errors) => {
                    setIsProcessing(false);
                    const firstError = Object.values(errors)[0];
                    setError(
                        typeof firstError === "string"
                            ? firstError
                            : "Failed to update author style.",
                    );
                },
            },
        );
    };

    if (!authorStyle) return null;

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>Edit Author Style</DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto pr-2">
                    {/* Author Name */}
                    <div className="mb-6">
                        <Label htmlFor="author-name">Author Name</Label>
                        <Input
                            id="author-name"
                            value={authorName}
                            onChange={(e) => setAuthorName(e.target.value)}
                            placeholder="Author name"
                            className="mt-1"
                        />
                    </div>

                    <Tabs defaultValue="techniques" className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="techniques">
                                Techniques
                            </TabsTrigger>
                            <TabsTrigger value="examples">Examples</TabsTrigger>
                            <TabsTrigger value="adaptation">Adaptation</TabsTrigger>
                        </TabsList>

                        {/* Techniques Tab */}
                        <TabsContent value="techniques" className="mt-4">
                            <Accordion
                                type="multiple"
                                className="w-full"
                                defaultValue={["voice"]}
                            >
                                {(
                                    Object.keys(
                                        TECHNIQUE_FIELDS,
                                    ) as TechniqueCategory[]
                                ).map((category) => (
                                    <AccordionItem
                                        key={category}
                                        value={category}
                                    >
                                        <AccordionTrigger className="text-sm font-medium">
                                            {CATEGORY_LABELS[category]}
                                        </AccordionTrigger>
                                        <AccordionContent>
                                            <div className="space-y-4 pt-2">
                                                {TECHNIQUE_FIELDS[category].map(
                                                    (field) => (
                                                        <div key={field.key}>
                                                            <Label className="text-xs text-muted-foreground">
                                                                {field.label}
                                                            </Label>
                                                            <Textarea
                                                                value={
                                                                    techniques?.[
                                                                        category
                                                                    ]?.[
                                                                        field.key as keyof (typeof techniques)[typeof category]
                                                                    ] || ""
                                                                }
                                                                onChange={(e) =>
                                                                    updateTechnique(
                                                                        category,
                                                                        field.key,
                                                                        e.target
                                                                            .value,
                                                                    )
                                                                }
                                                                placeholder={`Describe ${field.label.toLowerCase()}...`}
                                                                className="mt-1 text-sm min-h-20"
                                                            />
                                                        </div>
                                                    ),
                                                )}
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        </TabsContent>

                        {/* Examples Tab */}
                        <TabsContent value="examples" className="mt-4">
                            <Accordion
                                type="multiple"
                                className="w-full"
                                defaultValue={["voice"]}
                            >
                                {(
                                    Object.keys(
                                        EXAMPLE_CATEGORY_LABELS,
                                    ) as ExampleCategory[]
                                ).map((category) => (
                                    <AccordionItem
                                        key={category}
                                        value={category}
                                    >
                                        <AccordionTrigger className="text-sm font-medium">
                                            {EXAMPLE_CATEGORY_LABELS[category]} Examples
                                        </AccordionTrigger>
                                        <AccordionContent>
                                            <div className="pt-2">
                                                <p className="text-xs text-muted-foreground mb-2">
                                                    Enter one example per line
                                                </p>
                                                <Textarea
                                                    value={getExamplesString(
                                                        category,
                                                    )}
                                                    onChange={(e) =>
                                                        updateExamples(
                                                            category,
                                                            e.target.value,
                                                        )
                                                    }
                                                    placeholder={`Enter ${EXAMPLE_CATEGORY_LABELS[category].toLowerCase()} examples, one per line...`}
                                                    className="text-sm min-h-[120px]"
                                                />
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        </TabsContent>

                        <TabsContent value="adaptation" className="mt-4">
                            <div className="space-y-4">
                                {ADAPTATION_FIELDS.map((field) => (
                                    <div key={field.key}>
                                        <Label className="text-xs text-muted-foreground">
                                            {field.label}
                                        </Label>
                                        <p className="text-xs text-muted-foreground mb-2">
                                            Enter one item per line
                                        </p>
                                        <Textarea
                                            value={getAdaptationString(field.key)}
                                            onChange={(e) =>
                                                updateAdaptation(field.key, e.target.value)
                                            }
                                            placeholder={`Enter ${field.label.toLowerCase()}...`}
                                            className="text-sm min-h-[120px]"
                                        />
                                    </div>
                                ))}
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>

                {error && (
                    <p className="text-sm text-destructive mt-2">{error}</p>
                )}

                {/* Footer */}
                <div className="flex flex-row items-center justify-between pt-4 border-t mt-4">
                    <Button variant="outline" onClick={onClose}>
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isProcessing || !authorName}
                    >
                        <Save className="h-4 w-4 mr-1" />
                        {isProcessing ? "Saving..." : "Save Changes"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
