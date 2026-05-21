import React from "react";
import { GraphTemplate } from "../types";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Trash2, X, FolderOpen, Save, FileText } from "lucide-react";

interface TemplatesSidebarProps {
    isOpen: boolean;
    templates: GraphTemplate[];
    templateName: string;
    editingTemplateId: string | null;
    onOpenChange: (open: boolean) => void;
    onTemplateNameChange: (name: string) => void;
    onSaveTemplate: () => void;
    onLoadTemplate: (template: GraphTemplate) => void;
    onEditTemplate: (template: GraphTemplate) => void;
    onDeleteTemplate: (id: string) => void;
    onStartNewTemplate: () => void;
}

export const TemplatesSidebar: React.FC<TemplatesSidebarProps> = ({
    isOpen,
    templates,
    templateName,
    editingTemplateId,
    onOpenChange,
    onTemplateNameChange,
    onSaveTemplate,
    onLoadTemplate,
    onEditTemplate,
    onDeleteTemplate,
    onStartNewTemplate,
}) => {
    return (
        <div className="relative flex items-center h-full">
            {/* Toggle Button - Always visible on right edge when collapsed */}
            {!isOpen && (
                <button
                    onClick={() => onOpenChange(true)}
                    className="absolute right-0 top-1/2 -translate-y-1/2 z-50 bg-white border-l border-t border-b border-gray-300 rounded-l-lg px-3 py-8 shadow-md hover:bg-gray-50 transition-colors flex items-center justify-center"
                    title="Open Templates"
                >
                    <FileText className="w-5 h-5 text-gray-600" />
                </button>
            )}

            {/* Templates Panel */}
            <div
                className={`h-full bg-white border-l border-gray-300 flex flex-col shadow-lg transition-all duration-300 ${
                    isOpen ? "w-80" : "w-0 overflow-hidden"
                }`}
            >
                {isOpen && (
                    <>
                        <div className="p-4 border-b border-gray-300 flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                <FileText className="w-4 h-4" /> Templates
                            </h2>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => onOpenChange(false)}
                                title="Close Templates"
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {/* Save Template Form */}
                            <div className="flex flex-col gap-2 pb-4 border-b border-gray-200">
                                <label className="text-sm font-medium text-gray-700">
                                    {editingTemplateId
                                        ? "Edit Template"
                                        : "Save Current Graph as Template"}
                                </label>
                                <div className="flex gap-2 items-stretch">
                                    <Input
                                        value={templateName}
                                        onChange={(e) =>
                                            onTemplateNameChange(e.target.value)
                                        }
                                        placeholder="Template name..."
                                        className="flex-1"
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") {
                                                onSaveTemplate();
                                            }
                                        }}
                                    />
                                    <Button
                                        onClick={onSaveTemplate}
                                        disabled={!templateName.trim()}
                                        size="sm"
                                        className="bg-blue-600 hover:bg-blue-700 h-9"
                                    >
                                        <Save className="w-4 h-4" />
                                    </Button>
                                    {editingTemplateId && (
                                        <Button
                                            onClick={onStartNewTemplate}
                                            variant="outline"
                                            size="sm"
                                            className="h-9"
                                        >
                                            Cancel
                                        </Button>
                                    )}
                                </div>
                            </div>

                            {/* Templates List */}
                            <div className="space-y-2">
                                <h3 className="text-sm font-semibold text-gray-700">
                                    Saved Templates
                                </h3>
                                {templates.length === 0 ? (
                                    <p className="text-sm text-gray-500 italic">
                                        No templates saved yet
                                    </p>
                                ) : (
                                    <div className="space-y-2">
                                        {templates.map((template) => (
                                            <div
                                                key={template.id}
                                                className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
                                            >
                                                <div className="flex items-start justify-between mb-2">
                                                    <h4 className="text-sm font-medium text-gray-900 flex-1">
                                                        {template.name}
                                                    </h4>
                                                    <div className="flex gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-6 w-6"
                                                            onClick={() =>
                                                                onEditTemplate(
                                                                    template,
                                                                )
                                                            }
                                                            title="Edit"
                                                        >
                                                            <Save className="w-3 h-3" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-6 w-6 text-red-600 hover:text-red-700"
                                                            onClick={() =>
                                                                onDeleteTemplate(
                                                                    template.id,
                                                                )
                                                            }
                                                            title="Delete"
                                                        >
                                                            <Trash2 className="w-3 h-3" />
                                                        </Button>
                                                    </div>
                                                </div>
                                                <div className="text-xs text-gray-500 mb-2">
                                                    {template.nodes.length} node
                                                    {template.nodes.length !== 1
                                                        ? "s"
                                                        : ""}
                                                    , {template.edges.length}{" "}
                                                    edge
                                                    {template.edges.length !== 1
                                                        ? "s"
                                                        : ""}
                                                </div>
                                                <Button
                                                    onClick={() =>
                                                        onLoadTemplate(template)
                                                    }
                                                    size="sm"
                                                    variant="outline"
                                                    className="w-full"
                                                >
                                                    <FolderOpen className="w-3 h-3 mr-2" />
                                                    Load
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};
