// Format entity from Records system for use in context nodes

import { Entity } from '../types';

export const formatEntityForContext = (entity: Entity): string => {
    let text = `--- ${entity.name} (${entity.type}) ---\n`;
    
    // Format properties
    if (entity.properties && Object.keys(entity.properties).length > 0) {
        Object.entries(entity.properties).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                const formattedKey = key
                    .split('_')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');
                text += `${formattedKey}: ${value}\n`;
            }
        });
    } else {
        text += `No additional properties defined.\n`;
    }
    
    // TODO: Add relationships if needed (from novel_graph_edges)
    // Could fetch relationships for this entity and format them
    
    return text;
};

