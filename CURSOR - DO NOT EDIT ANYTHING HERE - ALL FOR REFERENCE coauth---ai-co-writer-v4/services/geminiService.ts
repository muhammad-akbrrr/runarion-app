

import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { ModelType, StreamCallbacks, GraphInput, StyleProfile, BibleSchema, GraphNode, GraphEdge, GraphExecutionMode, BibleItem, LoreSuggestion, EditorIssue, ScanFocus, AdvisorMessage, TextSuggestion, EditorScanMode } from "../types";

const apiKey = process.env.API_KEY;

if (!apiKey) {
  console.error("API_KEY is missing from environment variables.");
}

const ai = new GoogleGenAI({ apiKey: apiKey || 'dummy-key-to-prevent-crash' });

// --- CONSTANTS ---
const BANNED_AI_WORDS = [
    "tapestry", "symphony", "delve", "underscore", "vibrant", "testament", 
    "crucible", "nuance", "landscape", "realm", "foster", "invaluable", 
    "game-changer", "unleash", "elevate", "cutting-edge", "robust", 
    "transformative", "pivot", "synergy", "paradigm", "stark contrast", 
    "rich history", "testament to", "serves as", "a sense of"
];

// --- HELPER: Robust JSON Parser ---
const parseGeneratedJSON = <T>(text: string, fallback: T): T => {
    if (!text) return fallback;
    
    // 1. Try cleaning Markdown
    let clean = text.replace(/```json/g, '').replace(/```/g, '').trim();
    
    try {
        return JSON.parse(clean);
    } catch (e) {
        // 2. Try extracting Array structure
        if (Array.isArray(fallback)) {
            const start = text.indexOf('[');
            const end = text.lastIndexOf(']');
            if (start !== -1 && end !== -1 && end > start) {
                try {
                    return JSON.parse(text.substring(start, end + 1));
                } catch (e2) {
                    // console.warn("Failed to parse extracted array JSON", e2);
                }
            }
        } 
        // 3. Try extracting Object structure
        else {
            const start = text.indexOf('{');
            const end = text.lastIndexOf('}');
            if (start !== -1 && end !== -1 && end > start) {
                try {
                    return JSON.parse(text.substring(start, end + 1));
                } catch (e2) {
                    // console.warn("Failed to parse extracted object JSON", e2);
                }
            }
        }
        
        console.error("Critical JSON Parse Failure. Raw text:", text);
        return fallback;
    }
};

// --- HELPER: Retry with Exponential Backoff ---
async function retryWithBackoff<T>(
  fn: () => Promise<T>, 
  retries = 3, 
  baseDelay = 1000
): Promise<T> {
  try {
    return await fn();
  } catch (error: any) {
    // Robust check for 429 / Resource Exhausted
    const isRateLimit = 
        error.status === 429 || 
        error.response?.status === 429 ||
        error.message?.includes('429') ||
        error.message?.includes('RESOURCE_EXHAUSTED') ||
        error.message?.includes('quota');

    if (retries > 0 && isRateLimit) {
      const delay = baseDelay * Math.pow(2, 3 - retries) + Math.random() * 500;
      console.warn(`Rate limit hit (Quota/429). Retrying in ${Math.round(delay)}ms...`);
      await new Promise(r => setTimeout(r, delay));
      return retryWithBackoff(fn, retries - 1, baseDelay);
    }
    throw error;
  }
}

// --- HELPER: Format Bible Item with Rich Context (Events & Relations) ---
export const formatBibleItemForContext = (item: BibleItem): string => {
    let text = `--- ${item.name} (${item.schemaId}) ---\n`;
    
    // 1. Data Fields
    if (item.data) {
        Object.entries(item.data).forEach(([key, value]) => {
            if (value) text += `${key.toUpperCase()}: ${value}\n`;
        });
    }

    // 2. Timeline Events
    if (item.events && item.events.length > 0) {
        text += `\n[KNOWN HISTORY / TIMELINE]\n`;
        item.events.forEach(e => {
            text += `- (${e.timestamp || 'Unknown Time'}): ${e.description}\n`;
        });
    }

    // 3. Relationships
    if (item.relationships && item.relationships.length > 0) {
        text += `\n[RELATIONSHIPS]\n`;
        item.relationships.forEach(r => {
            const score = r.affinityScore !== undefined ? `[Score: ${r.affinityScore}]` : '';
            text += `- With ${r.targetName} (${r.type}): ${r.description} ${score}\n`;
        });
    }

    return text;
};

export const extractStyleDNA = async (
  sampleText: string,
  model: ModelType
): Promise<string> => {
  try {
    const prompt = `
      Analyze the provided text to extract its stylistic DNA.
      Focus on:
      1. Sentence structure (length, rhythm, complexity).
      2. Vocabulary (archaic, modern, technical, flowery).
      3. Tone and Voice (cynical, optimistic, detached, intimate).
      4. Pacing.

      Output a concise set of instructions (approx 100-150 words) that can be fed to an AI to replicate this style.
      Do not describe the content, only the style.
      
      TEXT SAMPLE:
      """
      ${sampleText.slice(0, 5000)}
      """
    `;

    const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
      model: model,
      contents: prompt,
    }));

    return response.text || "Style extraction failed.";
  } catch (error) {
    console.error("Style Extraction Error:", error);
    throw error;
  }
};

export const refineStyleInstruction = async (
    currentDna: string,
    instruction: string,
    model: ModelType
): Promise<string> => {
    try {
        const prompt = `
           You are a Style Editor.
           
           CURRENT STYLE DNA:
           "${currentDna}"
           
           USER REQUEST TO MODIFY:
           "${instruction}"
           
           Rewrite the Style DNA to incorporate the user's request while keeping the core essence of the original style (unless the user asks to change it completely).
           Return ONLY the new DNA text.
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));

        return response.text || currentDna;
    } catch (e) {
        return currentDna;
    }
};

export const suggestNegativeConstraints = async (
    dna: string,
    model: ModelType
): Promise<string> => {
    try {
        const prompt = `
           Analyze this writing style DNA and suggest a list of "Negative Constraints" (Things the AI should strictly AVOID doing to maintain this style).
           
           STYLE DNA:
           "${dna}"
           
           Return a comma-separated list or short sentences of what to avoid (e.g. "Avoid flowery adjectives, Do not use modern slang").
           Return ONLY the constraints text.
        `;
        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));
        return response.text || "";
    } catch (e) {
        return "";
    }
};

export const generateBibleAttributes = async (
  schema: BibleSchema,
  seed: string,
  model: ModelType
): Promise<Record<string, string>> => {
  try {
    const fieldsDesc = schema.fields.map(f => `- ${f.key} (${f.label}): ${f.placeholder}`).join('\n');
    
    const prompt = `
      You are a creative world-building assistant.
      Generate content for a World Bible Entry of type: "${schema.name}".
      
      The user has provided this seed idea: "${seed || 'Create something interesting and unique'}"
      
      Please generate specific, creative details for the following fields:
      ${fieldsDesc}

      Return the result strictly as a valid JSON object where keys match the field keys exactly.
      Do not wrap in markdown code blocks. Just the raw JSON string.
    `;

    const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
      model: model,
      contents: prompt,
      config: {
        responseMimeType: 'application/json'
      }
    }));
    
    return parseGeneratedJSON(response.text || "{}", {});

  } catch (error) {
    console.error("Attribute Generation Error:", error);
    throw error;
  }
};

export const scanForNewLore = async (
  storyText: string,
  existingItems: BibleItem[],
  schemas: BibleSchema[],
  model: ModelType,
  scanFocus: ScanFocus[] = ['entities', 'events', 'relationships']
): Promise<LoreSuggestion[]> => {
  try {
    const existingIndex = existingItems.map(i => ({ id: i.id, name: i.name, schema: i.schemaId }));
    const schemaSummary = schemas.map(s => `${s.id} (${s.name}): [${s.fields.map(f => f.key).join(', ')}]`).join('\n');

    let tasksPrompt = "";
    if (scanFocus.includes('entities')) tasksPrompt += `1. **New Entities**: Identify proper nouns (Characters, Locations, Items) not in the Bible. Suggest a Schema for them.\n`;
    if (scanFocus.includes('events')) tasksPrompt += `2. **Events (Timeline)**: Did a significant plot event happen to an existing character/location? (e.g., "Vex was injured").\n`;
    if (scanFocus.includes('relationships')) tasksPrompt += `3. **Relationships**: Look closely for interactions. Did the dynamic between two characters change? Quantify this with an 'Affinity Shift' (-100 to 100). E.g., if they argued, shift -10. If they saved each other, shift +20. Provide a reason.\n`;

    // UNCAP: Read FIRST 1,000,000 characters to build lore from start
    const textSlice = storyText.slice(0, 1000000);

    const prompt = `
      You are a "Lore Keeper" AI. 
      Your job is to read the story text and update the World Bible.
      
      EXISTING BIBLE ENTRIES:
      ${JSON.stringify(existingIndex)}
      
      AVAILABLE SCHEMAS (Categories):
      ${schemaSummary}
      
      STORY TEXT TO SCAN:
      """
      ${textSlice}
      """
      
      FOCUS TASKS:
      ${tasksPrompt}
      
      OUTPUT FORMAT (JSON Array of Objects):
      
      Type 'new_entity':
      {
        "type": "new_entity",
        "name": "Name",
        "schemaId": "schema_id",
        "newSchemaName": "Optional (if no existing schema fits)",
        "data": { "key": "value" },
        "reason": "Why?"
      }
      
      Type 'update_entity':
      {
        "type": "update_entity",
        "targetId": "existing_id",
        "name": "Name",
        "data": { "key": "new_value" }, // Only include changed fields
        "reason": "Why?"
      }

      Type 'new_event':
      {
        "type": "new_event",
        "targetId": "existing_id", // Who did this happen to?
        "name": "Character Name",
        "eventDescription": "What happened?",
        "eventContext": "Short quote from text source",
        "reason": "Plot significance"
      }

      Type 'update_relationship':
      {
        "type": "update_relationship",
        "targetId": "existing_id", // Subject (e.g., Vex)
        "name": "Subject Name",
        "relTargetName": "Other Character Name (e.g., Elara)",
        "relType": "Ally/Enemy/etc",
        "relDescription": "Details of relationship",
        "relAffinityChange": 0, // Integer (e.g. -10, +25)
        "relChangeReason": "Why did the score change? (e.g. 'Betrayal')",
        "reason": "Interaction in text"
      }
      
      Return ONLY the JSON array.
    `;

    const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
      model: model,
      contents: prompt,
      config: { responseMimeType: 'application/json' }
    }));

    return parseGeneratedJSON<LoreSuggestion[]>(response.text || "[]", []);

  } catch (e) {
    console.error("Lore Scan Error", e);
    throw e;
  }
};

export const runEditorScan = async (
    storyText: string,
    bibleItems: BibleItem[],
    modes: EditorScanMode[],
    customInstruction: string,
    model: ModelType
): Promise<EditorIssue[]> => {
    try {
        const bibleFullText = bibleItems.map(item => formatBibleItemForContext(item)).join('\n\n');

        // UNCAP: Read FIRST 1,000,000 characters
        const textSlice = storyText.slice(0, 1000000);

        let instructions = "";
        if (modes.includes('logic')) {
            instructions += `
            MODE: LOGIC & CONTINUITY
            - Compare story text against World Bible.
            - Find contradictions in facts, character traits, or history.
            - Check for timeline errors.
            `;
        }
        if (modes.includes('prose')) {
            instructions += `
            MODE: PROSE & STYLE
            - "Show, Don't Tell" Detector: Identify filter words (e.g., "he saw", "she felt", "it was sad", "he heard") that distance the reader. Suggest visceral rewrites that describe the physical sensation.
            - Rhythm Check: Flag clusters of 3+ sentences with identical structure or length (e.g., Subject-Verb-Object). Flag repetitive sentence starters.
            - Weak Verbs: Flag excessive use of 'to be' verbs and '-ly' adverbs.
            `;
        }
        if (modes.includes('humanization')) {
            instructions += `
            MODE: HUMANIZATION (DE-AI)
            - Identify "AI Clichés" and robotic vocabulary. STRICTLY FLAG the following words if used in a flowery way: ${BANNED_AI_WORDS.join(', ')}.
            - Flag overly balanced or perfect sentence structures that lack human "grit".
            - Flag "moralizing" conclusions or summaries at the end of scenes.
            - Label these issues as type 'humanization' and category 'AI Cliché' or 'Robotic Tone'.
            `;
        }
        if (modes.includes('formatting')) {
            instructions += `
            MODE: FORMATTING, SPELLING & GRAMMAR
            - ACT AS A SPELLCHECKER: Flag any typos or misspelled words.
            - ACT AS A GRAMMAR CHECKER: Flag incorrect subject-verb agreement, misused punctuation, or confusing syntax.
            - Check for proper dialogue punctuation (e.g., punctuation inside quotes).
            - Identify paragraphs that are too long (>10 lines).
            `;
        }
        if (modes.includes('custom') && customInstruction) {
            instructions += `
            MODE: CUSTOM INSTRUCTION
            - ${customInstruction}
            `;
        }

        const prompt = `
            You are an Expert Book Editor (Developmental, Copy Editor & Proofreader). Run a scan on the following manuscript.

            WORLD BIBLE (Truth Source for Logic checks):
            """
            ${bibleFullText}
            """

            STORY TEXT (To Audit):
            """
            ${textSlice}
            """

            TASKS:
            ${instructions}

            CRITICAL RULES:
            1. For every issue found, the 'snippet' field MUST be an EXACT, CHARACTER-FOR-CHARACTER COPY of the text in the story. Include 1 sentence of surrounding context to ensure uniqueness for search-and-replace.
            2. Provide a 'fixSuggestion' that rewrites the snippet to solve the problem.
            3. Return a JSON Array.

            OUTPUT FORMAT:
            [
                { 
                    "type": "logic" | "prose" | "formatting" | "humanization" | "custom",
                    "category": "e.g. Contradiction, Passive Voice, AI Cliché, Spelling",
                    "description": "Short explanation of the error", 
                    "snippet": "EXACT UNIQUE TEXT from story",
                    "fixSuggestion": "Rewritten version",
                    "bibleUpdate": { "targetName": "...", "updates": { ... } } // Only if Bible is wrong/incomplete
                }
            ]
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt,
            config: { responseMimeType: 'application/json' }
        }));

        return parseGeneratedJSON<EditorIssue[]>(response.text || "[]", []);

    } catch (e) {
        console.error("Editor Scan Error", e);
        throw e;
    }
};

export const assessNaturalness = async (
    text: string,
    model: ModelType
): Promise<{ score: number, summary: string }> => {
    try {
        const prompt = `
            Analyze the following text for "Artificiality" vs "Human Naturalness".
            
            TEXT TO ANALYZE:
            """
            ${text.slice(0, 10000)}
            """
            
            CRITERIA:
            - AI often uses specific clichés (${BANNED_AI_WORDS.slice(0, 10).join(', ')}...).
            - AI often has perfect, rhythmic balance and moralizing tones.
            - Humans use sentence fragments, run-on sentences, irregular rhythm, and concrete, gritty details.
            
            Rate the "Naturalness" from 0 to 100.
            0 = Obviously Synthetic/AI (Robotic, Cliché-ridden).
            100 = Distinctly Human (Voice, Flaws, Unique Rhythm).
            
            Return JSON: { "score": number, "summary": "Short explanation of why" }
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt,
            config: { responseMimeType: 'application/json' }
        }));

        return parseGeneratedJSON(response.text || "{}", { score: 50, summary: "Analysis failed" });
    } catch (e) {
        console.error("Naturalness Assessment Error", e);
        return { score: 0, summary: "Error" };
    }
};

export const humanizeSelection = async (
    selection: string,
    model: ModelType
): Promise<string> => {
    try {
        const prompt = `
            You are a "Humanizer" Editor. 
            Rewrite the following text to sound MORE HUMAN and LESS AI.
            
            Directives:
            1. INCREASE BURSTINESS: Vary sentence length aggressively. Use fragments. Use run-ons.
            2. REMOVE AI CLICHÉS: Do not use words like ${BANNED_AI_WORDS.slice(0, 5).join(', ')}.
            3. BE GRITTY: Remove polish. Add texture. Focus on sensory details rather than abstract summaries.
            4. REMOVE FILTER WORDS: Change "he saw" to the image itself.
            
            TEXT:
            "${selection}"
            
            Output ONLY the rewritten text.
        `;
        
        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));
        
        return response.text?.trim() || selection;
    } catch (e) {
        console.error("Humanize Error", e);
        throw e;
    }
};

export const processInlineSelection = async (
    selection: string,
    instruction: string,
    storyContext: string,
    model: ModelType,
    styleProfile: StyleProfile | null
): Promise<string> => {
    try {
        const styleInstruction = styleProfile 
          ? `\nSTYLE GUIDELINES (Strictly Adhere to this DNA):\n${styleProfile.dna}\n` 
          : "";
        
        const negativeConstraints = styleProfile?.negativeConstraints
          ? `\nNEGATIVE CONSTRAINTS (Do NOT do this):\n${styleProfile.negativeConstraints}\n`
          : "";

        const prompt = `
           You are an expert literary editor.
           Your task is to REWRITE the selected text based on the user's instruction.
           
           FULL STORY CONTEXT (For reference):
           """
           ${storyContext.slice(-20000)}...
           """
           
           SELECTED TEXT TO MODIFY:
           """
           ${selection}
           """
           
           USER INSTRUCTION: "${instruction}"
           
           ${styleInstruction}
           ${negativeConstraints}
           
           Return ONLY the rewritten version of the selected text. Do not add quotes or filler.
        `;
        
        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));
        
        return response.text?.trim() || selection;
    } catch (e) {
        console.error("Inline Edit Error", e);
        throw e;
    }
};

export const continueStory = async (
  currentContent: string,
  instruction: string,
  model: ModelType,
  styleProfile: StyleProfile | null,
  callbacks: StreamCallbacks,
  userNegativeConstraints?: string
) => {
  try {
    const styleInstruction = styleProfile 
      ? `\nSTYLE GUIDELINES (Strictly Adhere to this DNA):\n${styleProfile.dna}\n` 
      : "";
    
    // Combine style profile constraints with on-the-fly user constraints
    const constraintsList = [
        styleProfile?.negativeConstraints,
        userNegativeConstraints
    ].filter(Boolean).join('\n');

    const negativePrompt = constraintsList
      ? `\nNEGATIVE CONSTRAINTS (Do NOT do this):\n${constraintsList}\n`
      : "";

    const prompt = `
      You are an expert literary co-writer. 
      Your task is to continue the story seamlessly from the text provided below.
      
      STORY SO FAR:
      """
      ${currentContent}
      """
      
      USER INSTRUCTION:
      ${instruction ? instruction : "Continue the story naturally."}
      ${styleInstruction}
      ${negativePrompt}

      GUIDELINES:
      - Match the tone, style, and voice of the existing text (and the Style DNA if provided).
      - Do not repeat the last sentence provided; just write what comes next.
      - Output ONLY the continuation text. Do not add conversational filler like "Here is the continuation".
    `;

    let thinkingBudget = 0;
    
    if (model === ModelType.GEMINI_3_PRO || model === ModelType.GEMINI_2_5_PRO) {
      thinkingBudget = 4096; 
    } else if (model === ModelType.GEMINI_2_5_FLASH) {
      thinkingBudget = 2048;
    }

    // Stream generation also wrapped in try/catch but streaming logic prevents easy retry wrapper without re-implementing stream handling.
    // For now, streaming is direct. Retry logic is critical for non-streaming batch ops.
    const streamResult = await ai.models.generateContentStream({
      model: model,
      contents: prompt,
      config: {
        thinkingConfig: thinkingBudget > 0 ? { thinkingBudget } : undefined,
      }
    });

    for await (const chunk of streamResult) {
      const text = chunk.text;
      if (text) {
        callbacks.onChunk(text);
      }
    }

    callbacks.onComplete();

  } catch (error) {
    console.error("Gemini Generation Error:", error);
    callbacks.onError(error instanceof Error ? error : new Error("Unknown error occurred"));
  }
};

export const runChainStep = async (
  nodePrompt: string,
  previousContext: string,
  storyContext: string,
  model: ModelType
): Promise<string> => {
  try {
    const fullPrompt = `
      You are a specialized story logic processor.
      
      CONTEXT (Story so far):
      """
      ${storyContext.slice(0, 500000)} ... (truncated for focus)
      """

      INPUT FROM PREVIOUS STEP:
      """
      ${previousContext || "None (First Step)"}
      """

      TASK FOR THIS STEP:
      ${nodePrompt}

      Output only the result of the task.
    `;

    const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
      model: model,
      contents: fullPrompt,
    }));

    return response.text || "";
  } catch (error) {
    console.error("Chain Step Error:", error);
    throw error;
  }
};

export const runGraphNode = async (
  nodePrompt: string,
  inputs: GraphInput[],
  storyContext: string,
  model: ModelType,
  styleProfile: StyleProfile | null
): Promise<string> => {
  try {
    const styleInstruction = styleProfile 
      ? `\nSTYLE GUIDELINES (Strictly Adhere to this DNA):\n${styleProfile.dna}\n` 
      : "";

    const negativeConstraints = styleProfile?.negativeConstraints
      ? `\nNEGATIVE CONSTRAINTS (Do NOT do this):\n${styleProfile.negativeConstraints}\n`
      : "";

    const inputsText = inputs.map((input) => {
      const typeLabel = input.type === 'context' ? 'BACKGROUND DATA' : 'PREVIOUS STEP OUTPUT';
      return `--- ${typeLabel} (${input.label}) ---\n${input.text}\n-------------------`;
    }).join("\n\n");

    // UNCAP: Read 500k context (focused on end for continuation)
    const textSlice = storyContext.slice(-500000);

    const fullPrompt = `
      You are a specialized creative writing engine component.
      
      You are part of a node-based workflow. Your job is to execute your specific instruction, taking into account the inputs from previous nodes.

      GLOBAL STORY CONTEXT (The story so far):
      """
      ${textSlice} ...
      """

      INPUTS FROM CONNECTED NODES (Data/Logic):
      ${inputsText.length > 0 ? inputsText : "No upstream inputs."}

      YOUR INSTRUCTION:
      ${nodePrompt}

      ${styleInstruction}
      ${negativeConstraints}

      Execute the instruction using the provided Data and Context. 
      If you are a 'Prompt' node, generate the actual story text requested.
      If you are a 'Logic' node, perform the analysis or refinement requested.
      Return ONLY the result of your specific node's task.
    `;

    const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
      model: model,
      contents: fullPrompt,
    }));

    return response.text || "";
  } catch (error) {
    console.error("Graph Node Error:", error);
    throw error;
  }
};

export const generateNodeInstruction = async (
    seed: string,
    inputs: GraphInput[],
    storyContext: string,
    model: ModelType
): Promise<string> => {
    try {
        const inputsText = inputs.map(i => `SOURCE: ${i.label}\nCONTENT: ${i.text}`).join('\n\n');
        
        const prompt = `
           You are a "Director AI". Your job is to write a precise, effective Prompt Instruction for another AI to execute.
           
           USER GOAL (Seed Idea): "${seed}"
           
           AVAILABLE CONTEXT/RESOURCES:
           ${inputsText}
           
           STORY CONTEXT:
           ${storyContext.slice(-20000)}...

           Based on the user's goal and the available resources (Characters, Locations, Logic), write a robust paragraph of instructions.
           Tell the AI exactly what to write, how to incorporate the characters provided, and how to advance the plot.
           
           Return ONLY the instruction text.
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));

        return response.text || seed;

    } catch (e) {
        console.error("Magic Wand Error", e);
        return seed;
    }
};

export const generateGraphLayout = async (
    userGoal: string,
    storyContext: string,
    bibleItems: BibleItem[],
    mode: GraphExecutionMode,
    model: ModelType
): Promise<{ nodes: GraphNode[], edges: GraphEdge[] }> => {
    try {
        // Use formatted bible items so the Auto-Builder sees events/relationships
        const bibleSummary = bibleItems.map(item => formatBibleItemForContext(item)).join('\n\n');

        const modeInstruction = mode === 'sequence' 
            ? "DESIGN FOR SEQUENCE MODE: Connect prompt nodes in a LINEAR chain (A -> B -> C) where each node writes a subsequent part of the story."
            : "DESIGN FOR FINAL-ONLY MODE: Design a flow where context and logic nodes feed into a FINAL prompt node. The intermediate nodes should process data, not write story segments.";

        // UNCAP: Read up to 500,000 characters
        const textSlice = storyContext.slice(-500000);

        const prompt = `
           You are an AI Graph Architect. 
           Create a Logic Graph (Workflow) for a story writing app based on the user's goal.
           
           STORY CONTEXT (The story so far):
           """
           ${textSlice}...
           """

           AVAILABLE WORLD BIBLE ASSETS (Rich Context):
           """
           ${bibleSummary || "No bible assets available."}
           """
           
           USER GOAL: "${userGoal}"
           
           OPTIMIZATION STRATEGY:
           ${modeInstruction}
           
           Available Node Types:
           - 'prompt': Writes story text.
           - 'context': Static background info (Prefer using Bible Assets if they match!).
           - 'logic': Performs checks, critiques, or brainstorming (does not write final story text).

           Return a JSON object with 'nodes' and 'edges'. 
           - Assign strict string IDs (e.g., 'n1', 'n2').
           - Position nodes visually in a logical flow (Top to Bottom). Start at x:0, y:0 and space them out by y+250.
           - Connect them logically.
           - IMPORTANT: If the user goal involves a character/location from the Bible assets, create a 'context' node pre-filled with their RICH details (Events/Relations).
           - CRITICAL RULE: Create separate 'context' nodes for each specific Bible entity involved. Do NOT create a single 'World Bible Context' lump node. Each entity must have its own draggable node.

           Example Structure:
           {
             "nodes": [
               { "id": "n1", "type": "context", "position": {"x": 0, "y": 0}, "data": { "label": "Char Bio", "content": "..." } },
               { "id": "n2", "type": "prompt", "position": {"x": 0, "y": 200}, "data": { "label": "Scene Start", "content": "..." } }
             ],
             "edges": [ { "id": "e1", "source": "n1", "target": "n2" } ]
           }

           Return ONLY the JSON.
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt,
            config: { responseMimeType: 'application/json' }
        }));

        return parseGeneratedJSON(response.text || "{}", { nodes: [], edges: [] });

    } catch (e) {
        console.error("Auto Graph Error", e);
        throw e;
    }
};

export const refineGraphSelection = async (
    selectedNodes: GraphNode[],
    selectedEdges: GraphEdge[],
    instruction: string,
    storyContext: string,
    model: ModelType
): Promise<{ nodes: GraphNode[], edges: GraphEdge[] }> => {
    try {
        const prompt = `
           You are an expert Story Logic Engineer.
           You are provided with a SUBSET of a node graph.
           
           STORY CONTEXT:
           """
           ${storyContext.slice(-500000)}...
           """

           YOUR TASK: Refine, Expand, or Modify this subset based on the user's instruction.
           
           USER INSTRUCTION: "${instruction}"
           
           CURRENT SUBSET JSON:
           ${JSON.stringify({ nodes: selectedNodes, edges: selectedEdges }, null, 2)}
           
           RULES:
           1. Return a NEW JSON object with 'nodes' and 'edges' representing the improved flow.
           2. You can add new nodes (e.g., breaking a prompt into 3 steps), remove nodes, or change node content.
           3. Use specific names/details from the Story Context in your new nodes.
           4. Use unique IDs for new nodes (e.g., 'new_1', 'new_2').
           5. Keep the general position coordinates similar but adjust spacing so they don't overlap.
           
           Return ONLY the JSON.
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt,
            config: { responseMimeType: 'application/json' }
        }));

        const fallback = { nodes: selectedNodes, edges: selectedEdges };
        const parsed = parseGeneratedJSON(response.text || "{}", fallback);

        // Safety check to ensure parsed result has expected structure
        if (!parsed || !Array.isArray(parsed.nodes)) {
            return fallback;
        }

        if (parsed.nodes) {
            parsed.nodes = parsed.nodes.map((n: any) => ({
                ...n,
                data: { ...n.data, status: 'idle' } // Reset status
            }));
        }
        return parsed;
    } catch (e) {
        console.error("Refine Graph Error", e);
        throw e;
    }
};

export const chatWithAdvisor = async (
    messageHistory: AdvisorMessage[],
    newMessage: string,
    storyContext: string,
    bibleItems: BibleItem[],
    activeStyle: StyleProfile | null,
    instruction: string, // System instruction for mode
    model: ModelType
): Promise<AdvisorMessage> => {
    try {
        const bibleSummary = bibleItems.map(item => formatBibleItemForContext(item)).join('\n\n');
        
        // UNCAP: Read FIRST 1,000,000 characters to see the START of the book
        const context = `
            STORY CONTENT:
            """
            ${storyContext.slice(0, 1000000)}
            """
            
            WORLD BIBLE:
            """
            ${bibleSummary}
            """
            
            ACTIVE STYLE DNA:
            ${activeStyle ? activeStyle.dna : "None"}
        `;

        const prompt = `
            You are an Expert AI Writing Advisor.
            
            YOUR PERSONA/INSTRUCTION:
            ${instruction}
            
            CONTEXT:
            ${context}
            
            CHAT HISTORY:
            ${messageHistory.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n')}
            
            USER'S NEW MESSAGE:
            "${newMessage}"
            
            INSTRUCTIONS:
            1. Respond conversationally to the user's message.
            2. If you suggest specific text changes to the story, YOU MUST USE THE FOLLOWING FORMAT block for EACH suggestion at the end of your response:
            
            :::suggestion {"original": "exact text to replace", "replacement": "new text", "explanation": "why"} :::
            
            Example:
            "I think the dialogue in the second paragraph is weak. Here is a fix:
            :::suggestion {"original": "He said hi.", "replacement": "He nodded, eyes cold.", "explanation": "Show, don't tell."} :::"
            
            3. Ensure the "original" text matches the story content EXACTLY so it can be programmatically replaced.
        `;

        const response = await retryWithBackoff<GenerateContentResponse>(() => ai.models.generateContent({
            model: model,
            contents: prompt
        }));

        const text = response.text || "I'm having trouble thinking right now.";
        
        // Parse suggestions
        const suggestions: TextSuggestion[] = [];
        const suggestionRegex = /:::suggestion\s*({[\s\S]*?})\s*:::/g;
        let match;
        
        let cleanedText = text;

        while ((match = suggestionRegex.exec(text)) !== null) {
            try {
                const json = JSON.parse(match[1]);
                suggestions.push({
                    id: Date.now() + Math.random().toString(),
                    original: json.original,
                    replacement: json.replacement,
                    explanation: json.explanation
                });
                // Remove the raw JSON block from the display text to keep it clean
                cleanedText = cleanedText.replace(match[0], '').trim();
            } catch (e) {
                console.error("Failed to parse suggestion JSON", e);
            }
        }

        return {
            id: Date.now().toString(),
            role: 'model',
            content: cleanedText,
            suggestions: suggestions.length > 0 ? suggestions : undefined
        };

    } catch (e) {
        console.error("Advisor Chat Error", e);
        throw e;
    }
};