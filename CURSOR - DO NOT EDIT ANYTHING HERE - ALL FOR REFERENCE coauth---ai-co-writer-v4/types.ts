

export interface StoryState {
  content: string;
  isGenerating: boolean;
  instruction: string;
  wordCount: number;
}

export enum ModelType {
  GEMINI_3_PRO = 'gemini-3-pro-preview',
  GEMINI_2_5_PRO = 'gemini-2.5-pro',
  GEMINI_2_5_FLASH = 'gemini-2.5-flash',
}

export interface StreamCallbacks {
  onChunk: (text: string) => void;
  onComplete: () => void;
  onError: (error: Error) => void;
}

// Legacy Chain types
export interface ChainNode {
  id: string;
  type: 'prompt' | 'refine';
  prompt: string;
  output?: string;
  status: 'idle' | 'running' | 'completed' | 'error';
}

// --- New Visual Graph Types ---

export type GraphNodeType = 'prompt' | 'context' | 'logic';

export interface GraphNodeData {
  label: string;
  content: string; // The user's prompt or context text
  output?: string; // The AI generation result
  status: 'idle' | 'running' | 'completed' | 'error';
  errorMessage?: string;
}

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  position: { x: number; y: number };
  data: GraphNodeData;
  width?: number;
  height?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export type GraphExecutionMode = 'final-only' | 'sequence';

export interface GraphInput {
  label: string;
  text: string;
  type: GraphNodeType;
}

export interface GraphTemplate {
    id: string;
    name: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
}

// --- World Building & Style Types ---

export interface BibleField {
  key: string;
  label: string;
  type: 'text' | 'textarea';
  required: boolean;
  placeholder?: string;
}

export interface BibleSchema {
  id: string; // e.g., 'character', 'custom_spell'
  name: string; // e.g., 'Character', 'Magic Spell'
  fields: BibleField[];
  isCustom: boolean;
}

export interface BibleEvent {
    id: string;
    description: string;
    contextSnippet?: string; // The text source that triggered this event
    timestamp?: string; // Could be "Chapter 1" or a date
}

export interface RelationshipModifier {
    id: string;
    reason: string;
    value: number; // e.g., -10 or +15
    timestamp?: string;
}

export interface BibleRelationship {
    targetId: string; // ID of the other entity (if known) or Name
    targetName: string; 
    type: string; // e.g., "Ally", "Rival", "Family"
    description: string;
    affinityScore?: number; // -100 (Hated) to 100 (Loved/Loyal). Default 0.
    modifiers?: RelationshipModifier[]; // History of why the score changed
}

export interface BibleItem {
  id: string;
  schemaId: string; // Link to the schema definition
  name: string;
  data: Record<string, string>; // Dynamic key-value pairs based on schema
  events?: BibleEvent[];
  relationships?: BibleRelationship[];
}

export interface StyleProfile {
  id: string;
  name: string;
  dna: string; // The extracted stylistic instructions
  negativeConstraints?: string; // What NOT to do
}

export type ScanFocus = 'entities' | 'events' | 'relationships';

export interface LoreSuggestion {
  type: 'new_entity' | 'update_entity' | 'new_event' | 'update_relationship';
  targetId?: string; // If 'update', the ID of the existing BibleItem
  name: string;      // The name of the entity found (or main actor)
  
  // For Entities
  schemaId?: string; 
  newSchemaName?: string; 
  data?: Record<string, string>; 
  
  // For Events
  eventDescription?: string;
  eventContext?: string;
  
  // For Relationships
  relTargetName?: string;
  relType?: string;
  relDescription?: string;
  
  // New: Affinity Logic
  relAffinityChange?: number; // e.g. -10
  relChangeReason?: string;   // e.g. "Betrayal in Chapter 3"

  reason: string;    // Why the AI suggests this
}

export type EditorScanMode = 'logic' | 'prose' | 'formatting' | 'humanization' | 'custom';

export interface EditorIssue {
  id: string;
  type: EditorScanMode;
  category: string; // e.g., "Contradiction", "Passive Voice", "Typos", "AI Cliché"
  description: string;
  snippet: string; // The exact text in the story
  fixSuggestion?: string; // The rewriten text
  bibleUpdate?: {        // Optional: Update the bible instead
      targetName: string;
      updates: Partial<BibleItem>;
  };
  explanation?: string;
}

// Backward compatibility alias if needed, but we will migrate
export type ConsistencyResult = EditorIssue;

// --- ADVISOR TYPES ---

export interface TextSuggestion {
    id: string;
    original: string; // The text to replace
    replacement: string; // The new text
    explanation?: string;
}

export interface AdvisorMessage {
    id: string;
    role: 'user' | 'model';
    content: string; // Can contain markdown and custom tags
    suggestions?: TextSuggestion[];
}

export interface AdvisorMode {
    id: string;
    name: string;
    description: string;
    systemInstruction: string;
}

// --- BOOK SETTINGS (TYPESETTER) ---

export interface BookSettings {
    trimSize: '6x9' | '5x8' | 'a5';
    fontFamily: 'merriweather' | 'garamond' | 'baskerville' | 'inter';
    fontSize: number; // pt
    lineHeight: number;
    marginTop: number; // inches
    marginBottom: number;
    marginLeft: number; // inner
    marginRight: number; // outer
    firstLineIndent: number; // em
    sceneBreakMarker: string;
    // New Typography Settings
    headingScale: number; // Multiplier, 1.0 to 3.0
    alignment: 'justify' | 'left';
}

// --- CONSTANTS ---

export const DEFAULT_BOOK_SETTINGS: BookSettings = {
    trimSize: '6x9',
    fontFamily: 'merriweather',
    fontSize: 11,
    lineHeight: 1.5,
    marginTop: 0.75,
    marginBottom: 0.75,
    marginLeft: 0.75, // Gutter
    marginRight: 0.5,
    firstLineIndent: 1.5,
    sceneBreakMarker: '* * *',
    headingScale: 1.0,
    alignment: 'justify'
};

export const DEFAULT_SCHEMAS: BibleSchema[] = [
    {
        id: 'character',
        name: 'Character',
        isCustom: false,
        fields: [
            { key: 'role', label: 'Role/Archetype', type: 'text', required: true, placeholder: 'e.g., Protagonist, Villain' },
            { key: 'appearance', label: 'Appearance', type: 'textarea', required: true, placeholder: 'Physical description...' },
            { key: 'personality', label: 'Personality', type: 'textarea', required: false, placeholder: 'Traits, quirks, flaws...' },
            { key: 'backstory', label: 'Backstory', type: 'textarea', required: false, placeholder: 'History and motivation...' }
        ]
    },
    {
        id: 'location',
        name: 'Location',
        isCustom: false,
        fields: [
            { key: 'region', label: 'Region/Setting', type: 'text', required: true, placeholder: 'e.g., Lower District' },
            { key: 'atmosphere', label: 'Atmosphere/Vibe', type: 'textarea', required: true, placeholder: 'Sensory details, mood...' },
            { key: 'history', label: 'History', type: 'textarea', required: false, placeholder: 'Key historical events...' }
        ]
    },
    {
        id: 'item',
        name: 'Item/Object',
        isCustom: false,
        fields: [
            { key: 'type', label: 'Item Type', type: 'text', required: true, placeholder: 'e.g., Weapon, Artifact' },
            { key: 'effect', label: 'Effect/Function', type: 'textarea', required: true, placeholder: 'What does it do?' },
            { key: 'origin', label: 'Origin', type: 'text', required: false, placeholder: 'Where did it come from?' }
        ]
    },
    {
        id: 'lore',
        name: 'Lore/Concept',
        isCustom: false,
        fields: [
            { key: 'description', label: 'Description', type: 'textarea', required: true, placeholder: 'Explain the concept...' },
            { key: 'impact', label: 'Impact on World', type: 'textarea', required: false, placeholder: 'How does it affect the story?' }
        ]
    }
];

export const DEFAULT_ADVISOR_MODES: AdvisorMode[] = [
    {
        id: 'critic',
        name: 'Ruthless Critic',
        description: 'Analyzes weaknesses, plot holes, and bad prose.',
        systemInstruction: 'You are a ruthless literary critic. Focus on pacing issues, weak dialogue, passive voice, and logical inconsistencies. Be harsh but constructive.'
    },
    {
        id: 'brainstormer',
        name: 'Brainstormer',
        description: 'Generates ideas, plot twists, and "what ifs".',
        systemInstruction: 'You are an enthusiastic creative partner. Generate wild ideas, plot twists, and "yes, and" suggestions. Focus on expanding the world and raising the stakes.'
    },
    {
        id: 'lore_keeper',
        name: 'Lore Keeper',
        description: 'Checks for continuity and suggests world-building.',
        systemInstruction: 'You are the keeper of the World Bible. Focus on ensuring the story matches the established lore. Suggest ways to weave in history, items, and character backstories.'
    },
    {
        id: 'editor',
        name: 'Line Editor',
        description: 'Polishes prose, grammar, and flow.',
        systemInstruction: 'You are a meticulous line editor. Focus on sentence structure, word choice, grammar, and flow. Suggest edits to make the prose sing.'
    },
    {
        id: 'custom',
        name: 'Custom Persona',
        description: 'Define your own advisor personality.',
        systemInstruction: '' // User defined
    }
];