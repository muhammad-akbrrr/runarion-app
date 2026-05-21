import { useState, useEffect } from "react";
import { Accordion } from "@/Components/ui/accordion";
import type {
    AuditorToolsTabProps,
    ScanStatus,
    ConsistencyIssue,
    DuplicateGroup,
    RefreshResults,
} from "./auditor/types";

// Section components
import ScanStatusSection from "./auditor/ScanStatusSection";
import RecordConsistencySection from "./auditor/RecordConsistencySection";
import StoryConsistencySection from "./auditor/StoryConsistencySection";
import PropertyRefreshSection from "./auditor/PropertyRefreshSection";
import DuplicateFinderSection from "./auditor/DuplicateFinderSection";

export default function AuditorToolsTab({
    workspaceId,
    projectId,
    selectedModel,
    onApplyStoryFix,
}: AuditorToolsTabProps) {
    // ============================================
    // SHARED STATE (data needed by multiple sections)
    // ============================================

    // Scan status - needed by ScanStatus and StoryConsistency (for chapter list)
    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [loadingScanStatus, setLoadingScanStatus] = useState(false);

    // Categories/entities - shared across Record, Property, and Duplicate sections
    const [availableCategories, setAvailableCategories] = useState<string[]>([]);
    const [availableEntities, setAvailableEntities] = useState<
        Record<string, Array<{ vertex_id: string; name: string }>>
    >({});
    const [loadingCategories, setLoadingCategories] = useState(false);
    const [loadingEntities, setLoadingEntities] = useState(false);

    // ============================================
    // PERSISTED STATE (saved to localStorage)
    // ============================================

    const [recordIssues, setRecordIssues] = useState<ConsistencyIssue[]>([]);
    const [storyIssues, setStoryIssues] = useState<ConsistencyIssue[]>([]);
    const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
    const [refreshResults, setRefreshResults] = useState<RefreshResults | null>(
        null
    );

    // ============================================
    // PERSISTENCE
    // ============================================

    const STORAGE_KEY = `auditor_state_${projectId}`;

    const loadPersistedState = () => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.recordIssues) setRecordIssues(parsed.recordIssues);
                if (parsed.storyIssues) setStoryIssues(parsed.storyIssues);
                if (parsed.refreshResults) setRefreshResults(parsed.refreshResults);
                if (parsed.duplicates) setDuplicates(parsed.duplicates);
            }
        } catch (error) {
            console.error("Error loading persisted state:", error);
        }
    };

    const savePersistedState = () => {
        try {
            const state = {
                recordIssues,
                storyIssues,
                refreshResults,
                duplicates,
                savedAt: new Date().toISOString(),
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (error) {
            console.error("Error saving persisted state:", error);
        }
    };

    // ============================================
    // SHARED LOADERS
    // ============================================

    const loadScanStatus = async () => {
        setLoadingScanStatus(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/auditor/scan-status`,
                { headers: { Accept: "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                setScanStatus(data.scan_status || null);
            }
        } catch (error) {
            console.error("Error loading scan status:", error);
        } finally {
            setLoadingScanStatus(false);
        }
    };

    const loadAvailableCategories = async () => {
        setLoadingCategories(true);
        try {
            const response = await fetch(
                `/${workspaceId}/projects/${projectId}/editor/records/categories`,
                { headers: { Accept: "application/json" } }
            );
            if (response.ok) {
                const data = await response.json();
                setAvailableCategories(data.categories || []);
            }
        } catch (error) {
            console.error("Error loading categories:", error);
        } finally {
            setLoadingCategories(false);
        }
    };

    const loadEntitiesForCategory = async (category: string) => {
        if (availableEntities[category]) return; // Already loaded

        setLoadingEntities(true);
        try {
            const url = `/${workspaceId}/projects/${projectId}/editor/records/entities?category=${encodeURIComponent(
                category
            )}`;
            const response = await fetch(url, {
                headers: { Accept: "application/json" },
            });
            if (response.ok) {
                const data = await response.json();
                setAvailableEntities((prev) => ({
                    ...prev,
                    [category]: (data.entities || []).map((e: any) => ({
                        vertex_id: String(e.vertex_id),
                        name: e.name,
                    })),
                }));
            }
        } catch (error) {
            console.error("Error loading entities:", error);
        } finally {
            setLoadingEntities(false);
        }
    };

    // ============================================
    // EFFECTS
    // ============================================

    // Load initial data on mount
    useEffect(() => {
        loadScanStatus();
        loadAvailableCategories();
        loadPersistedState();
    }, []);

    // Save state when results change
    useEffect(() => {
        savePersistedState();
    }, [recordIssues, storyIssues, refreshResults, duplicates]);

    // ============================================
    // SHARED PROPS FOR SECTIONS
    // ============================================

    const sharedSectionProps = {
        workspaceId,
        projectId,
        selectedModel,
        availableCategories,
        availableEntities,
        loadingCategories,
        loadingEntities,
        loadEntitiesForCategory,
    };

    // ============================================
    // RENDER
    // ============================================

    return (
        <div className="space-y-4">
            <Accordion
                type="multiple"
                defaultValue={["scan-status"]}
                className="w-full"
            >
                <ScanStatusSection
                    scanStatus={scanStatus}
                    loadingScanStatus={loadingScanStatus}
                    onRefresh={loadScanStatus}
                />

                <RecordConsistencySection
                    {...sharedSectionProps}
                    recordIssues={recordIssues}
                    onRecordIssuesChange={setRecordIssues}
                />

                <StoryConsistencySection
                    workspaceId={workspaceId}
                    projectId={projectId}
                    selectedModel={selectedModel}
                    scanStatus={scanStatus}
                    storyIssues={storyIssues}
                    onStoryIssuesChange={setStoryIssues}
                    onApplyStoryFix={onApplyStoryFix}
                />

                <PropertyRefreshSection
                    {...sharedSectionProps}
                    refreshResults={refreshResults}
                    onRefreshResultsChange={setRefreshResults}
                />

                <DuplicateFinderSection
                    {...sharedSectionProps}
                    duplicates={duplicates}
                    onDuplicatesChange={setDuplicates}
                />
            </Accordion>
        </div>
    );
}
