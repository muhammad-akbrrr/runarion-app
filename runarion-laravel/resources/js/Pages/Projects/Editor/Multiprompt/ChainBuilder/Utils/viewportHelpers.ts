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
 * Calculate viewport to fit all nodes in view
 */
export const fitViewToNodes = (
    nodes: Array<{ position: { x: number; y: number } }>,
    viewportWidth: number,
    viewportHeight: number,
    padding: number = 50,
    nodeWidth: number = 300,
    nodeHeight: number = 200
): { zoom: number; pan: { x: number; y: number } } => {
    // Handle empty canvas - return default view
    if (!nodes.length) {
        return { zoom: 1, pan: { x: 0, y: 0 } };
    }

    // Calculate bounding box of all nodes
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;

    for (const node of nodes) {
        minX = Math.min(minX, node.position.x);
        minY = Math.min(minY, node.position.y);
        maxX = Math.max(maxX, node.position.x + nodeWidth);
        maxY = Math.max(maxY, node.position.y + nodeHeight);
    }

    const boundsWidth = maxX - minX;
    const boundsHeight = maxY - minY;
    const boundsCenter = {
        x: minX + boundsWidth / 2,
        y: minY + boundsHeight / 2,
    };

    // Calculate zoom to fit bounds with padding
    const availableWidth = viewportWidth - 2 * padding;
    const availableHeight = viewportHeight - 2 * padding;

    let fitZoom = Math.min(
        availableWidth / boundsWidth,
        availableHeight / boundsHeight
    );

    // Apply slight zoom-out factor for breathing room
    fitZoom *= 0.85;

    // Clamp zoom to valid range (0.2 - 3)
    fitZoom = Math.max(0.2, Math.min(3, fitZoom));

    // Calculate pan to center bounds in viewport
    const pan = {
        x: viewportWidth / 2 - boundsCenter.x * fitZoom,
        y: viewportHeight / 2 - boundsCenter.y * fitZoom,
    };

    return { zoom: fitZoom, pan };
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

