import { useState, useEffect } from "react";
import ProjectEditorLayout from "@/Layouts/ProjectEditorLayout";
import { PageProps, Project, ProjectChapter } from "@/types";
import { Head } from "@inertiajs/react";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Textarea } from "@/Components/ui/textarea";
import { Label } from "@/Components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/Components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/Components/ui/collapsible";
import { Slider } from "@/Components/ui/slider";
import { Switch } from "@/Components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/Components/ui/select";
import { Separator } from "@/Components/ui/separator";
import { 
    Loader2, 
    Image as ImageIcon, 
    FileText, 
    Download, 
    Settings, 
    ChevronDown,
    RefreshCw,
    ZoomIn,
    ZoomOut,
    Trash2,
    Grid3x3,
    X,
    Search,
    Filter
} from "lucide-react";

interface GeneratedImage {
    image: string;
    imageBytes: string;
    chapterOrder: number;
    prompt: string;
    settings: GenerationSettings;
}

interface GenerationSettings {
    width: number;
    height: number;
    numInferenceSteps: number;
    guidanceScale: number;
    seed?: number;
    transparentBackground: boolean;
    borderTemplate?: string | null;
    negativePrompt: string;
    blackAndWhite: boolean;
    stylePreset: 'none' | 'line-art' | 'manga' | 'watercolor' | 'sketch' | 'oil-painting';
}

interface PDFSettings {
    paperSize: 'a4' | 'letter';
    includeCovers: boolean;
    fontName: string;
    fontSize: number;
    lineSpacing: number;
    margins: {
        top: number;
        bottom: number;
        left: number;
        right: number;
    };
    // New features
    dropCap: boolean;
    dropCapFont: string;
    dropCapUppercase: boolean;
    chapterBorders: boolean;
    includeToc: boolean;
}

export default function ProjectEditorPage({
    workspaceId,
    projectId,
    project,
    chapters = [],
}: PageProps<{
    workspaceId: string;
    projectId: string;
    project: Project;
    chapters?: ProjectChapter[];
}>) {
    const [activeTab, setActiveTab] = useState<'generator' | 'preview'>('generator');
    
    const [selectedChapter, setSelectedChapter] = useState<ProjectChapter | null>(null);
    const [prompt, setPrompt] = useState("");
    const [generating, setGenerating] = useState(false);
    
    // Store images per chapter
    const [chapterImages, setChapterImages] = useState<Map<number, GeneratedImage>>(new Map());
    
    const [generatingPDF, setGeneratingPDF] = useState(false);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    
    // Generation settings with localStorage persistence
    const STORAGE_KEY = `img_gen_settings_${projectId}`;
    
    // Load settings from localStorage on mount
    const loadGenSettings = (): GenerationSettings => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                return {
                    width: parsed.width ?? 768,
                    height: parsed.height ?? 768,
                    numInferenceSteps: parsed.numInferenceSteps ?? 20,
                    guidanceScale: parsed.guidanceScale ?? 5,
                    seed: parsed.seed,
                    transparentBackground: parsed.transparentBackground ?? false,
                    borderTemplate: parsed.borderTemplate ?? null,
                    negativePrompt: parsed.negativePrompt ?? "text, watermark, signature, low quality, blurry, deformed",
                    blackAndWhite: parsed.blackAndWhite ?? false,
                    stylePreset: parsed.stylePreset ?? 'none',
                };
            }
        } catch (error) {
            console.error("Error loading generation settings:", error);
        }
        // Default settings (optimized for RTX 3060 6GB)
        return {
            width: 768,
            height: 768,
            numInferenceSteps: 20,
            guidanceScale: 5,
            seed: undefined,
            transparentBackground: false,
            borderTemplate: null,
            negativePrompt: "text, watermark, signature, low quality, blurry, deformed",
            blackAndWhite: false,
            stylePreset: 'none',
        };
    };
    
    const [genSettings, setGenSettings] = useState<GenerationSettings>(loadGenSettings());
    
    // Save settings to localStorage whenever they change
    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(genSettings));
        } catch (error) {
            console.error("Error saving generation settings:", error);
        }
    }, [genSettings, STORAGE_KEY]);
    
    // Border templates
    const [borderTemplates, setBorderTemplates] = useState<string[]>([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);
    const [generatingBorder, setGeneratingBorder] = useState(false);
    const [showBorderGenerator, setShowBorderGenerator] = useState(false);
    const [borderPrompt, setBorderPrompt] = useState("ornate decorative border frame, intricate patterns, elegant design");
    const [borderSettings, setBorderSettings] = useState({
        borderThickness: 80,
        borderStyle: 'rectangular' as 'rectangular' | 'circular' | 'ornate',
        templateName: '',
    });
    
    // PDF settings
    const [pdfSettings, setPdfSettings] = useState<PDFSettings>({
        paperSize: 'a4',
        includeCovers: true,
        fontName: 'Times-Roman',
        fontSize: 12,
        lineSpacing: 1.5,
        // New features
        dropCap: true,
        dropCapFont: 'UnifrakturCook',
        dropCapUppercase: true,
        chapterBorders: false,
        includeToc: true,
        margins: {
            top: 1.0,
            bottom: 1.0,
            left: 1.25,
            right: 1.25,
        },
    });
    
    const [showGenSettings, setShowGenSettings] = useState(false);
    const [showPdfSettings, setShowPdfSettings] = useState(false);
    const [imageZoom, setImageZoom] = useState(100);
    const [showGallery, setShowGallery] = useState(false);
    const [gallerySearch, setGallerySearch] = useState("");
    const [galleryFilter, setGalleryFilter] = useState<'all' | 'with-covers' | 'without-covers' | 'borders'>('all');
    const [showBorderGallery, setShowBorderGallery] = useState(false);

    // Get current chapter's generated image
    const currentImage = selectedChapter ? chapterImages.get(selectedChapter.order) : null;

    // Auto-fill prompt from chapter content
    useEffect(() => {
        if (selectedChapter && selectedChapter.content && !prompt) {
            const chapterTitle = selectedChapter.chapter_name || "Chapter";
            const contentPreview = selectedChapter.content.substring(0, 200);
            setPrompt(`A book cover illustration for "${chapterTitle}". ${contentPreview}...`);
        }
    }, [selectedChapter]);
    
    // Load border templates on mount
    useEffect(() => {
        const loadBorderTemplates = async () => {
            setLoadingTemplates(true);
            try {
                const response = await fetch(`/${workspaceId}/projects/${projectId}/editor/image/border-templates`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.templates) {
                        setBorderTemplates(data.templates);
                    }
                }
            } catch (error) {
                console.error("Failed to load border templates:", error);
            } finally {
                setLoadingTemplates(false);
            }
        };
        loadBorderTemplates();
    }, [workspaceId, projectId]);

    const handleGenerateCover = async () => {
        if (!prompt.trim() || !selectedChapter) {
            alert("Please select a chapter and enter a prompt");
            return;
        }

        setGenerating(true);

        // Build the final prompt with style preset and B&W modifiers
        const stylePresets: Record<string, string> = {
            'none': '',
            'line-art': 'line art illustration, black ink drawing, clean lines, detailed linework, ',
            'manga': 'manga style illustration, anime art, japanese comic style, ',
            'watercolor': 'watercolor painting, soft colors, artistic brushstrokes, ',
            'sketch': 'pencil sketch, hand-drawn, artistic sketch style, ',
            'oil-painting': 'oil painting style, classical art, painterly brushstrokes, ',
        };
        
        let finalPrompt = prompt;
        const stylePrefix = stylePresets[genSettings.stylePreset] || '';
        if (stylePrefix) {
            finalPrompt = stylePrefix + finalPrompt;
        }
        if (genSettings.blackAndWhite) {
            finalPrompt = finalPrompt + ', monochrome, black and white, grayscale';
        }
        
        // Build negative prompt
        let finalNegativePrompt = genSettings.negativePrompt;
        if (genSettings.blackAndWhite) {
            finalNegativePrompt = finalNegativePrompt + ', color, colorful, vibrant colors';
        }

        // Log the settings being sent for verification
        const requestBody = {
            prompt: finalPrompt,
            negative_prompt: finalNegativePrompt,
            chapter_id: selectedChapter.order,
            width: genSettings.width,
            height: genSettings.height,
            num_inference_steps: genSettings.numInferenceSteps,
            guidance_scale: genSettings.guidanceScale,
            seed: genSettings.seed || null,
            transparent_background: genSettings.transparentBackground,
            border_template_path: genSettings.borderTemplate || null,
        };
        
        console.log("🚀 Generating cover with settings:", {
            size: `${requestBody.width}x${requestBody.height}`,
            steps: requestBody.num_inference_steps,
            guidance: requestBody.guidance_scale,
            seed: requestBody.seed,
            transparent: requestBody.transparent_background,
        });

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes for SDXL generation

            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/image/generate-cover`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify(requestBody),
                    signal: controller.signal,
                }
            );

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json();
                const errorMessage = error.error || error.details || "Failed to generate cover";
                
                // Preserve "still loading" messages - don't convert them to "not running"
                if (errorMessage.includes("still loading") || errorMessage.includes("initializing") || errorMessage.includes("loading models")) {
                    throw new Error(errorMessage); // Keep the original message
                }
                
                // Only convert to "not running" for actual connection errors
                if (errorMessage.includes("not running") || errorMessage.includes("not available") || errorMessage.includes("Could not connect")) {
                    throw new Error("Stable Diffusion service is not running. Image generation requires Stable Diffusion to be started. PDF generation works without it.");
                }
                
                throw new Error(errorMessage);
            }

            const data = await response.json();
            if (data.success && data.image) {
                const newImage: GeneratedImage = {
                    image: data.image,
                    imageBytes: data.image_bytes,
                    chapterOrder: selectedChapter.order,
                    prompt: prompt,
                    settings: { ...genSettings },
                };
                
                setChapterImages(prev => {
                    const newMap = new Map(prev);
                    newMap.set(selectedChapter.order, newImage);
                    return newMap;
                });
                
                // Switch to generator tab to show the image
                setActiveTab('generator');
            } else {
                throw new Error("No image returned");
            }
        } catch (error: any) {
            console.error("Error generating cover:", error);
            let errorMsg = error.message || "Failed to generate cover";
            
            if (error.name === 'AbortError' || errorMsg.includes('timeout')) {
                errorMsg = "Generation timed out. SDXL generation can take 5-10 minutes. Please try again or check if Stable Diffusion is running properly.";
            }
            
            if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
                errorMsg = "Network error. Please check your connection and try again.";
            }
            
            // Show "still loading" messages properly
            if (errorMsg.includes("still loading") || errorMsg.includes("initializing") || errorMsg.includes("loading models")) {
                alert(`Stable Diffusion is still initializing:\n\n${errorMsg}\n\nPlease wait for the models to finish loading (this can take 15-30 minutes on first run).`);
            } else if (errorMsg.includes("Stable Diffusion") && (errorMsg.includes("not running") || errorMsg.includes("not available"))) {
                alert("Stable Diffusion service is not running.\n\nImage generation requires Stable Diffusion to be started.\n\nPDF generation works without it - try generating a PDF instead!");
            } else {
                alert(`Failed to generate cover: ${errorMsg}`);
            }
        } finally {
            setGenerating(false);
        }
    };

    const handleRegenerateCover = () => {
        if (currentImage) {
            handleGenerateCover();
        }
    };

    const handleDownloadImage = () => {
        if (currentImage) {
            const link = document.createElement("a");
            link.href = currentImage.image;
            link.download = `chapter-${selectedChapter?.order}-cover.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    const handleDeleteImage = (chapterOrder: number) => {
        if (confirm(`Delete cover for ${chapters.find(c => c.order === chapterOrder)?.chapter_name || `Chapter ${chapterOrder}`}?`)) {
            setChapterImages(prev => {
                const newMap = new Map(prev);
                newMap.delete(chapterOrder);
                return newMap;
            });
            if (selectedChapter?.order === chapterOrder) {
                setSelectedChapter(null);
            }
        }
    };
    
    const handleGenerateBorder = async () => {
        if (!borderSettings.templateName.trim()) {
            alert("Please enter a template name");
            return;
        }
        
        setGeneratingBorder(true);
        
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/image/generate-border`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN':
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        prompt: borderPrompt,
                        width: genSettings.width,
                        height: genSettings.height,
                        border_thickness: borderSettings.borderThickness,
                        border_style: borderSettings.borderStyle,
                        template_name: borderSettings.templateName,
                        num_inference_steps: genSettings.numInferenceSteps,
                        guidance_scale: genSettings.guidanceScale,
                        seed: genSettings.seed || null,
                    }),
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || "Failed to generate border");
            }
            
            const data = await response.json();
            if (data.success) {
                // Reload border templates
                const templatesResponse = await fetch(`/${workspaceId}/projects/${projectId}/editor/image/border-templates`);
                if (templatesResponse.ok) {
                    const templatesData = await templatesResponse.json();
                    if (templatesData.templates) {
                        setBorderTemplates(templatesData.templates);
                        // Auto-select the newly generated border
                        setGenSettings(prev => ({ ...prev, borderTemplate: borderSettings.templateName }));
                    }
                }
                setShowBorderGenerator(false);
                setBorderSettings(prev => ({ ...prev, templateName: '' }));
                alert("Border template generated and saved successfully!");
            }
        } catch (error: any) {
            console.error("Error generating border:", error);
            alert(`Failed to generate border: ${error.message}`);
        } finally {
            setGeneratingBorder(false);
        }
    };

    const handleSelectChapterFromGallery = (chapterOrder: number) => {
        const chapter = chapters.find(c => c.order === chapterOrder);
        if (chapter) {
            setSelectedChapter(chapter);
            setActiveTab('generator');
        }
    };

    const handleGeneratePDF = async () => {
        if (chapters.length === 0) {
            alert("No chapters available");
            return;
        }

        setGeneratingPDF(true);
        setPdfUrl(null);

        try {
            const chaptersWithCovers = chapters.map((chapter) => {
                const chapterData: any = {
                    title: chapter.chapter_name || `Chapter ${chapter.order}`,
                    content: chapter.content || "",
                };
                
                const chapterImage = chapterImages.get(chapter.order);
                if (chapterImage && pdfSettings.includeCovers) {
                    let imageBytes = chapterImage.imageBytes;
                    if (imageBytes.startsWith('data:')) {
                        imageBytes = imageBytes.split(',')[1];
                    }
                    chapterData.cover_image_bytes = imageBytes;
                }
                
                return chapterData;
            });

            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/image/generate-pdf`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-TOKEN":
                            document
                                .querySelector('meta[name="csrf-token"]')
                                ?.getAttribute("content") || "",
                    },
                    body: JSON.stringify({
                        chapters: chaptersWithCovers,
                        paper_size: pdfSettings.paperSize,
                        margins: pdfSettings.margins,
                        font_name: pdfSettings.fontName,
                        font_size: pdfSettings.fontSize,
                        line_spacing: pdfSettings.lineSpacing,
                        include_covers: pdfSettings.includeCovers,
                        // New features
                        drop_cap: pdfSettings.dropCap,
                        drop_cap_font: pdfSettings.dropCapFont,
                        drop_cap_uppercase: pdfSettings.dropCapUppercase,
                        chapter_borders: pdfSettings.chapterBorders,
                        include_toc: pdfSettings.includeToc,
                    }),
                }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || "Failed to generate PDF");
            }

            const data = await response.json();
            if (data.success && data.pdf) {
                setPdfUrl(data.pdf);
                // Switch to preview tab to show the PDF
                setActiveTab('preview');
            } else {
                throw new Error("No PDF returned");
            }
        } catch (error: any) {
            console.error("Error generating PDF:", error);
            alert(`Failed to generate PDF: ${error.message}`);
        } finally {
            setGeneratingPDF(false);
        }
    };

    const handleDownloadPDF = () => {
        if (pdfUrl) {
            const link = document.createElement("a");
            link.href = pdfUrl;
            link.download = `${project.name || "book"}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    const chaptersWithCovers = chapters.filter(ch => chapterImages.has(ch.order)).length;

    return (
        <ProjectEditorLayout
            project={project}
            projectId={projectId}
            workspaceId={workspaceId}
        >
            <Head title="Book Preview - Image & PDF Generator" />
            
            <div className="w-full h-full flex gap-0 bg-gray-50">
                {/* Left Viewport */}
                <div className="flex-1 flex flex-col bg-white border-r border-gray-200">
                    {/* Generator Viewport */}
                    {activeTab === 'generator' && (
                        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50">
                            {generating ? (
                                <div className="flex flex-col items-center gap-4">
                                    <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
                                    <div className="text-center">
                                        <p className="text-lg font-semibold text-gray-700">Generating Cover...</p>
                                        <p className="text-sm text-gray-500 mt-2">This typically takes 30-60 seconds</p>
                                    </div>
                                </div>
                            ) : currentImage ? (
                                <div className="flex flex-col items-center gap-4 w-full h-full">
                                    <div className="flex items-center gap-2 mb-4">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setImageZoom(prev => Math.max(50, prev - 10))}
                                            disabled={imageZoom <= 50}
                                        >
                                            <ZoomOut className="h-4 w-4" />
                                        </Button>
                                        <span className="text-sm text-gray-600 min-w-[60px] text-center">{imageZoom}%</span>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setImageZoom(prev => Math.min(200, prev + 10))}
                                            disabled={imageZoom >= 200}
                                        >
                                            <ZoomIn className="h-4 w-4" />
                                        </Button>
                                        <Separator orientation="vertical" className="h-6" />
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setShowGallery(true)}
                                        >
                                            <Grid3x3 className="h-4 w-4 mr-1" />
                                            Gallery
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={handleRegenerateCover}
                                            disabled={generating}
                                        >
                                            <RefreshCw className="h-4 w-4 mr-1" />
                                            Regenerate
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={handleDownloadImage}
                                        >
                                            <Download className="h-4 w-4 mr-1" />
                                            Download
                                        </Button>
                                    </div>
                                    <div className="flex-1 flex items-center justify-center w-full overflow-auto">
                                        <img
                                            src={currentImage.image}
                                            alt="Generated chapter cover"
                                            className="max-w-full max-h-full object-contain shadow-2xl rounded-lg"
                                            style={{ transform: `scale(${imageZoom / 100})` }}
                                        />
                                    </div>
                                    <div className="mt-4 p-4 bg-white rounded-lg border border-gray-200 max-w-2xl w-full">
                                        <p className="text-sm text-gray-600"><strong>Chapter:</strong> {selectedChapter?.chapter_name || `Chapter ${selectedChapter?.order}`}</p>
                                        <p className="text-sm text-gray-600 mt-1"><strong>Prompt:</strong> {currentImage.prompt}</p>
                                        <p className="text-xs text-gray-500 mt-2">
                                            {currentImage.settings.width}×{currentImage.settings.height} • {currentImage.settings.numInferenceSteps} steps • Guidance {currentImage.settings.guidanceScale}
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center gap-4 text-center text-gray-500">
                                    <ImageIcon className="h-16 w-16 text-gray-300" />
                                    <p className="text-lg font-medium">No Cover Generated</p>
                                    <p className="text-sm">Select a chapter and generate a cover to see it here</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* PDF Preview Viewport */}
                    {activeTab === 'preview' && (
                        <div className="flex-1 flex flex-col bg-gray-50">
                            {generatingPDF ? (
                                <div className="flex-1 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-4">
                                        <Loader2 className="h-12 w-12 animate-spin text-green-600" />
                                        <div className="text-center">
                                            <p className="text-lg font-semibold text-gray-700">Generating PDF...</p>
                                            <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
                                        </div>
                                    </div>
                                </div>
                            ) : pdfUrl ? (
                                <div className="flex-1 flex flex-col">
                                    <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                                        <h3 className="font-semibold text-gray-700">PDF Preview</h3>
                                        <Button
                                            onClick={handleDownloadPDF}
                                            variant="outline"
                                            size="sm"
                                        >
                                            <Download className="h-4 w-4 mr-1" />
                                            Download PDF
                                        </Button>
                                    </div>
                                    <div className="flex-1 overflow-auto bg-gray-100 p-4">
                                        <iframe
                                            src={pdfUrl}
                                            className="w-full h-full min-h-[600px] bg-white shadow-lg rounded"
                                            title="PDF Preview"
                                        />
                                    </div>
                                </div>
                            ) : (
                                <div className="flex-1 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-4 text-center text-gray-500">
                                        <FileText className="h-16 w-16 text-gray-300" />
                                        <p className="text-lg font-medium">No PDF Generated</p>
                                        <p className="text-sm">Generate a PDF preview to see it here</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Right Sidebar */}
                <div className="w-96 flex flex-col bg-white border-l border-gray-200">
                    <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'generator' | 'preview')} className="flex flex-col h-full">
                        <div className="p-4 border-b border-gray-200">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="generator" className="flex items-center gap-2">
                                    <ImageIcon className="h-4 w-4" />
                                    Chapter Generator
                                </TabsTrigger>
                                <TabsTrigger value="preview" className="flex items-center gap-2">
                                    <FileText className="h-4 w-4" />
                                    Book Preview PDF
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {/* Chapter Generator Tab */}
                            <TabsContent value="generator" className="mt-0 p-4 space-y-4">
                                {/* Chapter Selection */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-sm font-semibold">Select Chapter</Label>
                                        {chapterImages.size > 0 && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => setShowGallery(true)}
                                                className="h-7 text-xs"
                                            >
                                                <Grid3x3 className="h-3 w-3 mr-1" />
                                                Gallery ({chapterImages.size})
                                            </Button>
                                        )}
                                    </div>
                                    <Select
                                        value={selectedChapter?.order?.toString() || ""}
                                        onValueChange={(value) => {
                                            if (!value) {
                                                setSelectedChapter(null);
                                                return;
                                            }
                                            const order = parseInt(value);
                                            const chapter = chapters.find((c) => c.order === order);
                                            setSelectedChapter(chapter || null);
                                            if (chapter && !prompt) {
                                                const contentPreview = chapter.content?.substring(0, 200) || "";
                                                setPrompt(`A book cover illustration for "${chapter.chapter_name || 'Chapter'}". ${contentPreview}...`);
                                            }
                                        }}
                                        disabled={generating}
                                    >
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select a chapter...">
                                                {selectedChapter ? (selectedChapter.chapter_name || `Chapter ${selectedChapter.order}`) : "Select a chapter..."}
                                            </SelectValue>
                                        </SelectTrigger>
                                        <SelectContent>
                                            {chapters.map((chapter) => (
                                                <SelectItem key={chapter.order} value={chapter.order.toString()}>
                                                    {chapter.chapter_name || `Chapter ${chapter.order}`}
                                                    {chapterImages.has(chapter.order) && " ✓"}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {selectedChapter && (
                                        <div className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs">
                                            <span className="text-gray-600">
                                                {selectedChapter.chapter_name || `Chapter ${selectedChapter.order}`}
                                            </span>
                                            {chapterImages.has(selectedChapter.order) && (
                                                <span className="text-green-600 font-medium">Cover exists</span>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Prompt Input */}
                                <div className="space-y-2">
                                    <Label className="text-sm font-semibold">Prompt</Label>
                                    <Textarea
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        placeholder="Describe the chapter cover you want to generate..."
                                        rows={4}
                                        className="w-full resize-none"
                                        disabled={generating}
                                    />
                                </div>
                                
                                {/* Negative Prompt */}
                                <div className="space-y-2">
                                    <Label className="text-sm font-semibold">Negative Prompt</Label>
                                    <Textarea
                                        value={genSettings.negativePrompt}
                                        onChange={(e) => setGenSettings(prev => ({ ...prev, negativePrompt: e.target.value }))}
                                        placeholder="What to avoid in the image..."
                                        rows={2}
                                        className="w-full resize-none text-sm"
                                        disabled={generating}
                                    />
                                </div>
                                
                                {/* Style Preset */}
                                <div className="space-y-2">
                                    <Label className="text-sm font-semibold">Style Preset</Label>
                                    <Select
                                        value={genSettings.stylePreset}
                                        onValueChange={(value: GenerationSettings['stylePreset']) => 
                                            setGenSettings(prev => ({ ...prev, stylePreset: value }))
                                        }
                                        disabled={generating}
                                    >
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select style..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="none">None (Realistic)</SelectItem>
                                            <SelectItem value="line-art">Line Art / Ink</SelectItem>
                                            <SelectItem value="manga">Manga / Anime</SelectItem>
                                            <SelectItem value="watercolor">Watercolor</SelectItem>
                                            <SelectItem value="sketch">Pencil Sketch</SelectItem>
                                            <SelectItem value="oil-painting">Oil Painting</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                
                                {/* Black & White Toggle */}
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div>
                                        <Label className="text-sm font-medium">Black & White</Label>
                                        <p className="text-xs text-gray-500">Generate monochrome image</p>
                                    </div>
                                    <Switch
                                        checked={genSettings.blackAndWhite}
                                        onCheckedChange={(checked) => setGenSettings(prev => ({ ...prev, blackAndWhite: checked }))}
                                        disabled={generating}
                                    />
                                </div>

                                {/* Generation Settings */}
                                <Collapsible open={showGenSettings} onOpenChange={setShowGenSettings}>
                                    <CollapsibleTrigger asChild>
                                        <Button variant="outline" className="w-full justify-between">
                                            <span className="flex items-center gap-2">
                                                <Settings className="h-4 w-4" />
                                                Generation Settings
                                            </span>
                                            <ChevronDown className={`h-4 w-4 transition-transform ${showGenSettings ? 'rotate-180' : ''}`} />
                                        </Button>
                                    </CollapsibleTrigger>
                                    <CollapsibleContent className="space-y-4 pt-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label className="text-xs">Width: {genSettings.width}px</Label>
                                                <Slider
                                                    value={[genSettings.width]}
                                                    onValueChange={([val]) => setGenSettings(prev => ({ ...prev, width: val }))}
                                                    min={512}
                                                    max={2048}
                                                    step={64}
                                                    disabled={generating}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label className="text-xs">Height: {genSettings.height}px</Label>
                                                <Slider
                                                    value={[genSettings.height]}
                                                    onValueChange={([val]) => setGenSettings(prev => ({ ...prev, height: val }))}
                                                    min={512}
                                                    max={2048}
                                                    step={64}
                                                    disabled={generating}
                                                />
                                            </div>
                                        </div>
                                        
                                        <div className="space-y-2">
                                            <Label className="text-xs">Inference Steps: {genSettings.numInferenceSteps}</Label>
                                            <Slider
                                                value={[genSettings.numInferenceSteps]}
                                                onValueChange={([val]) => setGenSettings(prev => ({ ...prev, numInferenceSteps: val }))}
                                                min={10}
                                                max={50}
                                                step={5}
                                                disabled={generating}
                                            />
                                        </div>
                                        
                                        <div className="space-y-2">
                                            <Label className="text-xs">Guidance Scale: {genSettings.guidanceScale}</Label>
                                            <Slider
                                                value={[genSettings.guidanceScale]}
                                                onValueChange={([val]) => setGenSettings(prev => ({ ...prev, guidanceScale: val }))}
                                                min={1}
                                                max={20}
                                                step={0.5}
                                                disabled={generating}
                                            />
                                        </div>
                                        
                                        <div className="space-y-2">
                                            <Label className="text-xs">Seed (optional)</Label>
                                            <Input
                                                type="number"
                                                value={genSettings.seed || ''}
                                                onChange={(e) => setGenSettings(prev => ({ 
                                                    ...prev, 
                                                    seed: e.target.value ? parseInt(e.target.value) : undefined 
                                                }))}
                                                placeholder="Random"
                                                disabled={generating}
                                            />
                                        </div>
                                        
                                        <div className="flex items-center justify-between">
                                            <Label className="text-sm">Transparent Background</Label>
                                            <Switch
                                                checked={genSettings.transparentBackground}
                                                onCheckedChange={(checked) => setGenSettings(prev => ({ ...prev, transparentBackground: checked }))}
                                                disabled={generating}
                                            />
                                        </div>
                                        
                                        <Separator />
                                        
                                        <div className="space-y-2">
                                            <Label className="text-sm">Border Template (Optional)</Label>
                                            <Select
                                                value={genSettings.borderTemplate || "none"}
                                                onValueChange={(value) => setGenSettings(prev => ({ 
                                                    ...prev, 
                                                    borderTemplate: value === "none" ? null : value 
                                                }))}
                                                disabled={generating || loadingTemplates}
                                            >
                                                <SelectTrigger className="w-full">
                                                    <SelectValue placeholder="No border">
                                                        {genSettings.borderTemplate ? genSettings.borderTemplate : "No border"}
                                                    </SelectValue>
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="none">No border</SelectItem>
                                                    {borderTemplates.map((template) => (
                                                        <SelectItem key={template} value={template}>
                                                            {template}
                                                        </SelectItem>
                                                    ))}
                                                    {borderTemplates.length === 0 && !loadingTemplates && (
                                                        <SelectItem value="none" disabled>
                                                            No templates available
                                                        </SelectItem>
                                                    )}
                                                </SelectContent>
                                            </Select>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="w-full mt-2"
                                                onClick={() => setShowBorderGenerator(true)}
                                                disabled={generating || loadingTemplates}
                                            >
                                                <ImageIcon className="h-4 w-4 mr-2" />
                                                Generate New Border
                                            </Button>
                                        </div>
                                    </CollapsibleContent>
                                </Collapsible>

                                {/* Generate Button */}
                                <Button
                                    onClick={handleGenerateCover}
                                    disabled={generating || !prompt.trim() || !selectedChapter}
                                    className="w-full h-11 text-base font-semibold"
                                    size="lg"
                                >
                                    {generating ? (
                                        <>
                                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                            Generating... (30-60s)
                                        </>
                                    ) : (
                                        <>
                                            <ImageIcon className="mr-2 h-5 w-5" />
                                            Generate Cover
                                        </>
                                    )}
                                </Button>
                            </TabsContent>

                            {/* Book Preview PDF Tab */}
                            <TabsContent value="preview" className="mt-0 p-4 space-y-4">
                                <div className="space-y-2">
                                    <p className="text-sm text-gray-700">
                                        Generate a PDF with all <strong>{chapters.length}</strong> chapter{chapters.length !== 1 ? 's' : ''} from your project.
                                    </p>
                                    {chaptersWithCovers > 0 && (
                                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                                            <p className="text-sm text-green-800">
                                                ✓ <strong>{chaptersWithCovers}</strong> chapter{chaptersWithCovers !== 1 ? 's have' : ' has'} cover{chaptersWithCovers !== 1 ? 's' : ''} that will be included
                                            </p>
                                        </div>
                                    )}
                                </div>

                                {/* PDF Settings */}
                                <Collapsible open={showPdfSettings} onOpenChange={setShowPdfSettings}>
                                    <CollapsibleTrigger asChild>
                                        <Button variant="outline" className="w-full justify-between">
                                            <span className="flex items-center gap-2">
                                                <Settings className="h-4 w-4" />
                                                PDF Settings
                                            </span>
                                            <ChevronDown className={`h-4 w-4 transition-transform ${showPdfSettings ? 'rotate-180' : ''}`} />
                                        </Button>
                                    </CollapsibleTrigger>
                                    <CollapsibleContent className="space-y-4 pt-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label className="text-xs">Paper Size</Label>
                                                <Select
                                                    value={pdfSettings.paperSize}
                                                    onValueChange={(val: 'a4' | 'letter') => setPdfSettings(prev => ({ ...prev, paperSize: val }))}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="a4">A4</SelectItem>
                                                        <SelectItem value="letter">Letter</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                            <div className="space-y-2">
                                                <Label className="text-xs">Body Font</Label>
                                                <Select
                                                    value={pdfSettings.fontName}
                                                    onValueChange={(val) => setPdfSettings(prev => ({ ...prev, fontName: val }))}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="Times-Roman">Times New Roman</SelectItem>
                                                        <SelectItem value="Garamond">Garamond</SelectItem>
                                                        <SelectItem value="Palatino">Palatino</SelectItem>
                                                        <SelectItem value="Georgia">Georgia</SelectItem>
                                                        <SelectItem value="Helvetica">Helvetica</SelectItem>
                                                        <SelectItem value="Courier">Courier</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        </div>
                                        
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label className="text-xs">Font Size: {pdfSettings.fontSize}pt</Label>
                                                <Slider
                                                    value={[pdfSettings.fontSize]}
                                                    onValueChange={([val]) => setPdfSettings(prev => ({ ...prev, fontSize: val }))}
                                                    min={8}
                                                    max={18}
                                                    step={1}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label className="text-xs">Line Spacing: {pdfSettings.lineSpacing}</Label>
                                                <Slider
                                                    value={[pdfSettings.lineSpacing]}
                                                    onValueChange={([val]) => setPdfSettings(prev => ({ ...prev, lineSpacing: val }))}
                                                    min={1}
                                                    max={3}
                                                    step={0.1}
                                                />
                                            </div>
                                        </div>
                                        
                                        <Separator />
                                        
                                        {/* Drop Cap Settings */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <Label className="text-sm font-semibold">Drop Cap (First Letter)</Label>
                                                <Switch
                                                    checked={pdfSettings.dropCap}
                                                    onCheckedChange={(checked) => setPdfSettings(prev => ({ ...prev, dropCap: checked }))}
                                                />
                                            </div>
                                            {pdfSettings.dropCap && (
                                                <div className="space-y-3 pl-2 border-l-2 border-gray-200">
                                                    <div className="space-y-2">
                                                        <Label className="text-xs">Drop Cap Font</Label>
                                                        <Select
                                                            value={pdfSettings.dropCapFont}
                                                            onValueChange={(val) => setPdfSettings(prev => ({ ...prev, dropCapFont: val }))}
                                                        >
                                                            <SelectTrigger>
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="UnifrakturCook">UnifrakturCook (Gothic)</SelectItem>
                                                                <SelectItem value="Tangerine">Tangerine (Script)</SelectItem>
                                                                <SelectItem value="Cinzel">Cinzel (Elegant)</SelectItem>
                                                                <SelectItem value="Times-Bold">Times Bold</SelectItem>
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <Label className="text-xs">Uppercase First Letter</Label>
                                                        <Switch
                                                            checked={pdfSettings.dropCapUppercase}
                                                            onCheckedChange={(checked) => setPdfSettings(prev => ({ ...prev, dropCapUppercase: checked }))}
                                                        />
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                        
                                        <Separator />
                                        
                                        {/* Chapter Borders & TOC */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <Label className="text-sm">Chapter Page Borders</Label>
                                                    <p className="text-xs text-gray-500">Add decorative borders to chapter pages</p>
                                                </div>
                                                <Switch
                                                    checked={pdfSettings.chapterBorders}
                                                    onCheckedChange={(checked) => setPdfSettings(prev => ({ ...prev, chapterBorders: checked }))}
                                                />
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <Label className="text-sm">Table of Contents</Label>
                                                    <p className="text-xs text-gray-500">Auto-generate TOC with page numbers</p>
                                                </div>
                                                <Switch
                                                    checked={pdfSettings.includeToc}
                                                    onCheckedChange={(checked) => setPdfSettings(prev => ({ ...prev, includeToc: checked }))}
                                                />
                                            </div>
                                        </div>
                                        
                                        <Separator />
                                        
                                        <div className="space-y-3">
                                            <Label className="text-sm font-semibold">Margins (inches)</Label>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div className="space-y-2">
                                                    <Label className="text-xs">Top: {pdfSettings.margins.top}"</Label>
                                                    <Slider
                                                        value={[pdfSettings.margins.top]}
                                                        onValueChange={([val]) => setPdfSettings(prev => ({ 
                                                            ...prev, 
                                                            margins: { ...prev.margins, top: val } 
                                                        }))}
                                                        min={0.5}
                                                        max={2}
                                                        step={0.25}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs">Bottom: {pdfSettings.margins.bottom}"</Label>
                                                    <Slider
                                                        value={[pdfSettings.margins.bottom]}
                                                        onValueChange={([val]) => setPdfSettings(prev => ({ 
                                                            ...prev, 
                                                            margins: { ...prev.margins, bottom: val } 
                                                        }))}
                                                        min={0.5}
                                                        max={2}
                                                        step={0.25}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs">Left: {pdfSettings.margins.left}"</Label>
                                                    <Slider
                                                        value={[pdfSettings.margins.left]}
                                                        onValueChange={([val]) => setPdfSettings(prev => ({ 
                                                            ...prev, 
                                                            margins: { ...prev.margins, left: val } 
                                                        }))}
                                                        min={0.5}
                                                        max={2}
                                                        step={0.25}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label className="text-xs">Right: {pdfSettings.margins.right}"</Label>
                                                    <Slider
                                                        value={[pdfSettings.margins.right]}
                                                        onValueChange={([val]) => setPdfSettings(prev => ({ 
                                                            ...prev, 
                                                            margins: { ...prev.margins, right: val } 
                                                        }))}
                                                        min={0.5}
                                                        max={2}
                                                        step={0.25}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <Separator />
                                        
                                        <div className="flex items-center justify-between">
                                            <Label className="text-sm">Include Chapter Covers</Label>
                                            <Switch
                                                checked={pdfSettings.includeCovers}
                                                onCheckedChange={(checked) => setPdfSettings(prev => ({ ...prev, includeCovers: checked }))}
                                            />
                                        </div>
                                    </CollapsibleContent>
                                </Collapsible>

                                <Button
                                    onClick={handleGeneratePDF}
                                    disabled={generatingPDF || chapters.length === 0}
                                    className="w-full h-11 text-base font-semibold"
                                    size="lg"
                                >
                                    {generatingPDF ? (
                                        <>
                                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                            Generating PDF...
                                        </>
                                    ) : (
                                        <>
                                            <FileText className="mr-2 h-5 w-5" />
                                            Generate PDF Preview
                                        </>
                                    )}
                                </Button>
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>

                    {/* Gallery Modal */}
                    {showGallery && (
                        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowGallery(false)}>
                            <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
                                <div className="p-4 border-b">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-lg font-semibold">Cover Gallery ({chapterImages.size})</h3>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setShowGallery(false)}
                                        >
                                            <X className="h-4 w-4" />
                                        </Button>
                                    </div>
                                    
                                    {/* Search and Filter */}
                                    <div className="flex gap-2">
                                        <div className="flex-1 relative">
                                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                                            <Input
                                                placeholder="Search by chapter name..."
                                                value={gallerySearch}
                                                onChange={(e) => setGallerySearch(e.target.value)}
                                                className="pl-9"
                                            />
                                        </div>
                                        <Select value={galleryFilter} onValueChange={(v: any) => setGalleryFilter(v)}>
                                            <SelectTrigger className="w-40">
                                                <Filter className="h-4 w-4 mr-2" />
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">All Chapters</SelectItem>
                                                <SelectItem value="with-covers">With Covers</SelectItem>
                                                <SelectItem value="without-covers">Without Covers</SelectItem>
                                                <SelectItem value="borders">Borders</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <div className="flex-1 overflow-y-auto p-4">
                                    {galleryFilter === 'borders' ? (
                                        // Border Gallery View
                                        <div className="space-y-4">
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm text-gray-600">
                                                    {borderTemplates.length} border template{borderTemplates.length !== 1 ? 's' : ''} available
                                                </p>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => {
                                                        setShowGallery(false);
                                                        setShowBorderGenerator(true);
                                                    }}
                                                >
                                                    <ImageIcon className="h-4 w-4 mr-2" />
                                                    Generate New Border
                                                </Button>
                                            </div>
                                            {borderTemplates.length === 0 ? (
                                                <div className="text-center text-gray-500 py-12">
                                                    <p>No border templates yet</p>
                                                    <Button
                                                        variant="outline"
                                                        className="mt-4"
                                                        onClick={() => {
                                                            setShowGallery(false);
                                                            setShowBorderGenerator(true);
                                                        }}
                                                    >
                                                        Generate Your First Border
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                                                    {borderTemplates.map((template) => (
                                                        <div
                                                            key={template}
                                                            className="border rounded-lg overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                                                            onClick={() => {
                                                                setGenSettings(prev => ({ ...prev, borderTemplate: template }));
                                                                setShowGallery(false);
                                                            }}
                                                        >
                                                            <div className="aspect-square bg-gray-100 flex items-center justify-center p-4">
                                                                <div className="text-center">
                                                                    <ImageIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                                                                    <p className="text-xs text-gray-600 font-medium">{template}</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ) : chapterImages.size === 0 ? (
                                        <div className="text-center text-gray-500 py-12">
                                            <ImageIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                                            <p>No covers generated yet</p>
                                        </div>
                                    ) : (() => {
                                        // Filter images based on search and filter
                                        let filteredImages = Array.from(chapterImages.entries());
                                        
                                        // Apply search filter
                                        if (gallerySearch.trim()) {
                                            const searchLower = gallerySearch.toLowerCase();
                                            filteredImages = filteredImages.filter(([order, image]) => {
                                                const chapter = chapters.find(c => c.order === order);
                                                const chapterName = (chapter?.chapter_name || `Chapter ${order}`).toLowerCase();
                                                const prompt = image.prompt.toLowerCase();
                                                return chapterName.includes(searchLower) || prompt.includes(searchLower);
                                            });
                                        }
                                        
                                        // Apply cover filter
                                        if (galleryFilter === 'with-covers') {
                                            // Already filtered to only images with covers
                                        } else if (galleryFilter === 'without-covers') {
                                            // Show chapters without covers
                                            const coveredOrders = new Set(chapterImages.keys());
                                            filteredImages = chapters
                                                .filter(ch => !coveredOrders.has(ch.order))
                                                .map(ch => [ch.order, null] as [number, GeneratedImage | null]);
                                        }
                                        
                                        if (filteredImages.length === 0) {
                                            return (
                                                <div className="text-center text-gray-500 py-12">
                                                    <p>No covers match your search</p>
                                                </div>
                                            );
                                        }
                                        
                                        return (
                                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                                                {filteredImages.map(([order, image]) => {
                                                    const chapter = chapters.find(c => c.order === order);
                                                    const hasCover = image !== null;
                                                    
                                                    return (
                                                        <div key={order} className="border rounded-lg overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow">
                                                            <div className="relative aspect-square bg-gray-100">
                                                                {hasCover ? (
                                                                    <>
                                                                        <img
                                                                            src={image.image}
                                                                            alt={`Chapter ${order} cover`}
                                                                            className="w-full h-full object-cover cursor-pointer"
                                                                            onClick={() => {
                                                                                handleSelectChapterFromGallery(order);
                                                                                setShowGallery(false);
                                                                            }}
                                                                        />
                                                                        <Button
                                                                            variant="destructive"
                                                                            size="sm"
                                                                            className="absolute top-2 right-2 h-7 w-7 p-0"
                                                                            onClick={() => handleDeleteImage(order)}
                                                                        >
                                                                            <Trash2 className="h-3 w-3" />
                                                                        </Button>
                                                                    </>
                                                                ) : (
                                                                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                                                                        <ImageIcon className="h-8 w-8" />
                                                                    </div>
                                                                )}
                                                            </div>
                                                            <div className="p-3">
                                                                <p className="text-sm font-medium truncate">
                                                                    {chapter?.chapter_name || `Chapter ${order}`}
                                                                </p>
                                                                {hasCover ? (
                                                                    <p className="text-xs text-gray-500 mt-1">
                                                                        {image.settings.width}×{image.settings.height}
                                                                    </p>
                                                                ) : (
                                                                    <p className="text-xs text-gray-400 mt-1">No cover</p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        );
                                    })()}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Border Generator Modal */}
                    {showBorderGenerator && (
                        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowBorderGenerator(false)}>
                            <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
                                <div className="p-6 border-b">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-lg font-semibold">Generate Border Template</h3>
                                        <Button variant="ghost" size="sm" onClick={() => setShowBorderGenerator(false)}>
                                            <X className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                                
                                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                                    <div className="space-y-2">
                                        <Label className="text-sm font-semibold">Template Name</Label>
                                        <Input
                                            value={borderSettings.templateName}
                                            onChange={(e) => setBorderSettings(prev => ({ ...prev, templateName: e.target.value }))}
                                            placeholder="e.g., ornate_border_1"
                                            disabled={generatingBorder}
                                        />
                                        <p className="text-xs text-gray-500">This name will be used to save and reference the border template.</p>
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <Label className="text-sm font-semibold">Prompt</Label>
                                        <Textarea
                                            value={borderPrompt}
                                            onChange={(e) => setBorderPrompt(e.target.value)}
                                            placeholder="Describe the border design you want..."
                                            rows={3}
                                            disabled={generatingBorder}
                                        />
                                    </div>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label className="text-sm">Border Style</Label>
                                            <Select
                                                value={borderSettings.borderStyle}
                                                onValueChange={(value: 'rectangular' | 'circular' | 'ornate') => 
                                                    setBorderSettings(prev => ({ ...prev, borderStyle: value }))
                                                }
                                                disabled={generatingBorder}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="rectangular">Rectangular</SelectItem>
                                                    <SelectItem value="circular">Circular</SelectItem>
                                                    <SelectItem value="ornate">Ornate</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        
                                        <div className="space-y-2">
                                            <Label className="text-sm">Border Thickness: {borderSettings.borderThickness}px</Label>
                                            <Slider
                                                value={[borderSettings.borderThickness]}
                                                onValueChange={([val]) => setBorderSettings(prev => ({ ...prev, borderThickness: val }))}
                                                min={20}
                                                max={200}
                                                step={10}
                                                disabled={generatingBorder}
                                            />
                                        </div>
                                    </div>
                                    
                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                        <p className="text-sm text-blue-800">
                                            <strong>Note:</strong> Border generation uses ControlNet and may take 30-60 seconds. 
                                            The generated border will be saved as a template and can be used for future cover generations.
                                        </p>
                                    </div>
                                </div>
                                
                                <div className="p-6 border-t flex justify-end gap-2">
                                    <Button variant="outline" onClick={() => setShowBorderGenerator(false)} disabled={generatingBorder}>
                                        Cancel
                                    </Button>
                                    <Button onClick={handleGenerateBorder} disabled={generatingBorder || !borderSettings.templateName.trim()}>
                                        {generatingBorder ? (
                                            <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                Generating...
                                            </>
                                        ) : (
                                            <>
                                                <ImageIcon className="mr-2 h-4 w-4" />
                                                Generate & Save
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
            </div>
        </ProjectEditorLayout>
    );
}
