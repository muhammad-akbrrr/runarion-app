import { Button } from "@/Components/ui/button";
import { Badge } from "@/Components/ui/badge";
import {
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/Components/ui/accordion";
import {
    Clock,
    RefreshCw,
    Loader2,
    CheckCircle,
    AlertTriangle,
} from "lucide-react";
import type { ScanStatus } from "./types";

interface ScanStatusSectionProps {
    scanStatus: ScanStatus | null;
    loadingScanStatus: boolean;
    onRefresh: () => void;
}

export default function ScanStatusSection({
    scanStatus,
    loadingScanStatus,
    onRefresh,
}: ScanStatusSectionProps) {
    return (
        <AccordionItem value="scan-status">
            <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-blue-600" />
                    <span className="font-medium">Scan Status</span>
                    {scanStatus && (
                        <Badge variant="outline" className="ml-2">
                            {scanStatus.chapters_with_changes +
                                scanStatus.chapters_not_scanned}{" "}
                            pending
                        </Badge>
                    )}
                </div>
            </AccordionTrigger>
            <AccordionContent>
                <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-gray-500">
                            Shows which chapters have been scanned and which
                            have changes.
                        </p>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={onRefresh}
                            disabled={loadingScanStatus}
                        >
                            {loadingScanStatus ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                                <RefreshCw className="h-3 w-3" />
                            )}
                        </Button>
                    </div>

                    {scanStatus && (
                        <>
                            {/* Summary Stats */}
                            <div className="grid grid-cols-3 gap-2 text-center">
                                <div className="p-2 bg-gray-50 rounded">
                                    <div className="text-lg font-bold">
                                        {scanStatus.total_chapters}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        Chapters
                                    </div>
                                </div>
                                <div className="p-2 bg-blue-50 rounded">
                                    <div className="text-lg font-bold text-blue-700">
                                        {scanStatus.extraction_pending ||
                                            scanStatus.chapters_not_scanned ||
                                            0}
                                    </div>
                                    <div className="text-xs text-blue-600">
                                        Extract
                                    </div>
                                </div>
                                <div className="p-2 bg-orange-50 rounded">
                                    <div className="text-lg font-bold text-orange-700">
                                        {scanStatus.summarization_pending || 0}
                                    </div>
                                    <div className="text-xs text-orange-600">
                                        Summary
                                    </div>
                                </div>
                                {(scanStatus.data_warnings || 0) > 0 && (
                                    <div className="p-2 bg-red-50 rounded">
                                        <div className="text-lg font-bold text-red-700">
                                            {scanStatus.data_warnings}
                                        </div>
                                        <div className="text-xs text-red-600">
                                            Warnings
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Chapter Details */}
                            <div className="max-h-64 overflow-y-auto space-y-2">
                                {Object.values(scanStatus.chapters)
                                    .sort(
                                        (a, b) =>
                                            a.chapter_order - b.chapter_order
                                    )
                                    .map((ch) => (
                                        <div
                                            key={ch.chapter_order}
                                            className={`p-2 rounded border text-xs ${
                                                ch.has_changes
                                                    ? "border-yellow-300 bg-yellow-50"
                                                    : "border-green-300 bg-green-50"
                                            }`}
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-medium">
                                                    Ch. {ch.chapter_order + 1}:{" "}
                                                    {ch.chapter_name}
                                                </span>
                                                {ch.has_changes && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-[10px] bg-yellow-100 text-yellow-700"
                                                    >
                                                        Changed
                                                    </Badge>
                                                )}
                                            </div>

                                            {/* Status indicators */}
                                            <div className="grid grid-cols-2 gap-1 mt-1">
                                                {/* Extraction Status */}
                                                <div
                                                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                                                        ch.extraction?.warning
                                                            ? "bg-red-100 text-red-700"
                                                            : ch.extraction
                                                                  ?.done
                                                            ? "bg-green-100 text-green-700"
                                                            : "bg-gray-100 text-gray-500"
                                                    }`}
                                                >
                                                    {ch.extraction?.warning ? (
                                                        <AlertTriangle className="h-3 w-3" />
                                                    ) : ch.extraction?.done ? (
                                                        <CheckCircle className="h-3 w-3" />
                                                    ) : (
                                                        <Clock className="h-3 w-3" />
                                                    )}
                                                    <span>Extract</span>
                                                    {ch.extraction
                                                        ?.categories_extracted
                                                        ?.length > 0 && (
                                                        <span className="text-[10px]">
                                                            (
                                                            {
                                                                ch.extraction
                                                                    .categories_extracted
                                                                    .length
                                                            }
                                                            )
                                                        </span>
                                                    )}
                                                </div>

                                                {/* Record Keeper Status */}
                                                <div
                                                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${
                                                        ch.record_keeper
                                                            ?.warning
                                                            ? "bg-red-100 text-red-700"
                                                            : ch.record_keeper
                                                                  ?.done
                                                            ? "bg-green-100 text-green-700"
                                                            : "bg-gray-100 text-gray-500"
                                                    }`}
                                                >
                                                    {ch.record_keeper
                                                        ?.warning ? (
                                                        <AlertTriangle className="h-3 w-3" />
                                                    ) : ch.record_keeper
                                                          ?.done ? (
                                                        <CheckCircle className="h-3 w-3" />
                                                    ) : (
                                                        <Clock className="h-3 w-3" />
                                                    )}
                                                    <span>Summary</span>
                                                </div>
                                            </div>

                                            {/* Warning messages */}
                                            {(ch.extraction?.warning ||
                                                ch.record_keeper?.warning) && (
                                                <div className="mt-1 text-[10px] text-red-600 bg-red-50 p-1 rounded">
                                                    {ch.extraction?.warning && (
                                                        <div>
                                                            {
                                                                ch.extraction
                                                                    .warning
                                                            }
                                                        </div>
                                                    )}
                                                    {ch.record_keeper
                                                        ?.warning && (
                                                        <div>
                                                            {
                                                                ch.record_keeper
                                                                    .warning
                                                            }
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Categories extracted */}
                                            {ch.extraction?.categories_extracted
                                                ?.length > 0 && (
                                                <div className="mt-1 text-[10px] text-gray-500">
                                                    Categories:{" "}
                                                    {ch.extraction.categories_extracted.join(
                                                        ", "
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                            </div>

                            <p className="text-xs text-gray-500 italic">
                                Use Extractor for entities, Summarizer for
                                Record Keeper entries.
                            </p>
                        </>
                    )}
                </div>
            </AccordionContent>
        </AccordionItem>
    );
}
