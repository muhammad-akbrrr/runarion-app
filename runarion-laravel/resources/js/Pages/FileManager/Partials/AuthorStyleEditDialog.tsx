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
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/Components/ui/tabs";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import { router, usePage } from "@inertiajs/react";
import { Save, X } from "lucide-react";
import { AuthorStyle } from "@/types/files";
import { PageProps } from "@/types";

interface AuthorStyleEditDialogProps {
    open: boolean;
    onClose: () => void;
    authorStyle: AuthorStyle | null;
    workspaceId: string;
}

type TechniqueCategory = 'dialogue' | 'action' | 'literary' | 'descriptions' | 'worldbuilding';

const TECHNIQUE_FIELDS: Record<TechniqueCategory, { key: string; label: string }[]> = {
    dialogue: [
        { key: 'conversation_style', label: 'Conversation Style' },
        { key: 'dialogue_balance', label: 'Dialogue Balance' },
        { key: 'character_voices', label: 'Character Voices' },
    ],
    action: [
        { key: 'action_sequences', label: 'Action Sequences' },
        { key: 'fight_scenes', label: 'Fight Scenes' },
        { key: 'tension', label: 'Tension Building' },
    ],
    literary: [
        { key: 'devices', label: 'Literary Devices' },
        { key: 'metaphors', label: 'Metaphors & Similes' },
        { key: 'pacing', label: 'Pacing' },
        { key: 'transitions', label: 'Transitions' },
        { key: 'word_patterns', label: 'Word Patterns' },
        { key: 'scene_structure', label: 'Scene Structure' },
    ],
    descriptions: [
        { key: 'atmosphere', label: 'Atmosphere' },
        { key: 'scene_painting', label: 'Scene Painting' },
        { key: 'character_descriptions', label: 'Character Descriptions' },
    ],
    worldbuilding: [
        { key: 'world_reveals', label: 'World Reveals' },
        { key: 'exposition', label: 'Exposition' },
        { key: 'history_magic', label: 'History & Magic' },
    ],
};

const CATEGORY_LABELS: Record<TechniqueCategory, string> = {
    dialogue: 'Dialogue',
    action: 'Action & Combat',
    literary: 'Literary Techniques',
    descriptions: 'Descriptions',
    worldbuilding: 'Worldbuilding',
};

export default function AuthorStyleEditDialog({
    open,
    onClose,
    authorStyle,
    workspaceId,
}: AuthorStyleEditDialogProps) {
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [authorName, setAuthorName] = React.useState("");
    const [techniques, setTechniques] = React.useState<AuthorStyle['techniques']>({});
    const [examples, setExamples] = React.useState<AuthorStyle['examples']>({});
    const [error, setError] = React.useState<string | null>(null);

    // Load data when dialog opens
    React.useEffect(() => {
        if (open && authorStyle) {
            setAuthorName(authorStyle.name);
            setTechniques(authorStyle.techniques || {});
            setExamples(authorStyle.examples || {});
            setError(null);
        }
    }, [open, authorStyle]);

    // Update a technique field
    const updateTechnique = (category: TechniqueCategory, field: string, value: string) => {
        setTechniques(prev => ({
            ...prev,
            [category]: {
                ...(prev?.[category] || {}),
                [field]: value,
            },
        }));
    };

    // Update examples for a category
    const updateExamples = (category: TechniqueCategory, value: string) => {
        // Split by newlines to create array
        const examplesArray = value.split('\n').filter(line => line.trim());
        setExamples(prev => ({
            ...prev,
            [category]: examplesArray,
        }));
    };

    // Get examples as string for textarea
    const getExamplesString = (category: TechniqueCategory): string => {
        return examples?.[category]?.join('\n') || '';
    };

    // Handle save
    const handleSave = () => {
        if (!authorStyle) return;
        
        setIsProcessing(true);
        setError(null);

        router.patch(
            route("workspace.files.author-styles.update", { 
                workspace_id: workspaceId, 
                author_style_id: authorStyle.id 
            }),
            {
                author_name: authorName,
                techniques_json: techniques,
                examples_json: examples,
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
                    setError(typeof firstError === 'string' ? firstError : 'Failed to update author style.');
                },
            }
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
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="techniques">Techniques</TabsTrigger>
                            <TabsTrigger value="examples">Examples</TabsTrigger>
                        </TabsList>

                        {/* Techniques Tab */}
                        <TabsContent value="techniques" className="mt-4">
                            <Accordion type="multiple" className="w-full" defaultValue={['dialogue']}>
                                {(Object.keys(TECHNIQUE_FIELDS) as TechniqueCategory[]).map((category) => (
                                    <AccordionItem key={category} value={category}>
                                        <AccordionTrigger className="text-sm font-medium">
                                            {CATEGORY_LABELS[category]}
                                        </AccordionTrigger>
                                        <AccordionContent>
                                            <div className="space-y-4 pt-2">
                                                {TECHNIQUE_FIELDS[category].map((field) => (
                                                    <div key={field.key}>
                                                        <Label className="text-xs text-muted-foreground">
                                                            {field.label}
                                                        </Label>
                                                        <Textarea
                                                            value={techniques?.[category]?.[field.key as keyof typeof techniques[typeof category]] || ''}
                                                            onChange={(e) => updateTechnique(category, field.key, e.target.value)}
                                                            placeholder={`Describe ${field.label.toLowerCase()}...`}
                                                            className="mt-1 text-sm min-h-[80px]"
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        </TabsContent>

                        {/* Examples Tab */}
                        <TabsContent value="examples" className="mt-4">
                            <Accordion type="multiple" className="w-full" defaultValue={['dialogue']}>
                                {(Object.keys(CATEGORY_LABELS) as TechniqueCategory[]).map((category) => (
                                    <AccordionItem key={category} value={category}>
                                        <AccordionTrigger className="text-sm font-medium">
                                            {CATEGORY_LABELS[category]} Examples
                                        </AccordionTrigger>
                                        <AccordionContent>
                                            <div className="pt-2">
                                                <p className="text-xs text-muted-foreground mb-2">
                                                    Enter one example per line
                                                </p>
                                                <Textarea
                                                    value={getExamplesString(category)}
                                                    onChange={(e) => updateExamples(category, e.target.value)}
                                                    placeholder={`Enter ${CATEGORY_LABELS[category].toLowerCase()} examples, one per line...`}
                                                    className="text-sm min-h-[120px]"
                                                />
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
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
                    <Button onClick={handleSave} disabled={isProcessing || !authorName}>
                        <Save className="h-4 w-4 mr-1" />
                        {isProcessing ? "Saving..." : "Save Changes"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

