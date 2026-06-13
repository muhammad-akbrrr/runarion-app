import { useState, useEffect, useRef } from "react";
import { Button } from "@/Components/ui/button";
import { Label } from "@/Components/ui/label";
import { Textarea } from "@/Components/ui/textarea";
import { Input } from "@/Components/ui/input";
import { Slider } from "@/Components/ui/slider";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/Components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/Components/ui/tooltip";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/Components/ui/dialog";
import { ScrollArea } from "@/Components/ui/scroll-area";
import { toast } from "sonner";
import {
    HelpCircle,
    Plus,
    Trash2,
    MoreHorizontal,
    Send,
    Loader2,
    Settings2,
    MessageSquare,
    ChevronDown,
    Check,
    X,
    Bot,
    User,
    Sparkles,
    RefreshCw,
    Copy,
    Eraser,
    Edit3,
    Wand2,
    MessageCircle,
} from "lucide-react";
import {
    usePendingEdits,
} from "../../Contexts/PendingEditsContext";
import { MagicWandButton } from "@/Components/MagicWandButton";
import Echo from "@/echo";
import { http, normalizeHttpError } from "@/Lib/http";

interface AdvisorChat {
    id: string;
    title: string;
    model: string;
    system_instructions: string | null;
    message_count: number;
    created_at: string;
    updated_at: string;
}

interface AdvisorMessage {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    metadata?: Record<string, any>;
    created_at: string;
}

import { ProjectSettings, MODEL_CONFIGS } from "@/types/project";

interface AdvisorStreamSession {
    chatId: string;
    sessionId: string;
    fullContent: string;
}

interface AdvisorStreamStartedEvent {
    workspace_id: string;
    project_id: string;
    chat_id: string;
    session_id: string;
    user_message_id?: string | null;
}

interface AdvisorStreamChunkEvent {
    workspace_id: string;
    project_id: string;
    chat_id: string;
    session_id: string;
    chunk: string;
    chunk_index: number;
}

interface AdvisorStreamCompletedEvent {
    workspace_id: string;
    project_id: string;
    chat_id: string;
    session_id: string;
    success: boolean;
    message_id?: string | null;
    user_message_id?: string | null;
    error?: string | null;
    cancelled: boolean;
}

interface AdvisorTabProps {
    workspaceId: string;
    projectId: string;
    onApplyEdit?: (oldText: string, newText: string) => Promise<boolean>;
    settings?: Partial<ProjectSettings>;
    onSettingChange?: (key: keyof ProjectSettings, value: any) => void;
    onSavingChange?: (isSaving: boolean) => void;
}

// Available models — derived from MODEL_CONFIGS
const AVAILABLE_MODELS = Object.values(MODEL_CONFIGS).map((mc) => ({
    value: mc.id,
    label: mc.label,
    thinking: mc.supportsThinking,
}));

const DEFAULT_SYSTEM_INSTRUCTIONS = `You are an expert writing advisor and creative assistant. You have access to the full story context and can help with:

1. **Story Analysis**: Analyze plot, characters, pacing, themes, and narrative structure
2. **Writing Suggestions**: Offer improvements for dialogue, descriptions, and prose style
3. **Continuity Checking**: Identify inconsistencies in the story
4. **Brainstorming**: Help develop ideas, plot points, and character arcs
5. **Editing**: Suggest specific text changes when asked

When suggesting edits to the text, use this format:
<<<EDIT>>>
CHAPTER: [chapter name or number - chapters are numbered starting from 1, NOT 0]
LOCATION: [brief description of where in the text]
OLD: [exact text to replace]
NEW: [suggested replacement text]
REASON: [why this change improves the story]
<<<END_EDIT>>>

IMPORTANT RULES:
- Always provide thorough, detailed responses. When analyzing story content, quote relevant passages and provide comprehensive analysis.
- Do not give overly brief answers - be helpful and expansive in your responses.
- Reference specific parts of the story when relevant.
- Chapters are numbered starting from 1 (Chapter 1, Chapter 2, etc.). There is NO Chapter 0.`;

export default function AdvisorTab({
    workspaceId,
    projectId,
    onApplyEdit,
    settings,
    onSettingChange,
    onSavingChange,
}: AdvisorTabProps) {
    // Pending edits context for agent mode
    const {
        advisorMode,
        setAdvisorMode,
        addPendingEdits,
        pendingEdits,
        clearAllEdits,
    } = usePendingEdits();

    // Chat state
    const [chats, setChats] = useState<AdvisorChat[]>([]);
    const [activeChat, setActiveChat] = useState<AdvisorChat | null>(null);
    const [messages, setMessages] = useState<AdvisorMessage[]>([]);
    const [isLoadingChats, setIsLoadingChats] = useState(true);
    const [isLoadingMessages, setIsLoadingMessages] = useState(false);

    // Input state
    const [inputMessage, setInputMessage] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingContent, setStreamingContent] = useState("");

    // Settings state - local state for active session, with defaults from project settings
    const [showSettings, setShowSettings] = useState(false);
    const [selectedModel, setSelectedModel] = useState(
        settings?.advisorModel || "gemini-2.5-flash",
    );
    const [systemInstructions, setSystemInstructions] = useState(
        settings?.advisorSystemInstructions || DEFAULT_SYSTEM_INSTRUCTIONS,
    );
    const [thinkingBudget, setThinkingBudget] = useState(
        settings?.advisorThinkingBudget || 4096,
    );
    const [outputLength, setOutputLength] = useState(
        settings?.advisorOutputLength || 4000,
    ); // Increased default for more detailed responses
    const [temperature, setTemperature] = useState(
        settings?.advisorTemperature || 0.8,
    );

    // UI state
    const [showChatList, setShowChatList] = useState(false);
    const [showActions, setShowActions] = useState(false);
    const [editingTitle, setEditingTitle] = useState(false);
    const [titleValue, setTitleValue] = useState("");
    const [deleteConfirmChat, setDeleteConfirmChat] =
        useState<AdvisorChat | null>(null);

    // Message editing state
    const [editingMessageIndex, setEditingMessageIndex] = useState<
        number | null
    >(null);
    const [editingMessageContent, setEditingMessageContent] = useState("");

    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const chatListRef = useRef<HTMLDivElement>(null);
    const actionsRef = useRef<HTMLDivElement>(null);
    const pendingAfterMessagesRef = useRef<AdvisorMessage[]>([]); // Messages to append after edit completes
    const sentEditsRef = useRef<Set<string>>(new Set()); // Track sent edits to avoid duplicates
    const prevModeRef = useRef<"chat" | "agent">(advisorMode);
    const streamSessionRef = useRef<AdvisorStreamSession | null>(null);

    // Re-queue edits when switching to Agent mode
    useEffect(() => {
        if (advisorMode === "agent" && prevModeRef.current === "chat") {
            // Switching to Agent mode - clear sent edits cache and re-queue from ALL assistant messages
            sentEditsRef.current.clear();

            // Collect edits from ALL assistant messages (not just the latest)
            const allEditSuggestions: Array<{
                chapter: string;
                oldText: string;
                newText: string;
                reason: string;
            }> = [];

            const editRegex = /<<<EDIT>>>([\s\S]*?)<<<END_EDIT>>>/g;

            // Process all assistant messages
            messages
                .filter((m) => m.role === "assistant")
                .forEach((msg) => {
                    const matches = [...msg.content.matchAll(editRegex)];
                    matches.forEach((match) => {
                        const editContent = match[1];
                        const oldMatch = editContent.match(
                            /OLD:\s*([\s\S]*?)(?=NEW:|$)/,
                        );
                        const newMatch = editContent.match(
                            /NEW:\s*([\s\S]*?)(?=REASON:|$)/,
                        );
                        const reasonMatch = editContent.match(
                            /REASON:\s*([\s\S]*?)$/,
                        );
                        const chapterMatch = editContent.match(
                            /CHAPTER:\s*(.*?)(?=\n|$)/,
                        );

                        const oldText = oldMatch?.[1]?.trim() || "";
                        const newText = newMatch?.[1]?.trim() || "";

                        // Only add if we have both old and new text, and it's not a duplicate
                        if (oldText && newText) {
                            // Check for duplicates (same oldText)
                            const isDuplicate = allEditSuggestions.some(
                                (e) => e.oldText === oldText,
                            );
                            if (!isDuplicate) {
                                allEditSuggestions.push({
                                    chapter: chapterMatch?.[1]?.trim() || "",
                                    oldText,
                                    newText,
                                    reason: reasonMatch?.[1]?.trim() || "",
                                });
                            }
                        }
                    });
                });

            if (allEditSuggestions.length > 0) {
                console.log(
                    "[AdvisorTab] Re-queueing edits from all messages for Agent mode:",
                    allEditSuggestions.length,
                );
                // Clear old edits and add fresh ones
                clearAllEdits();
                addPendingEdits(allEditSuggestions);
            }
        }
        prevModeRef.current = advisorMode;
    }, [advisorMode, messages, clearAllEdits, addPendingEdits]);

    // Close dropdowns when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                chatListRef.current &&
                !chatListRef.current.contains(e.target as Node)
            ) {
                setShowChatList(false);
            }
            if (
                actionsRef.current &&
                !actionsRef.current.contains(e.target as Node)
            ) {
                setShowActions(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () =>
            document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streamingContent]);

    // Load chats on mount
    useEffect(() => {
        loadChats();
    }, [workspaceId, projectId]);

    // Load messages when active chat changes
    useEffect(() => {
        if (activeChat) {
            loadMessages(activeChat.id);
            setSelectedModel(activeChat.model);
            setSystemInstructions(
                activeChat.system_instructions || DEFAULT_SYSTEM_INSTRUCTIONS,
            );
            setTitleValue(activeChat.title);
        } else {
            setMessages([]);
            setTitleValue("");
        }
    }, [activeChat?.id]);

    useEffect(() => {
        const channelName = `project.${workspaceId}.${projectId}`;
        const channel = Echo.channel(channelName);

        channel.listen(".advisor.stream.started", (event: AdvisorStreamStartedEvent) => {
            if (
                streamSessionRef.current &&
                event.chat_id === streamSessionRef.current.chatId &&
                event.session_id === streamSessionRef.current.sessionId
            ) {
                setIsStreaming(true);
            }
        });

        channel.listen(".advisor.stream.chunk", (event: AdvisorStreamChunkEvent) => {
            if (
                !streamSessionRef.current ||
                event.chat_id !== streamSessionRef.current.chatId ||
                event.session_id !== streamSessionRef.current.sessionId
            ) {
                return;
            }

            streamSessionRef.current.fullContent += event.chunk ?? "";
            setStreamingContent(streamSessionRef.current.fullContent);
        });

        channel.listen(".advisor.stream.completed", (event: AdvisorStreamCompletedEvent) => {
            if (
                !streamSessionRef.current ||
                event.chat_id !== streamSessionRef.current.chatId ||
                event.session_id !== streamSessionRef.current.sessionId
            ) {
                return;
            }

            const fullContent = streamSessionRef.current.fullContent;
            const afterMessages = pendingAfterMessagesRef.current;
            pendingAfterMessagesRef.current = [];
            streamSessionRef.current = null;
            setIsStreaming(false);
            setStreamingContent("");

            if (event.cancelled) {
                return;
            }

            if (!event.success) {
                const errorMsg: AdvisorMessage = {
                    id: `error-${Date.now()}`,
                    role: "assistant",
                    content: `❌ Error: ${event.error || "Failed to generate response"}. Please try again.`,
                    created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, errorMsg]);
                return;
            }

            if (!fullContent) {
                return;
            }

            const assistantMsg: AdvisorMessage = {
                id: event.message_id || `assistant-${Date.now()}`,
                role: "assistant",
                content: fullContent,
                created_at: new Date().toISOString(),
            };

            setMessages((prev) => {
                const updated = prev.map((msg) => {
                    if (
                        msg.id.startsWith("pending-user-") &&
                        event.user_message_id
                    ) {
                        return {
                            ...msg,
                            id: event.user_message_id,
                        };
                    }

                    return msg;
                });

                if (
                    updated.some(
                        (msg) =>
                            msg.role === "assistant" &&
                            msg.content === fullContent,
                    )
                ) {
                    return updated;
                }

                return [...updated, assistantMsg, ...afterMessages];
            });
        });

        return () => {
            channel.stopListening(".advisor.stream.started");
            channel.stopListening(".advisor.stream.chunk");
            channel.stopListening(".advisor.stream.completed");
            Echo.leave(channelName);
        };
    }, [workspaceId, projectId]);

    const isThinkingModel =
        AVAILABLE_MODELS.find((m) => m.value === selectedModel)?.thinking ??
        false;

    // Get model-specific parameter config for advisor sliders
    const advisorModelConfig = MODEL_CONFIGS[selectedModel];

    const loadChats = async () => {
        setIsLoadingChats(true);
        try {
            const { data } = await http.get(
                route("advisor.chats.list", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
            );
            if (data.success) {
                setChats(data.chats);
                if (data.chats.length > 0 && !activeChat) {
                    setActiveChat(data.chats[0]);
                }
            }
        } catch (error) {
            console.error("Error loading chats:", error);
        } finally {
            setIsLoadingChats(false);
        }
    };

    const loadMessages = async (chatId: string) => {
        setIsLoadingMessages(true);
        try {
            const { data } = await http.get(
                route("advisor.messages.get", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: chatId,
                }),
            );
            if (data.success) {
                setMessages(data.messages);
            }
        } catch (error) {
            console.error("Error loading messages:", error);
        } finally {
            setIsLoadingMessages(false);
        }
    };

    const createNewChat = async () => {
        setShowChatList(false);
        setShowActions(false);
        onSavingChange?.(true);
        try {
            const { data } = await http.post(
                route("advisor.chats.create", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                }),
                {
                    title: "New Chat",
                    model: selectedModel,
                    system_instructions: systemInstructions,
                },
            );
            if (data.success) {
                setChats((prev) => [data.chat, ...prev]);
                setActiveChat(data.chat);
                setMessages([]);
            }
        } catch (error) {
            console.error("Error creating chat:", error);
        } finally {
            onSavingChange?.(false);
        }
    };

    const updateChatTitle = async () => {
        if (!activeChat || !titleValue.trim()) return;
        setEditingTitle(false);
        onSavingChange?.(true);
        try {
            const { data } = await http.put(
                route("advisor.chats.update", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: activeChat.id,
                }),
                { title: titleValue.trim() },
            );
            if (data.success) {
                setChats((prev) =>
                    prev.map((c) => (c.id === activeChat.id ? data.chat : c)),
                );
                setActiveChat(data.chat);
            }
        } catch (error) {
            console.error("Error updating chat:", error);
        } finally {
            onSavingChange?.(false);
        }
    };

    const saveSettings = async () => {
        if (!activeChat) return;
        setShowSettings(false);
        onSavingChange?.(true);
        try {
            const { data } = await http.put(
                route("advisor.chats.update", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: activeChat.id,
                }),
                {
                    model: selectedModel,
                    system_instructions: systemInstructions,
                },
            );
            if (data.success) {
                setChats((prev) =>
                    prev.map((c) => (c.id === activeChat.id ? data.chat : c)),
                );
                setActiveChat(data.chat);
            }

            // Also persist default settings to project settings
            onSettingChange?.("advisorModel", selectedModel);
            onSettingChange?.("advisorSystemInstructions", systemInstructions);
            onSettingChange?.("advisorThinkingBudget", thinkingBudget);
            onSettingChange?.("advisorOutputLength", outputLength);
            onSettingChange?.("advisorTemperature", temperature);
        } catch (error) {
            console.error("Error saving settings:", error);
        } finally {
            onSavingChange?.(false);
        }
    };

    const deleteChat = async (chatId: string) => {
        onSavingChange?.(true);
        try {
            const { data } = await http.delete(
                route("advisor.chats.delete", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: chatId,
                }),
            );
            if (data.success) {
                const remaining = chats.filter((c) => c.id !== chatId);
                setChats(remaining);
                if (activeChat?.id === chatId) {
                    setActiveChat(remaining.length > 0 ? remaining[0] : null);
                }
            }
        } catch (error) {
            console.error("Error deleting chat:", error);
        } finally {
            onSavingChange?.(false);
        }
        setDeleteConfirmChat(null);
    };

    const clearChat = async () => {
        if (!activeChat) return;
        setShowActions(false);
        onSavingChange?.(true);

        try {
            const { data } = await http.delete(
                route("advisor.messages.clear", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: activeChat.id,
                }),
            );
            if (data.success) {
                setMessages([]);
            } else {
                console.error("Error clearing chat:", data.error);
            }
        } catch (error) {
            console.error("Error clearing chat:", error);
        } finally {
            onSavingChange?.(false);
        }
    };

    const sendMessage = async (
        messageText?: string,
        isRetry = false,
        messagesOverride?: AdvisorMessage[],
    ) => {
        const textToSend = messageText || inputMessage.trim();
        if (!textToSend || isStreaming || !activeChat) return;

        const chatId = activeChat.id;

        if (!isRetry) {
            setInputMessage("");
        }
        setIsStreaming(true);
        setStreamingContent("");

        // Determine the base messages to work with
        let baseMessages: AdvisorMessage[];

        if (isRetry && messagesOverride) {
            // Retry with override: use the provided messages (includes user message)
            // Remove any trailing assistant messages after the last user message
            baseMessages = [...messagesOverride];
            while (
                baseMessages.length > 0 &&
                baseMessages[baseMessages.length - 1].role === "assistant"
            ) {
                baseMessages.pop();
            }
        } else if (isRetry) {
            // Regenerate last response: keep all messages except the last assistant
            baseMessages = [...messages];
            if (
                baseMessages.length > 0 &&
                baseMessages[baseMessages.length - 1].role === "assistant"
            ) {
                baseMessages.pop();
            }
        } else {
            // New message: add pending user message
            const pendingUserMsg: AdvisorMessage = {
                id: `pending-user-${Date.now()}`,
                role: "user",
                content: textToSend,
                created_at: new Date().toISOString(),
            };
            // Use messagesOverride if provided (e.g., for edit operations), otherwise use current messages
            const baseForNewMsg = messagesOverride ?? messages;
            baseMessages = [...baseForNewMsg, pendingUserMsg];
        }

        // Update UI with the base messages (without the streaming response yet)
        setMessages(baseMessages);
        streamSessionRef.current = {
            chatId,
            sessionId: "",
            fullContent: "",
        };

        try {
            const { data } = await http.post(
                route("advisor.messages.send", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: chatId,
                }),
                {
                    message: textToSend,
                    include_story_context: true,
                    is_retry: isRetry,
                    model: selectedModel,
                    thinking_budget: isThinkingModel ? thinkingBudget : 0,
                    max_output_tokens: outputLength,
                    temperature,
                },
            );

            if (streamSessionRef.current) {
                streamSessionRef.current.sessionId = data.session_id;
            }

            if (data.user_message_id) {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id.startsWith("pending-user-")
                            ? { ...msg, id: data.user_message_id }
                            : msg,
                    ),
                );
            }
        } catch (error) {
            const normalizedError = normalizeHttpError(error);
            console.error("Error:", normalizedError);
            streamSessionRef.current = null;
            setIsStreaming(false);
            setStreamingContent("");

            const errorMsg: AdvisorMessage = {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: `❌ Error: ${normalizedError.message}. Please try again.`,
                created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMsg]);
        }
    };

    const retryLastMessage = async () => {
        if (!activeChat) return;

        // For regenerate: find the last user message and resend it
        const lastUserIdx = messages
            .map((m, i) => ({ m, i }))
            .filter(({ m }) => m.role === "user")
            .pop()?.i;

        if (lastUserIdx !== undefined) {
            const lastUserMsg = messages[lastUserIdx];
            // Get messages after the user message (AI responses to delete)
            const messagesToDelete = messages.slice(lastUserIdx + 1);

            // Delete old AI responses from database
            for (const msg of messagesToDelete) {
                if (
                    !msg.id.startsWith("pending-") &&
                    !msg.id.startsWith("user-") &&
                    !msg.id.startsWith("assistant-") &&
                    !msg.id.startsWith("error-")
                ) {
                    try {
                        await http.delete(
                            route("advisor.messages.delete", {
                                workspace_id: workspaceId,
                                project_id: projectId,
                                chat_id: activeChat.id,
                                message_id: msg.id,
                            }),
                        );
                    } catch (error) {
                        console.error("Error deleting message:", error);
                    }
                }
            }

            // Pass messages up to and including the user message
            const messagesUpToUser = messages.slice(0, lastUserIdx + 1);
            sendMessage(lastUserMsg.content, true, messagesUpToUser);
        }
    };

    // Retry a specific user message (removes all messages after it and resends)
    const retryMessage = async (index: number) => {
        if (!activeChat) return;

        const messageToRetry = messages[index];
        if (messageToRetry && messageToRetry.role === "user") {
            // Get messages after this one to delete
            const messagesToDelete = messages.slice(index + 1);

            // Delete messages from database
            for (const msg of messagesToDelete) {
                if (
                    !msg.id.startsWith("pending-") &&
                    !msg.id.startsWith("user-") &&
                    !msg.id.startsWith("assistant-") &&
                    !msg.id.startsWith("error-")
                ) {
                    try {
                        await http.delete(
                            route("advisor.messages.delete", {
                                workspace_id: workspaceId,
                                project_id: projectId,
                                chat_id: activeChat.id,
                                message_id: msg.id,
                            }),
                        );
                    } catch (error) {
                        console.error("Error deleting message:", error);
                    }
                }
            }

            // Get messages up to and including this user message
            const messagesUpToUser = messages.slice(0, index + 1);
            // Call sendMessage with the message override - keeps the user message, gets fresh response
            sendMessage(messageToRetry.content, true, messagesUpToUser);
        }
    };

    // Start editing a message
    const startEditingMessage = (index: number, content: string) => {
        setEditingMessageIndex(index);
        setEditingMessageContent(content);
    };

    // Submit edited message - replaces the message and its AI response only
    const submitEditedMessage = async () => {
        if (
            editingMessageIndex === null ||
            !editingMessageContent.trim() ||
            !activeChat
        )
            return;

        const editedMessage = messages[editingMessageIndex];
        const editedContent = editingMessageContent.trim();

        // Clear editing state first
        setEditingMessageIndex(null);
        setEditingMessageContent("");

        // Find the AI response directly after this message (if any)
        const nextMessage = messages[editingMessageIndex + 1];
        const hasAIResponse = nextMessage && nextMessage.role === "assistant";

        // Messages before the edited one (these stay as-is)
        const messagesBefore = messages.slice(0, editingMessageIndex);

        // Messages after the edit pair (skip edited msg + its AI response if exists)
        const skipCount = hasAIResponse ? 2 : 1;
        const messagesAfter = messages.slice(editingMessageIndex + skipCount);

        // Store messages to append after AI response completes
        pendingAfterMessagesRef.current = messagesAfter;

        // Delete the old user message from database
        const isRealMessage = (id: string) =>
            !id.startsWith("pending-") &&
            !id.startsWith("user-") &&
            !id.startsWith("assistant-") &&
            !id.startsWith("error-");

        if (isRealMessage(editedMessage.id)) {
            try {
                await http.delete(
                    route("advisor.messages.delete", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                        chat_id: activeChat.id,
                        message_id: editedMessage.id,
                    }),
                );
            } catch (error) {
                console.error("Error deleting old message:", error);
            }
        }

        // Delete the AI response to this message (if any)
        if (hasAIResponse && isRealMessage(nextMessage.id)) {
            try {
                await http.delete(
                    route("advisor.messages.delete", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                        chat_id: activeChat.id,
                        message_id: nextMessage.id,
                    }),
                );
            } catch (error) {
                console.error("Error deleting AI response:", error);
            }
        }

        // Send the edited content as a new message, using messagesBefore as the base
        // This ensures the edited message appears in the correct position, not at the bottom
        sendMessage(editedContent, false, messagesBefore);
    };

    // Cancel editing
    const cancelEditingMessage = () => {
        setEditingMessageIndex(null);
        setEditingMessageContent("");
    };

    const cancelStreaming = async () => {
        if (!activeChat || !streamSessionRef.current) {
            return;
        }

        try {
            await http.post(
                route("advisor.messages.cancel", {
                    workspace_id: workspaceId,
                    project_id: projectId,
                    chat_id: activeChat.id,
                }),
                {
                    session_id: streamSessionRef.current.sessionId,
                },
            );
        } catch (error) {
            console.error("Error cancelling advisor stream:", error);
        }

        streamSessionRef.current = null;
        setIsStreaming(false);
        setStreamingContent("");
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const deleteMessage = async (index: number) => {
        if (!activeChat) return;

        const messageToDelete = messages[index];

        // Optimistically remove from UI
        setMessages((prev) => prev.filter((_, i) => i !== index));

        // If it's a real message (not a temp one), delete from backend
        if (
            messageToDelete &&
            !messageToDelete.id.startsWith("temp-") &&
            !messageToDelete.id.startsWith("user-") &&
            !messageToDelete.id.startsWith("assistant-") &&
            !messageToDelete.id.startsWith("error-")
        ) {
            try {
                await http.delete(
                    route("advisor.messages.delete", {
                        workspace_id: workspaceId,
                        project_id: projectId,
                        chat_id: activeChat.id,
                        message_id: messageToDelete.id,
                    }),
                );
            } catch (error) {
                console.error("Error deleting message:", error);
            }
        }
    };

    const parseEditSuggestions = (content: string) => {
        const editRegex = /<<<EDIT>>>([\s\S]*?)<<<END_EDIT>>>/g;
        const matches = [...content.matchAll(editRegex)];
        return matches.map((match) => {
            const editContent = match[1];
            const oldMatch = editContent.match(/OLD:\s*([\s\S]*?)(?=NEW:|$)/);
            const newMatch = editContent.match(
                /NEW:\s*([\s\S]*?)(?=REASON:|$)/,
            );
            const reasonMatch = editContent.match(/REASON:\s*([\s\S]*?)$/);
            const chapterMatch = editContent.match(/CHAPTER:\s*(.*?)(?=\n|$)/);

            return {
                chapter: chapterMatch?.[1]?.trim() || "",
                oldText: oldMatch?.[1]?.trim() || "",
                newText: newMatch?.[1]?.trim() || "",
                reason: reasonMatch?.[1]?.trim() || "",
            };
        });
    };

    // Send edits to the editor for inline preview (Agent mode)
    const sendEditsToEditor = (
        edits: typeof parseEditSuggestions extends (c: string) => infer R
            ? R
            : never,
        clearExisting: boolean = false,
    ) => {
        if (edits.length === 0) return;

        // Clear existing pending edits if requested (when getting fresh suggestions)
        if (clearExisting) {
            clearAllEdits();
        }

        const pendingEditData = edits.map((edit) => ({
            chapter: edit.chapter,
            oldText: edit.oldText,
            newText: edit.newText,
            reason: edit.reason,
        }));

        addPendingEdits(pendingEditData);
    };

    const renderMessageContent = (
        content: string,
        isLatestAssistant: boolean = false,
    ) => {
        const editSuggestions = parseEditSuggestions(content);

        if (editSuggestions.length > 0) {
            const parts = content.split(/<<<EDIT>>>[\s\S]*?<<<END_EDIT>>>/);

            // In Agent mode and this is the latest response, auto-send edits to editor
            if (
                advisorMode === "agent" &&
                isLatestAssistant &&
                editSuggestions.length > 0
            ) {
                // Use a ref to track if we've already sent these edits
                const editKey = editSuggestions
                    .map((e) => e.oldText.substring(0, 50))
                    .join("|");
                if (!sentEditsRef.current.has(editKey)) {
                    sentEditsRef.current.add(editKey);
                    // Append to existing edits (don't clear - user might have edits from previous messages)
                    setTimeout(
                        () => sendEditsToEditor(editSuggestions, false),
                        100,
                    );
                }
            }

            return (
                <div className="space-y-3">
                    {parts.map((part, idx) => (
                        <div key={idx}>
                            {part.trim() && (
                                <p className="whitespace-pre-wrap">
                                    {part.trim()}
                                </p>
                            )}
                            {editSuggestions[idx] && (
                                <div className="my-3 rounded-lg border border-purple-200 bg-purple-50 p-3">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Sparkles className="h-4 w-4 text-purple-600" />
                                        <span className="text-sm font-medium text-purple-700">
                                            Suggested Edit{" "}
                                            {editSuggestions[idx].chapter &&
                                                `- ${editSuggestions[idx].chapter}`}
                                        </span>
                                    </div>
                                    <div className="space-y-2">
                                        <div className="rounded bg-red-100 p-2 text-sm">
                                            <span className="text-red-600 font-medium">
                                                Remove:
                                            </span>
                                            <p className="text-red-800 line-through mt-1">
                                                {editSuggestions[idx].oldText}
                                            </p>
                                        </div>
                                        <div className="rounded bg-green-100 p-2 text-sm">
                                            <span className="text-green-600 font-medium">
                                                Add:
                                            </span>
                                            <p className="text-green-800 mt-1">
                                                {editSuggestions[idx].newText}
                                            </p>
                                        </div>
                                    </div>
                                    {editSuggestions[idx].reason && (
                                        <p className="text-xs text-gray-600 mt-2 italic">
                                            💡 {editSuggestions[idx].reason}
                                        </p>
                                    )}
                                    {/* Show different UI based on mode */}
                                    {advisorMode === "chat" ? (
                                        <div className="flex gap-2 mt-3">
                                            <Button
                                                size="sm"
                                                className="bg-green-600 hover:bg-green-700"
                                                onClick={async () => {
                                                    if (onApplyEdit) {
                                                        const success =
                                                            await onApplyEdit(
                                                                editSuggestions[
                                                                    idx
                                                                ].oldText,
                                                                editSuggestions[
                                                                    idx
                                                                ].newText,
                                                            );
                                                        if (success) {
                                                            toast.success(
                                                                "Edit applied!",
                                                            );
                                                        } else {
                                                            toast.info(
                                                                "Could not find text to replace. The text may have changed.",
                                                            );
                                                        }
                                                    }
                                                }}
                                            >
                                                <Check className="h-3 w-3 mr-1" />{" "}
                                                Apply
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() =>
                                                    copyToClipboard(
                                                        editSuggestions[idx]
                                                            .newText,
                                                    )
                                                }
                                            >
                                                <Copy className="h-3 w-3 mr-1" />{" "}
                                                Copy
                                            </Button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 mt-3 text-xs text-purple-600">
                                            <Wand2 className="h-3 w-3" />
                                            <span>
                                                Edit queued for inline preview
                                                in editor
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            );
        }

        return <p className="whitespace-pre-wrap">{content}</p>;
    };

    return (
        <div className="flex flex-col h-full bg-white">
            {/* Mode Toggle - Agent vs Chat */}
            <div className="p-2 border-b bg-linear-to-r from-purple-50 to-blue-50">
                <div className="grid grid-cols-2 gap-1 p-1 bg-white rounded-lg border shadow-sm">
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button
                                onClick={() => setAdvisorMode("chat")}
                                className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                                    advisorMode === "chat"
                                        ? "bg-blue-600 text-white shadow-sm"
                                        : "text-gray-600 hover:bg-gray-100"
                                }`}
                            >
                                <MessageCircle className="h-3.5 w-3.5" />
                                Chat
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom">
                            <p className="text-xs">
                                Chat mode: Apply edits manually from sidebar
                            </p>
                        </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button
                                onClick={() => setAdvisorMode("agent")}
                                className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                                    advisorMode === "agent"
                                        ? "bg-purple-600 text-white shadow-sm"
                                        : "text-gray-600 hover:bg-gray-100"
                                }`}
                            >
                                <Wand2 className="h-3.5 w-3.5" />
                                Agent
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom">
                            <p className="text-xs">
                                Agent mode: Preview edits inline in editor with
                                ✓/✗
                            </p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                {/* Pending edits indicator for Agent mode */}
                {advisorMode === "agent" && pendingEdits.length > 0 && (
                    <div className="flex items-center justify-between mt-2 px-1">
                        <span className="text-xs text-purple-600">
                            {
                                pendingEdits.filter(
                                    (e) => e.status === "pending",
                                ).length
                            }{" "}
                            pending
                            {pendingEdits.filter((e) => e.status === "stale")
                                .length > 0 && (
                                <span className="text-gray-400 ml-1">
                                    (
                                    {
                                        pendingEdits.filter(
                                            (e) => e.status === "stale",
                                        ).length
                                    }{" "}
                                    stale)
                                </span>
                            )}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs text-gray-500 hover:text-red-600"
                            onClick={clearAllEdits}
                        >
                            Clear all
                        </Button>
                    </div>
                )}
            </div>

            {/* Title Block - Always visible */}
            <div className="p-3 border-b">
                {editingTitle ? (
                    <div className="flex items-center gap-2">
                        <Input
                            value={titleValue}
                            onChange={(e) => setTitleValue(e.target.value)}
                            className="flex-1 h-8 font-medium"
                            autoFocus
                            onKeyDown={(e) => {
                                if (e.key === "Enter") updateChatTitle();
                                if (e.key === "Escape") {
                                    setEditingTitle(false);
                                    setTitleValue(activeChat?.title || "");
                                }
                            }}
                            onBlur={updateChatTitle}
                        />
                    </div>
                ) : (
                    <div
                        className="font-medium text-gray-800 cursor-pointer hover:text-blue-600 truncate"
                        onClick={() => activeChat && setEditingTitle(true)}
                        title="Click to edit title"
                    >
                        {activeChat?.title || "No chat selected"}
                    </div>
                )}
            </div>

            {/* Controls Row */}
            <div className="p-2 border-b bg-gray-50 flex items-center gap-2">
                {/* Chat List Dropdown */}
                <div className="relative flex-1" ref={chatListRef}>
                    <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between"
                        onClick={() => setShowChatList(!showChatList)}
                        disabled={isLoadingChats}
                    >
                        <div className="flex items-center gap-2 truncate">
                            <MessageSquare className="h-4 w-4" />
                            <span className="truncate">
                                {chats.length} chats
                            </span>
                        </div>
                        <ChevronDown
                            className={`h-4 w-4 transition-transform ${
                                showChatList ? "rotate-180" : ""
                            }`}
                        />
                    </Button>

                    {showChatList && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-md shadow-lg z-50 max-h-64 overflow-y-auto">
                            <div
                                className="px-3 py-2 hover:bg-blue-50 cursor-pointer flex items-center gap-2 text-blue-600 border-b"
                                onClick={createNewChat}
                            >
                                <Plus className="h-4 w-4" />
                                <span className="text-sm font-medium">
                                    New Chat
                                </span>
                            </div>
                            {chats.length === 0 ? (
                                <div className="px-3 py-4 text-sm text-gray-500 text-center">
                                    No chats yet
                                </div>
                            ) : (
                                chats.map((chat) => (
                                    <div
                                        key={chat.id}
                                        className={`px-3 py-2 hover:bg-gray-50 cursor-pointer flex items-center justify-between group ${
                                            activeChat?.id === chat.id
                                                ? "bg-blue-50"
                                                : ""
                                        }`}
                                        onClick={() => {
                                            setActiveChat(chat);
                                            setShowChatList(false);
                                        }}
                                    >
                                        <div className="flex items-center gap-2 min-w-0 flex-1">
                                            <MessageSquare className="h-4 w-4 text-gray-400 shrink-0" />
                                            <span className="text-sm truncate">
                                                {chat.title}
                                            </span>
                                        </div>
                                        <button
                                            className="p-1 hover:bg-red-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setDeleteConfirmChat(chat);
                                            }}
                                        >
                                            <Trash2 className="h-3 w-3 text-red-500" />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>

                {/* Settings Button */}
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowSettings(!showSettings)}
                        >
                            <Settings2 className="h-4 w-4" />
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent>Settings</TooltipContent>
                </Tooltip>

                {/* Actions Menu */}
                <div className="relative" ref={actionsRef}>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowActions(!showActions)}
                    >
                        <MoreHorizontal className="h-4 w-4" />
                    </Button>

                    {showActions && (
                        <div className="absolute top-full right-0 mt-1 bg-white border rounded-md shadow-lg z-50 min-w-[140px]">
                            <div
                                className="px-3 py-2 hover:bg-gray-50 cursor-pointer flex items-center gap-2 text-sm"
                                onClick={createNewChat}
                            >
                                <Plus className="h-4 w-4" />
                                New Chat
                            </div>
                            <div
                                className="px-3 py-2 hover:bg-gray-50 cursor-pointer flex items-center gap-2 text-sm"
                                onClick={clearChat}
                            >
                                <Eraser className="h-4 w-4" />
                                Clear Chat
                            </div>
                            {activeChat && (
                                <div
                                    className="px-3 py-2 hover:bg-red-50 cursor-pointer flex items-center gap-2 text-sm text-red-600 border-t"
                                    onClick={() => {
                                        setShowActions(false);
                                        setDeleteConfirmChat(activeChat);
                                    }}
                                >
                                    <Trash2 className="h-4 w-4" />
                                    Delete Chat
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Settings Panel */}
            {showSettings && (
                <div className="p-3 border-b bg-gray-50 space-y-4">
                    {/* Model Selection */}
                    <div className="space-y-1">
                        <Label className="text-xs font-medium">AI Model</Label>
                        <Select
                            value={selectedModel}
                            onValueChange={setSelectedModel}
                        >
                            <SelectTrigger className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {AVAILABLE_MODELS.map((model) => (
                                    <SelectItem
                                        key={model.value}
                                        value={model.value}
                                    >
                                        {model.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Thinking Budget - Greyed out for non-thinking models */}
                    <div
                        className={`space-y-1 ${
                            !isThinkingModel ? "opacity-50" : ""
                        }`}
                    >
                        <div className="flex justify-between">
                            <Label className="text-xs font-medium">
                                Thinking Budget
                            </Label>
                            <span className="text-xs text-gray-500">
                                {isThinkingModel
                                    ? `${thinkingBudget} tokens`
                                    : "N/A"}
                            </span>
                        </div>
                        <Slider
                            value={[thinkingBudget]}
                            onValueChange={([v]) => setThinkingBudget(v)}
                            min={
                                advisorModelConfig?.params.thinkingBudget
                                    ?.min ?? 0
                            }
                            max={
                                advisorModelConfig?.params.thinkingBudget
                                    ?.max ?? 24576
                            }
                            step={
                                advisorModelConfig?.params.thinkingBudget
                                    ?.step ?? 256
                            }
                            className="w-full"
                            disabled={!isThinkingModel}
                        />
                        {!isThinkingModel && (
                            <p className="text-xs text-gray-400">
                                Only available for thinking models
                            </p>
                        )}
                    </div>

                    {/* Output Length */}
                    <div className="space-y-1">
                        <div className="flex justify-between">
                            <Label className="text-xs font-medium">
                                Max Output
                            </Label>
                            <span className="text-xs text-gray-500">
                                {outputLength} tokens
                            </span>
                        </div>
                        <Slider
                            value={[outputLength]}
                            onValueChange={([v]) => setOutputLength(v)}
                            min={
                                advisorModelConfig?.params.outputLength?.min ??
                                50
                            }
                            max={
                                advisorModelConfig?.params.outputLength?.max ??
                                8192
                            }
                            step={
                                advisorModelConfig?.params.outputLength?.step ??
                                10
                            }
                            className="w-full"
                        />
                    </div>

                    {/* Temperature */}
                    <div className="space-y-1">
                        <div className="flex justify-between">
                            <Label className="text-xs font-medium">
                                Temperature
                            </Label>
                            <span className="text-xs text-gray-500">
                                {temperature}
                            </span>
                        </div>
                        <Slider
                            value={[temperature]}
                            onValueChange={([v]) => setTemperature(v)}
                            min={
                                advisorModelConfig?.params.temperature?.min ?? 0
                            }
                            max={
                                advisorModelConfig?.params.temperature?.max ?? 2
                            }
                            step={
                                advisorModelConfig?.params.temperature?.step ??
                                0.01
                            }
                            className="w-full"
                        />
                    </div>

                    {/* System Instructions */}
                    <div className="space-y-1">
                        <div className="flex items-center gap-1">
                            <Label className="text-xs font-medium">
                                System Instructions
                            </Label>
                            <Tooltip>
                                <TooltipTrigger>
                                    <HelpCircle className="h-3 w-3 text-gray-400" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                    Customize the AI's behavior and personality.
                                </TooltipContent>
                            </Tooltip>
                        </div>
                        <Textarea
                            value={systemInstructions}
                            onChange={(e) =>
                                setSystemInstructions(e.target.value)
                            }
                            className="text-xs min-h-20 max-h-[150px]"
                        />
                    </div>

                    <div className="flex justify-end gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowSettings(false)}
                        >
                            Cancel
                        </Button>
                        <Button size="sm" onClick={saveSettings}>
                            Save
                        </Button>
                    </div>
                </div>
            )}

            {/* Messages Area */}
            <ScrollArea className="flex-1">
                <div className="p-3">
                    {isLoadingMessages ? (
                        <div className="flex items-center justify-center h-32">
                            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                        </div>
                    ) : !activeChat ? (
                        <div className="flex flex-col items-center justify-center h-48 text-center">
                            <Bot className="h-12 w-12 text-gray-300 mb-3" />
                            <p className="text-sm text-gray-500 mb-3">
                                Create a new chat to start
                            </p>
                            <Button size="sm" onClick={createNewChat}>
                                <Plus className="h-4 w-4 mr-1" /> New Chat
                            </Button>
                        </div>
                    ) : messages.length === 0 && !streamingContent ? (
                        <div className="flex flex-col items-center justify-center h-48 text-center">
                            <Sparkles className="h-12 w-12 text-purple-300 mb-3" />
                            <p className="text-sm text-gray-600">
                                Ask anything about your story
                            </p>
                            <p className="text-xs text-gray-400 mt-1">
                                The AI has full context
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {messages.map((message, idx) => (
                                <div
                                    key={message.id}
                                    className={`flex gap-2 group ${
                                        message.role === "user"
                                            ? "justify-end"
                                            : "justify-start"
                                    }`}
                                >
                                    {message.role === "assistant" && (
                                        <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0 mt-1">
                                            <Bot className="h-4 w-4 text-purple-600" />
                                        </div>
                                    )}
                                    <div className="flex flex-col max-w-[85%]">
                                        {/* Show edit UI if editing this message */}
                                        {editingMessageIndex === idx ? (
                                            <div className="space-y-2">
                                                <Textarea
                                                    value={
                                                        editingMessageContent
                                                    }
                                                    onChange={(e) =>
                                                        setEditingMessageContent(
                                                            e.target.value,
                                                        )
                                                    }
                                                    className="min-h-20 text-sm"
                                                    autoFocus
                                                />
                                                <div className="flex gap-2">
                                                    <Button
                                                        size="sm"
                                                        onClick={
                                                            submitEditedMessage
                                                        }
                                                    >
                                                        <Send className="h-3 w-3 mr-1" />{" "}
                                                        Send
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={
                                                            cancelEditingMessage
                                                        }
                                                    >
                                                        Cancel
                                                    </Button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div
                                                className={`rounded-lg p-3 ${
                                                    message.role === "user"
                                                        ? "bg-blue-600 text-white"
                                                        : "bg-gray-100 text-gray-900"
                                                }`}
                                            >
                                                <div className="text-sm">
                                                    {message.role ===
                                                    "assistant" ? (
                                                        renderMessageContent(
                                                            message.content,
                                                            idx ===
                                                                messages.length -
                                                                    1,
                                                        )
                                                    ) : (
                                                        <p className="whitespace-pre-wrap">
                                                            {message.content}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Message Actions - Always visible */}
                                        <div
                                            className={`flex gap-1 mt-1 ${
                                                message.role === "user"
                                                    ? "justify-end"
                                                    : "justify-start"
                                            }`}
                                        >
                                            {message.role === "assistant" && (
                                                <>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <button
                                                                className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
                                                                onClick={() =>
                                                                    copyToClipboard(
                                                                        message.content,
                                                                    )
                                                                }
                                                            >
                                                                <Copy className="h-3 w-3" />
                                                            </button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Copy
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    {idx ===
                                                        messages.length - 1 &&
                                                        !isStreaming && (
                                                            <Tooltip>
                                                                <TooltipTrigger
                                                                    asChild
                                                                >
                                                                    <button
                                                                        className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
                                                                        onClick={
                                                                            retryLastMessage
                                                                        }
                                                                    >
                                                                        <RefreshCw className="h-3 w-3" />
                                                                    </button>
                                                                </TooltipTrigger>
                                                                <TooltipContent>
                                                                    Regenerate
                                                                </TooltipContent>
                                                            </Tooltip>
                                                        )}
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <button
                                                                className="p-1 rounded hover:bg-red-100 text-gray-400 hover:text-red-500"
                                                                onClick={() =>
                                                                    deleteMessage(
                                                                        idx,
                                                                    )
                                                                }
                                                            >
                                                                <Trash2 className="h-3 w-3" />
                                                            </button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Delete
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </>
                                            )}
                                            {message.role === "user" && (
                                                <>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <button
                                                                className="p-1 rounded hover:bg-blue-200 text-gray-400 hover:text-blue-600"
                                                                onClick={() =>
                                                                    startEditingMessage(
                                                                        idx,
                                                                        message.content,
                                                                    )
                                                                }
                                                            >
                                                                <Edit3 className="h-3 w-3" />
                                                            </button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Edit & Resend
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <button
                                                                className="p-1 rounded hover:bg-blue-200 text-gray-400 hover:text-blue-600"
                                                                onClick={() =>
                                                                    retryMessage(
                                                                        idx,
                                                                    )
                                                                }
                                                                disabled={
                                                                    isStreaming
                                                                }
                                                            >
                                                                <RefreshCw className="h-3 w-3" />
                                                            </button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Retry
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <button
                                                                className="p-1 rounded hover:bg-red-100 text-gray-400 hover:text-red-500"
                                                                onClick={() =>
                                                                    deleteMessage(
                                                                        idx,
                                                                    )
                                                                }
                                                            >
                                                                <Trash2 className="h-3 w-3" />
                                                            </button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            Delete
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                    {message.role === "user" && (
                                        <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1">
                                            <User className="h-4 w-4 text-blue-600" />
                                        </div>
                                    )}
                                </div>
                            ))}

                            {/* Streaming */}
                            {streamingContent && (
                                <div className="flex gap-2 justify-start">
                                    <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0 mt-1">
                                        <Bot className="h-4 w-4 text-purple-600" />
                                    </div>
                                    <div className="rounded-lg p-3 max-w-[85%] bg-gray-100">
                                        <div className="text-sm">
                                            {renderMessageContent(
                                                streamingContent,
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {isStreaming && !streamingContent && (
                                <div className="flex gap-2 justify-start">
                                    <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                                        <Bot className="h-4 w-4 text-purple-600" />
                                    </div>
                                    <div className="rounded-lg p-3 bg-gray-100">
                                        <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="p-3 border-t">
                <div className="flex gap-2">
                    <Textarea
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage();
                            }
                        }}
                        placeholder={
                            activeChat
                                ? "Ask about your story..."
                                : "Create a chat first"
                        }
                        className="max-h-full grow resize-none text-sm"
                        disabled={!activeChat || isStreaming}
                    />
                    <div className="flex flex-col gap-2">
                        {!isStreaming && (
                            <MagicWandButton
                                text={inputMessage}
                                onEnhanced={(enhanced) =>
                                    setInputMessage(enhanced)
                                }
                                enhancementMode="chat_message"
                                workspaceId={workspaceId}
                                projectId={projectId}
                                aiModel={selectedModel}
                                disabled={isStreaming || !inputMessage.trim()}
                                size="icon"
                                variant="outline"
                                className="h-[40px] w-10 border-green-600 bg-green-600 hover:bg-green-500 text-white"
                            />
                        )}
                        {isStreaming ? (
                            <Button
                                variant="destructive"
                                size="icon"
                                onClick={cancelStreaming}
                                className="h-16 w-10"
                            >
                                <X className="h-2.5 w-2.5" />
                            </Button>
                        ) : (
                            <Button
                                onClick={() => sendMessage()}
                                disabled={!activeChat || !inputMessage.trim()}
                                className="h-[40px] w-10"
                            >
                                <Send className="h-2.5 w-2.5" />
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            {/* Delete Confirmation */}
            <Dialog
                open={!!deleteConfirmChat}
                onOpenChange={() => setDeleteConfirmChat(null)}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Chat</DialogTitle>
                        <DialogDescription>
                            Delete "{deleteConfirmChat?.title}"? This cannot be
                            undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeleteConfirmChat(null)}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={() =>
                                deleteConfirmChat &&
                                deleteChat(deleteConfirmChat.id)
                            }
                        >
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
