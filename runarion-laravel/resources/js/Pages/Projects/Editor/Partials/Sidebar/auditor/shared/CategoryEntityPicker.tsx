import { Button } from "@/Components/ui/button";
import { Checkbox } from "@/Components/ui/checkbox";
import { Label } from "@/Components/ui/label";

export type PickerMode = "all" | "category" | "entity";

interface CategoryEntityPickerProps {
    mode: PickerMode;
    onModeChange: (mode: PickerMode) => void;
    availableCategories: string[];
    availableEntities: Record<string, Array<{ vertex_id: string; name: string }>>;
    selectedCategories: Set<string>;
    selectedEntities: Set<string>;
    onCategoriesChange: (categories: Set<string>) => void;
    onEntitiesChange: (entities: Set<string>) => void;
    loadingCategories: boolean;
    loadingEntities: boolean;
    expandedCategory: string | null;
    onExpandCategory: (category: string | null) => void;
    loadEntitiesForCategory: (category: string) => Promise<void>;
    // Styling customization
    accentColor?: "orange" | "purple" | "indigo" | "green";
    // Whether to show category checkbox in entity mode
    showCategoryCheckbox?: boolean;
}

const accentColors = {
    orange: {
        selected: "bg-orange-100 text-orange-800 border-orange-300",
        text: "text-orange-600",
        entitySelected: "bg-orange-100 text-orange-800",
    },
    purple: {
        selected: "bg-purple-100 text-purple-800 border-purple-300",
        text: "text-purple-600",
        entitySelected: "bg-purple-100 text-purple-800",
    },
    indigo: {
        selected: "bg-indigo-100 text-indigo-800 border-indigo-300",
        text: "text-indigo-600",
        entitySelected: "bg-indigo-100 text-indigo-800",
    },
    green: {
        selected: "bg-green-100 text-green-800 border-green-300",
        text: "text-green-600",
        entitySelected: "bg-green-100 text-green-800",
    },
};

export default function CategoryEntityPicker({
    mode,
    onModeChange,
    availableCategories,
    availableEntities,
    selectedCategories,
    selectedEntities,
    onCategoriesChange,
    onEntitiesChange,
    loadingCategories,
    loadingEntities,
    expandedCategory,
    onExpandCategory,
    loadEntitiesForCategory,
    accentColor = "orange",
    showCategoryCheckbox = false,
}: CategoryEntityPickerProps) {
    const colors = accentColors[accentColor];

    const toggleCategory = (cat: string, checked: boolean) => {
        const next = new Set(selectedCategories);
        if (checked) next.add(cat);
        else next.delete(cat);
        onCategoriesChange(next);
    };

    const toggleEntity = (vertexId: string, checked: boolean) => {
        const next = new Set(selectedEntities);
        if (checked) next.add(vertexId);
        else next.delete(vertexId);
        onEntitiesChange(next);
    };

    const selectAllEntitiesInCategory = (category: string) => {
        const entities = availableEntities[category] || [];
        const next = new Set(selectedEntities);
        entities.forEach((e) => next.add(e.vertex_id));
        onEntitiesChange(next);
    };

    const deselectAllEntitiesInCategory = (category: string) => {
        const entities = availableEntities[category] || [];
        const entityIds = new Set(entities.map((e) => e.vertex_id));
        const next = new Set(selectedEntities);
        entityIds.forEach((id) => next.delete(id));
        onEntitiesChange(next);
    };

    const handleCategoryClick = (cat: string) => {
        if (mode === "entity") {
            if (expandedCategory === cat) {
                onExpandCategory(null);
            } else {
                onExpandCategory(cat);
                loadEntitiesForCategory(cat);
            }
        }
    };

    return (
        <div className="p-2 border rounded space-y-2">
            {/* Mode selector */}
            <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Scope:</Label>
                <div className="flex gap-1">
                    <Button
                        variant={mode === "all" ? "default" : "outline"}
                        size="sm"
                        className="h-6 text-xs px-2"
                        onClick={() => onModeChange("all")}
                    >
                        All
                    </Button>
                    <Button
                        variant={mode === "category" ? "default" : "outline"}
                        size="sm"
                        className="h-6 text-xs px-2"
                        onClick={() => onModeChange("category")}
                    >
                        Category
                    </Button>
                    <Button
                        variant={mode === "entity" ? "default" : "outline"}
                        size="sm"
                        className="h-6 text-xs px-2"
                        onClick={() => onModeChange("entity")}
                    >
                        Entity
                    </Button>
                </div>
            </div>

            {/* Category selection (category mode) */}
            {mode === "category" && (
                <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                    {loadingCategories ? (
                        <span className="text-xs text-gray-400">
                            Loading categories...
                        </span>
                    ) : availableCategories.length === 0 ? (
                        <span className="text-xs text-gray-400">
                            No categories found
                        </span>
                    ) : (
                        availableCategories.map((cat) => (
                            <label
                                key={cat}
                                className={`flex items-center gap-1 px-2 py-1 rounded text-xs cursor-pointer transition-colors ${
                                    selectedCategories.has(cat)
                                        ? colors.selected
                                        : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                                }`}
                            >
                                <Checkbox
                                    checked={selectedCategories.has(cat)}
                                    onCheckedChange={(checked) =>
                                        toggleCategory(cat, !!checked)
                                    }
                                    className="h-3 w-3"
                                />
                                {cat}
                            </label>
                        ))
                    )}
                </div>
            )}

            {/* Entity selection (entity mode) */}
            {mode === "entity" && (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                    {loadingCategories ? (
                        <span className="text-xs text-gray-400">
                            Loading categories...
                        </span>
                    ) : availableCategories.length === 0 ? (
                        <span className="text-xs text-gray-400">
                            No categories found
                        </span>
                    ) : (
                        availableCategories.map((cat) => (
                            <div key={cat} className="border rounded">
                                <div
                                    className={`flex items-center justify-between p-1.5 cursor-pointer hover:bg-gray-50 ${
                                        showCategoryCheckbox &&
                                        selectedCategories.has(cat)
                                            ? `bg-${accentColor}-50`
                                            : ""
                                    }`}
                                    onClick={() => handleCategoryClick(cat)}
                                >
                                    {showCategoryCheckbox ? (
                                        <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                                            <Checkbox
                                                checked={selectedCategories.has(cat)}
                                                onCheckedChange={(checked) =>
                                                    toggleCategory(cat, !!checked)
                                                }
                                                className="h-3 w-3"
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                            <span
                                                className={
                                                    selectedCategories.has(cat)
                                                        ? `${colors.text} font-medium`
                                                        : ""
                                                }
                                            >
                                                {cat}
                                            </span>
                                        </label>
                                    ) : (
                                        <span className="text-xs font-medium">
                                            {cat}
                                        </span>
                                    )}
                                    <span className="text-xs text-gray-400">
                                        {expandedCategory === cat ? "▼" : "▶"}
                                    </span>
                                </div>

                                {expandedCategory === cat && (
                                    <div className="border-t p-1.5 bg-gray-50 space-y-1">
                                        {loadingEntities ? (
                                            <span className="text-xs text-gray-400">
                                                Loading...
                                            </span>
                                        ) : (availableEntities[cat] || []).length ===
                                          0 ? (
                                            <span className="text-xs text-gray-400">
                                                No entities
                                            </span>
                                        ) : (
                                            <>
                                                <div className="flex gap-2 mb-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-5 text-xs px-1"
                                                        onClick={() =>
                                                            selectAllEntitiesInCategory(
                                                                cat
                                                            )
                                                        }
                                                    >
                                                        Select All
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-5 text-xs px-1"
                                                        onClick={() =>
                                                            deselectAllEntitiesInCategory(
                                                                cat
                                                            )
                                                        }
                                                    >
                                                        Deselect All
                                                    </Button>
                                                </div>
                                                {(availableEntities[cat] || []).map(
                                                    (entity) => (
                                                        <label
                                                            key={entity.vertex_id}
                                                            className={`flex items-center gap-1.5 text-xs cursor-pointer p-1 rounded ${
                                                                selectedEntities.has(
                                                                    entity.vertex_id
                                                                )
                                                                    ? colors.entitySelected
                                                                    : "hover:bg-gray-100"
                                                            }`}
                                                        >
                                                            <Checkbox
                                                                checked={selectedEntities.has(
                                                                    entity.vertex_id
                                                                )}
                                                                onCheckedChange={(
                                                                    checked
                                                                ) =>
                                                                    toggleEntity(
                                                                        entity.vertex_id,
                                                                        !!checked
                                                                    )
                                                                }
                                                                className="h-3 w-3"
                                                            />
                                                            {entity.name}
                                                        </label>
                                                    )
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Selection summary */}
            {mode === "category" && selectedCategories.size > 0 && (
                <div className={`text-xs ${colors.text}`}>
                    {selectedCategories.size} categor
                    {selectedCategories.size === 1 ? "y" : "ies"} selected
                </div>
            )}

            {mode === "entity" && selectedEntities.size > 0 && (
                <div className={`text-xs ${colors.text}`}>
                    {selectedEntities.size} entit
                    {selectedEntities.size === 1 ? "y" : "ies"} selected
                </div>
            )}
        </div>
    );
}
