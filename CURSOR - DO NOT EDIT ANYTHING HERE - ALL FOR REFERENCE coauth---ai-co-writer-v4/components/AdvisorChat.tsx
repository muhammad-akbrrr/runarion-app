
import React, { useState, useEffect, useRef } from 'react';
import { AdvisorMessage, AdvisorMode, DEFAULT_ADVISOR_MODES, BibleItem, StyleProfile, ModelType } from '../types';
import { chatWithAdvisor } from '../services/geminiService';
import { Send, User, Bot, Sparkles, Check, X, Settings, Trash2, Plus, MessageSquareText, Eye, EyeOff } from 'lucide-react';
import { Button } from './Button';
import { findBestMatch } from '../utils';

interface AdvisorChatProps {
    storyContext: string;
    bibleItems: BibleItem[];
    activeStyle: StyleProfile | null;
    onUpdateContent: (text: string) => void;
    history: AdvisorMessage[];
    setHistory: React.Dispatch<React.SetStateAction<AdvisorMessage[]>>;
}

export const AdvisorChat: React.FC<AdvisorChatProps> = ({
    storyContext,
    bibleItems,
    activeStyle,
    onUpdateContent,
    history,
    setHistory
}) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [activeModeId, setActiveModeId] = useState<string>('critic');
    const [selectedModel, setSelectedModel] = useState<ModelType>(ModelType.GEMINI_3_PRO);
    const [customModeInstruction, setCustomModeInstruction] = useState('');
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [history, isLoading]);

    const activeMode = DEFAULT_ADVISOR_MODES.find(m => m.id === activeModeId) || DEFAULT_ADVISOR_MODES[0];
    const wordCount = storyContext.trim().length > 0 ? storyContext.trim().split(/\s+/).length : 0;

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg: AdvisorMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: input
        };

        setHistory(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            const systemInstruction = activeMode.id === 'custom' ? customModeInstruction : activeMode.systemInstruction;
            
            const response = await chatWithAdvisor(
                [...history, userMsg], // Full history context
                input,
                storyContext,
                bibleItems,
                activeStyle,
                systemInstruction,
                selectedModel
            );

            setHistory(prev => [...prev, response]);
        } catch (e: any) {
            let errorMsg = "Advisor failed to respond.";
            if (e.message?.includes('404')) errorMsg = "Model Not Found. Please select a different model.";
            else if (e.message?.includes('429')) errorMsg = "Rate Limit Exceeded. Try again later.";
            
            setHistory(prev => [...prev, {
                id: Date.now().toString(),
                role: 'model',
                content: `⚠️ **Error:** ${errorMsg}`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleApplySuggestion = (suggestion: any) => {
        const match = findBestMatch(storyContext, suggestion.original);
        
        if (!match) {
            alert("Could not find text match to replace. The text may have changed or the AI quoted it incorrectly.");
            return;
        }
        
        // Replace the found range
        const newContent = storyContext.substring(0, match.start) + suggestion.replacement + storyContext.substring(match.end);
        
        onUpdateContent(newContent);
    };

    return (
        <div className="flex flex-col h-full bg-gray-900 border-l border-gray-800">
            {/* Header / Settings */}
            <div className="p-3 border-b border-gray-800 bg-gray-955/50 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2"><MessageSquareText className="w-4 h-4 text-purple-400"/> Advisor</h3>
                    <div className="flex items-center gap-2">
                        <div className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full ${wordCount > 0 ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`} title={wordCount > 0 ? `Advisor reading ${wordCount} words` : "No context detected"}>
                            {wordCount > 0 ? <Eye className="w-3 h-3"/> : <EyeOff className="w-3 h-3"/>}
                            <span>{wordCount > 0 ? 'Context Active' : 'No Context'}</span>
                        </div>
                        <button onClick={() => setHistory([])} className="text-gray-500 hover:text-red-400 p-1"><Trash2 className="w-4 h-4"/></button>
                    </div>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                    <select 
                        value={activeModeId} 
                        onChange={(e) => setActiveModeId(e.target.value)}
                        className="bg-gray-800 text-xs text-white border border-gray-700 rounded p-1.5 focus:border-purple-500 outline-none"
                    >
                        {DEFAULT_ADVISOR_MODES.map(m => (
                            <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                    </select>
                    
                    <select 
                        value={selectedModel} 
                        onChange={(e) => setSelectedModel(e.target.value as ModelType)}
                        className="bg-gray-800 text-xs text-white border border-gray-700 rounded p-1.5 focus:border-blue-500 outline-none"
                    >
                        <option value={ModelType.GEMINI_3_PRO}>Gemini 3.0 Pro</option>
                        <option value={ModelType.GEMINI_2_5_PRO}>Gemini 2.5 Pro</option>
                        <option value={ModelType.GEMINI_2_5_FLASH}>Gemini 2.5 Flash</option>
                    </select>
                </div>

                {activeModeId === 'custom' && (
                    <textarea 
                        value={customModeInstruction}
                        onChange={(e) => setCustomModeInstruction(e.target.value)}
                        placeholder="Enter custom persona instructions..."
                        className="w-full h-16 bg-black/20 border border-gray-700 rounded p-2 text-xs text-gray-300 resize-none"
                    />
                )}
                
                <p className="text-[10px] text-gray-500 italic">{activeMode.description}</p>
            </div>

            {/* Chat History */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
                {history.length === 0 && (
                    <div className="text-center text-gray-600 text-xs mt-10">
                        Start chatting with your advisor.<br/>I know your whole story.
                    </div>
                )}
                
                {history.map((msg) => (
                    <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className={`max-w-[90%] rounded-lg p-3 text-sm ${msg.role === 'user' ? 'bg-purple-900/30 text-purple-100 border border-purple-500/30' : 'bg-gray-800 text-gray-200 border border-gray-700'}`}>
                            <div className="flex items-center gap-2 mb-1 opacity-50 text-[10px] uppercase font-bold">
                                {msg.role === 'user' ? <User className="w-3 h-3"/> : <Bot className="w-3 h-3"/>}
                                {msg.role === 'user' ? 'You' : 'Advisor'}
                            </div>
                            <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>

                        {/* Render Suggestions Cards */}
                        {msg.suggestions && msg.suggestions.map(sugg => (
                            <div key={sugg.id} className="mt-2 w-[90%] bg-black/40 border border-gray-600 rounded-lg overflow-hidden">
                                <div className="bg-gray-800 px-3 py-1 text-[10px] font-bold text-gray-400 border-b border-gray-700 flex justify-between items-center">
                                    <span>SUGGESTION</span>
                                    {sugg.explanation && <span className="italic font-normal opacity-70">{sugg.explanation}</span>}
                                </div>
                                <div className="p-2 space-y-1">
                                    <div className="bg-red-900/20 text-red-200 p-2 rounded text-xs border border-red-500/20 line-through decoration-red-500/50">
                                        {sugg.original}
                                    </div>
                                    <div className="flex justify-center text-gray-500"><Plus className="w-3 h-3"/></div>
                                    <div className="bg-green-900/20 text-green-200 p-2 rounded text-xs border border-green-500/20 font-medium">
                                        {sugg.replacement}
                                    </div>
                                </div>
                                <div className="flex border-t border-gray-700">
                                    <button onClick={() => handleApplySuggestion(sugg)} className="flex-1 py-1.5 text-xs font-medium text-green-400 hover:bg-green-900/20 flex items-center justify-center gap-1 border-r border-gray-700">
                                        <Check className="w-3 h-3"/> Apply
                                    </button>
                                    <button className="flex-1 py-1.5 text-xs font-medium text-gray-400 hover:bg-gray-800 hover:text-white flex items-center justify-center gap-1">
                                        <X className="w-3 h-3"/> Ignore
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ))}
                
                {isLoading && (
                    <div className="flex items-start gap-2">
                        <div className="bg-gray-800 p-3 rounded-lg border border-gray-700">
                            <Sparkles className="w-4 h-4 animate-spin text-purple-400"/>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-3 bg-gray-950 border-t border-gray-800">
                <div className="flex gap-2">
                    <textarea 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Ask for advice..."
                        className="flex-1 bg-black/20 border border-gray-700 rounded-lg p-2 text-sm text-gray-200 focus:border-purple-500 outline-none resize-none h-10 min-h-[40px] max-h-32 scrollbar-none"
                    />
                    <button 
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white p-2 rounded-lg transition-colors"
                    >
                        <Send className="w-4 h-4"/>
                    </button>
                </div>
            </div>
        </div>
    );
};
