import * as React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import { router } from "@inertiajs/react";
import { X, File, FileText, CloudUpload, Plus } from "lucide-react";
import { Switch } from "@/Components/ui/switch";

// Types for author styles and writing perspectives
interface AuthorStyle {
    id: string;
    author_name: string;
}

const WRITING_PERSPECTIVES = [
    { value: "1st-person", label: "1st-Person" },
    { value: "2nd-person", label: "2nd-Person" },
    { value: "omniscient", label: "Omniscient" },
    { value: "tpl", label: "TPL" },
];

interface OnboardingDialogProps {
    open: boolean;
    onClose: () => void;
    workspaceId: string;
    projectId: string;
    authorStyles: AuthorStyle[];
}

const INITIAL_FORM = {
    method: null as "scratch" | "draft" | null,
    draftFile: null as File | null,
    authorStyleType: "existing" as "existing" | "new",
    selectedAuthorStyle: "",
    newAuthorFiles: [] as File[],
    newAuthorName: "",
    writingPerspective: WRITING_PERSPECTIVES[0].value,
    summarize: false,
};

export default function OnboardingDialog({
    open,
    onClose,
    workspaceId,
    projectId,
    authorStyles,
}: OnboardingDialogProps) {
    const [step, setStep] = React.useState(0);
    const [form, setForm] = React.useState({ ...INITIAL_FORM });
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);

    // Reset state on open/close
    React.useEffect(() => {
        if (!open) {
            setStep(0);
            setForm({ ...INITIAL_FORM });
            setIsProcessing(false);
            setError(null);
        }
    }, [open]);

    // File input handlers
    const handleDraftFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setForm((prev) => ({ ...prev, draftFile: e.target.files![0] }));
        }
    };
    const handleNewAuthorFilesChange = (
        e: React.ChangeEvent<HTMLInputElement>
    ) => {
        if (e.target.files) {
            const files = Array.from(e.target.files).slice(0, 5);
            setForm((prev) => ({ ...prev, newAuthorFiles: files }));
        }
    };

    // Step navigation
    const nextStep = () => setStep((s) => s + 1);
    const prevStep = () => setStep((s) => s - 1);

    // Unified close handler
    const handleClose = () => {
        setStep(0);
        setForm({ ...INITIAL_FORM });
        setIsProcessing(false);
        setError(null);
        onClose();
    };

    // Form submission handlers
    const handleScratch = () => {
        setIsProcessing(true);
        setError(null);
        router.post(
            route("editor.project.onboarding", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            { method: "scratch" },
            {
                onSuccess: () => {
                    setIsProcessing(false);
                    handleClose();
                },
                onError: (errors: any) => {
                    setIsProcessing(false);
                    setError(errors?.method || "An error occurred.");
                },
            }
        );
    };

    const handleDraft = () => {
        setIsProcessing(true);
        setError(null);
        const data: Record<string, any> = {
            method: "draft",
            draft_file: form.draftFile,
            author_style_type: form.authorStyleType,
            author_style_id: form.selectedAuthorStyle,
            author_samples: form.newAuthorFiles,
            author_name: form.newAuthorName,
            writing_perspective: form.writingPerspective,
            summarize: form.summarize,
        };
        router.post(
            route("editor.project.onboarding", {
                workspace_id: workspaceId,
                project_id: projectId,
            }),
            data,
            {
                forceFormData: true,
                onSuccess: () => {
                    setIsProcessing(false);
                    window.location.reload();
                },
                onError: (errors: any) => {
                    setIsProcessing(false);
                    setError(
                        errors?.draft_file ||
                            errors?.author_name ||
                            errors?.method ||
                            "An error occurred."
                    );
                },
            }
        );
    };

    // UI rendering
    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="max-w-xl">
                {step === 0 && (
                    <>
                        <DialogHeader className="flex flex-row justify-center mb-2">
                            <DialogTitle>
                                Select a way to get started
                            </DialogTitle>
                        </DialogHeader>

                        <div className="grid grid-cols-2 gap-4">
                            <Button
                                variant="ghost"
                                className="p-6 border !w-auto !h-auto"
                                onClick={() => {
                                    setForm((prev) => ({
                                        ...prev,
                                        method: "scratch",
                                    }));
                                    handleScratch();
                                }}
                            >
                                <div className="flex flex-col gap-2 items-center w-full text-center">
                                    <File className="w-4 h-4" />
                                    <p className="font-semibold">
                                        Start from scratch
                                    </p>
                                    <p className="text-sm text-muted-foreground text-wrap">
                                        Build a custom project from scratch, let
                                        your imagination run wild
                                    </p>
                                </div>
                            </Button>

                            <Button
                                variant="ghost"
                                className="p-6 border !w-auto !h-auto"
                                onClick={() => {
                                    setForm((prev) => ({
                                        ...prev,
                                        method: "draft",
                                    }));
                                    nextStep();
                                }}
                            >
                                <div className="flex flex-col gap-2 items-center w-full text-center">
                                    <FileText className="w-4 h-4" />
                                    <p className="font-semibold">
                                        Start from draft
                                    </p>
                                    <p className="text-sm text-muted-foreground text-wrap">
                                        Build your project from an existing
                                        draft, with full control
                                    </p>
                                </div>
                            </Button>
                        </div>

                        <Button variant="outline" className="w-full">
                            Learn the basics with a tutorial
                        </Button>
                    </>
                )}
                {step === 1 && form.method === "draft" && (
                    <>
                        <DialogHeader className="flex flex-row justify-center mb-2">
                            <DialogTitle>Step 1: Upload your Draft</DialogTitle>
                        </DialogHeader>

                        <div className="border-dashed border-2 rounded-lg p-8 flex flex-col items-center justify-center gap-1 text-center relative mb-2">
                            <Input
                                type="file"
                                accept=".pdf"
                                onChange={handleDraftFileChange}
                                className="absolute left-0 top-0 w-full h-full opacity-0 cursor-pointer"
                            />
                            <CloudUpload className="w-5 h-5 text-muted-foreground mb-2" />
                            {!form.draftFile && (
                                <p className="font-semibold">
                                    Click or drag to upload
                                </p>
                            )}
                            {form.draftFile && (
                                <p className="font-semibold">
                                    {form.draftFile.name}
                                </p>
                            )}
                            <div className="w-4 h-0.5 bg-muted-foreground rounded-[1px]"></div>
                            <p className="text-muted-foreground text-xs">
                                Max file size: 100 MiB
                            </p>
                        </div>

                        <div className="flex flex-row items-center justify-between">
                            <Button variant="outline" onClick={prevStep}>
                                Back
                            </Button>
                            <Button
                                onClick={nextStep}
                                disabled={!form.draftFile}
                            >
                                Next
                            </Button>
                        </div>
                    </>
                )}
                {step === 2 && form.method === "draft" && (
                    <>
                        <DialogHeader className="flex flex-row justify-center mb-2">
                            <DialogTitle>
                                Step 2: Deconstructor Configuration
                            </DialogTitle>
                        </DialogHeader>

                        <div className="flex flex-col gap-4 mb-2">
                            <div className="flex flex-col justify-stretch items-start gap-2">
                                <div className="flex flex-col justify-start items-start gap-0.5">
                                    <label className="text-sm">
                                        Author Profile
                                    </label>
                                    <p className="text-xs text-muted-foreground">
                                        Select your existing profile or create
                                        one
                                    </p>
                                </div>
                                <div className="flex flex-row gap-2 items-center w-full">
                                    <Select
                                        value={
                                            form.authorStyleType === "existing"
                                                ? form.selectedAuthorStyle
                                                : ""
                                        }
                                        onValueChange={(val) => {
                                            setForm((prev) => ({
                                                ...prev,
                                                authorStyleType: "existing",
                                                selectedAuthorStyle: val,
                                            }));
                                        }}
                                    >
                                        <SelectTrigger className="w-full flex-grow">
                                            <SelectValue placeholder="Select one..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {authorStyles.map((style) => (
                                                <SelectItem
                                                    key={style.id}
                                                    value={style.id}
                                                >
                                                    {style.author_name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <Button
                                        variant="outline"
                                        onClick={() =>
                                            setForm((prev) => ({
                                                ...prev,
                                                authorStyleType: "new",
                                            }))
                                        }
                                        className="h-9 w-9"
                                    >
                                        <Plus className="h-4 w-4" />
                                    </Button>
                                </div>
                                {form.authorStyleType === "new" && (
                                    <div className="flex flex-col gap-2 w-full">
                                        <div className="border-dashed border-2 rounded-lg p-6 flex flex-col items-center justify-center gap-1 text-center relative mb-2">
                                            <Input
                                                className="absolute left-0 top-0 w-full h-full opacity-0 cursor-pointer"
                                                type="file"
                                                accept=".pdf"
                                                multiple
                                                onChange={
                                                    handleNewAuthorFilesChange
                                                }
                                            />
                                            <CloudUpload className="w-5 h-5 text-muted-foreground mb-2" />
                                            <p className="font-semibold">
                                                Click or drag to upload
                                            </p>
                                            <div className="w-4 h-0.5 bg-muted-foreground rounded-[1px]"></div>
                                            <p className="text-muted-foreground text-xs">
                                                Max file size: 100 MiB
                                            </p>
                                        </div>

                                        <div className="flex flex-col justify-stretch items-start gap-2 w-full">
                                            {form.newAuthorFiles.map(
                                                (file, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="flex items-center justify-between bg-muted p-2 rounded-md w-full"
                                                    >
                                                        <p className="text-xs">
                                                            {file.name}
                                                        </p>
                                                        <Button
                                                            className="!p-0 w-auto h-auto"
                                                            variant="ghost"
                                                            onClick={() =>
                                                                setForm(
                                                                    (prev) => ({
                                                                        ...prev,
                                                                        newAuthorFiles:
                                                                            prev.newAuthorFiles.filter(
                                                                                (
                                                                                    _,
                                                                                    i
                                                                                ) =>
                                                                                    i !==
                                                                                    idx
                                                                            ),
                                                                    })
                                                                )
                                                            }
                                                        >
                                                            <X className="h-2 w-2" />
                                                        </Button>
                                                    </div>
                                                )
                                            )}
                                        </div>

                                        <div className="flex flex-col justify-stretch items-start gap-2">
                                            <label className="text-sm">
                                                Save Author as...
                                            </label>
                                            <div className="flex flex-row items-stretch justify-between gap-2 w-full">
                                                <Input
                                                    className="w-full flex-grow"
                                                    placeholder="Save Author as..."
                                                    value={form.newAuthorName}
                                                    onChange={(e) =>
                                                        setForm((prev) => ({
                                                            ...prev,
                                                            newAuthorName:
                                                                e.target.value,
                                                        }))
                                                    }
                                                />
                                                <Button
                                                    onClick={() => {}}
                                                    disabled={
                                                        form.newAuthorFiles
                                                            .length === 0 ||
                                                        !form.newAuthorName
                                                    }
                                                >
                                                    Save
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-col justify-stretch items-start gap-2">
                                <div className="flex flex-col justify-start items-start gap-0.5">
                                    <label className="text-sm">
                                        Writing Perspective
                                    </label>
                                </div>
                                <Select
                                    value={form.writingPerspective}
                                    onValueChange={(val) =>
                                        setForm((prev) => ({
                                            ...prev,
                                            writingPerspective: val,
                                        }))
                                    }
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {WRITING_PERSPECTIVES.map((persp) => (
                                            <SelectItem
                                                key={persp.value}
                                                value={persp.value}
                                            >
                                                {persp.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="flex flex-row items-center justify-between gap-2">
                                <div className="flex flex-col justify-start items-start gap-0.5">
                                    <label className="text-sm">Summarize</label>
                                    <p className="text-xs text-muted-foreground">
                                        This will auto summarize your story upon
                                        completion
                                    </p>
                                </div>

                                <Switch checked={false} disabled={true} />
                            </div>
                        </div>

                        <div className="flex flex-row items-center justify-between">
                            <Button variant="outline" onClick={prevStep}>
                                Back
                            </Button>
                            <Button
                                onClick={handleDraft}
                                disabled={
                                    isProcessing ||
                                    (form.authorStyleType === "existing" &&
                                        !form.selectedAuthorStyle) ||
                                    (form.authorStyleType === "new" &&
                                        (form.newAuthorFiles.length === 0 ||
                                            !form.newAuthorName))
                                }
                            >
                                {isProcessing ? "Processing..." : "Start"}
                            </Button>
                        </div>
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}
