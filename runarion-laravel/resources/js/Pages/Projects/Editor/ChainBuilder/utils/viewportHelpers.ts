// Viewport pan/zoom calculation utilities

export interface ViewportState {
    pan: { x: number; y: number };
    zoom: number;
}

/**
 * Convert screen coordinates to world coordinates
 */
export const screenToWorld = (
    screenX: number,
    screenY: number,
    pan: { x: number; y: number },
    zoom: number
): { x: number; y: number } => {
    return {
        x: (screenX - pan.x) / zoom,
        y: (screenY - pan.y) / zoom,
    };
};

/**
 * Convert world coordinates to screen coordinates
 */
export const worldToScreen = (
    worldX: number,
    worldY: number,
    pan: { x: number; y: number },
    zoom: number
): { x: number; y: number } => {
    return {
        x: worldX * zoom + pan.x,
        y: worldY * zoom + pan.y,
    };
};

/**
 * Calculate zoom with mouse position as pivot point
 */
export const zoomAtPoint = (
    currentZoom: number,
    delta: number,
    mouseX: number,
    mouseY: number,
    currentPan: { x: number; y: number },
    minZoom: number = 0.2,
    maxZoom: number = 3
): { zoom: number; pan: { x: number; y: number } } => {
    const zoomSensitivity = 0.001;
    const zoomDelta = -delta * zoomSensitivity;
    const newZoom = Math.min(Math.max(currentZoom + zoomDelta, minZoom), maxZoom);
    
    // Calculate world position of mouse before zoom
    const worldX = (mouseX - currentPan.x) / currentZoom;
    const worldY = (mouseY - currentPan.y) / currentZoom;
    
    // Calculate new pan to keep mouse point fixed
    const newPanX = mouseX - worldX * newZoom;
    const newPanY = mouseY - worldY * newZoom;
    
    return {
        zoom: newZoom,
        pan: { x: newPanX, y: newPanY },
    };
};

