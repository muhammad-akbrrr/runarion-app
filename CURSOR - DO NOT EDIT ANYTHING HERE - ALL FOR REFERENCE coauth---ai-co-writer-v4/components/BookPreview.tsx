
import React, { useMemo, useState } from 'react';
import { X, Printer, Settings2, Type, MoveVertical, MoveHorizontal, FileText, AlignLeft, AlignJustify, Lock, Unlock } from 'lucide-react';
import { BookSettings } from '../types';
import { Button } from './Button';

interface BookPreviewProps {
    isOpen: boolean;
    onClose: () => void;
    content: string;
    settings: BookSettings;
    onUpdateSettings: (settings: BookSettings) => void;
}

export const BookPreview: React.FC<BookPreviewProps> = ({
    isOpen,
    onClose,
    content,
    settings,
    onUpdateSettings
}) => {
    const [isEditing, setIsEditing] = useState(false);

    // Helper to format content into print-ready HTML with better Markdown Support
    const formattedHtml = useMemo(() => {
        if (!content) return '<p>No content to preview.</p>';
        
        // 1. Split paragraphs
        const paragraphs = content.split(/\n\n+/);
        
        let html = '';

        paragraphs.forEach((p) => {
            let trimmed = p.trim();
            if (!trimmed) return;
            
            // Escape Basic HTML chars to prevent injection before we insert our own HTML
            trimmed = trimmed
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");

            // --- INLINE FORMATTING PARSER ---
            // Bold (**text**)
            trimmed = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Italic (*text* or _text_)
            trimmed = trimmed.replace(/\*(.*?)\*/g, '<em>$1</em>');
            trimmed = trimmed.replace(/_(.*?)_/g, '<em>$1</em>');

            // --- BLOCK PARSER ---
            
            // Chapter Heading
            if (trimmed.startsWith('# ')) {
                const title = trimmed.replace(/^#\s+/, '');
                html += `<h1 class="chapter-title">${title}</h1>`;
            }
            // Subheading
            else if (trimmed.startsWith('## ')) {
                const subtitle = trimmed.replace(/^##\s+/, '');
                html += `<h2 class="section-title">${subtitle}</h2>`;
            }
            // Scene Break
            else if (trimmed.includes('***') || trimmed === '---') {
                html += `<div class="scene-break">${settings.sceneBreakMarker}</div>`;
            }
            // Standard Paragraph
            else {
                // Convert remaining newlines within a paragraph to breaks (soft wrap)
                const finalP = trimmed.replace(/\n/g, '<br/>');
                html += `<p>${finalP}</p>`;
            }
        });

        return html;
    }, [content, settings.sceneBreakMarker]);

    if (!isOpen) return null;

    const handlePrint = () => {
        // Force unlock before printing so cursor doesn't show up? 
        // Actually, window.print usually captures what's rendered. 
        // Ideally we turn off edit mode, but user might want to print WITH edits. 
        // But edits are in the DOM. So it works.
        window.print();
    };

    // Calculate print dimensions in mm or inches for preview scaling
    const getPageDimensions = () => {
        switch(settings.trimSize) {
            case '6x9': return { width: '6in', height: '9in' };
            case '5x8': return { width: '5in', height: '8in' };
            case 'a5': return { width: '148mm', height: '210mm' };
            default: return { width: '6in', height: '9in' };
        }
    };

    const dims = getPageDimensions();

    return (
        <div className="fixed inset-0 z-[200] bg-black/95 flex flex-col backdrop-blur-md">
            
            {/* Header / Toolbar (Hidden when printing) */}
            <div className="flex-none p-4 border-b border-gray-800 bg-[#1a1b26] flex items-center justify-between print:hidden">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-serif font-bold text-white flex items-center gap-2"><Printer className="w-5 h-5 text-green-400"/> Typesetter</h2>
                    <div className="h-6 w-px bg-gray-700"/>
                    
                    {/* Size */}
                    <div className="flex flex-col">
                        <label className="text-[9px] text-gray-500 uppercase font-bold">Trim</label>
                        <select 
                            value={settings.trimSize} 
                            onChange={(e) => onUpdateSettings({...settings, trimSize: e.target.value as any})}
                            className="bg-gray-900 border border-gray-700 rounded text-xs text-gray-300 p-1 focus:border-green-500"
                        >
                            <option value="6x9">6" x 9"</option>
                            <option value="5x8">5" x 8"</option>
                            <option value="a5">A5</option>
                        </select>
                    </div>

                    {/* Font */}
                    <div className="flex flex-col">
                        <label className="text-[9px] text-gray-500 uppercase font-bold">Font</label>
                        <select 
                            value={settings.fontFamily} 
                            onChange={(e) => onUpdateSettings({...settings, fontFamily: e.target.value as any})}
                            className="bg-gray-900 border border-gray-700 rounded text-xs text-gray-300 p-1 focus:border-green-500"
                        >
                            <option value="merriweather">Merriweather</option>
                            <option value="garamond">Garamond</option>
                            <option value="baskerville">Baskerville</option>
                            <option value="inter">Inter (Sans)</option>
                        </select>
                    </div>

                    <div className="h-6 w-px bg-gray-700"/>

                    {/* Typography Sliders */}
                    <div className="flex gap-3">
                        <div className="flex flex-col w-20">
                            <label className="text-[9px] text-gray-500 uppercase font-bold">Size ({settings.fontSize}pt)</label>
                            <input type="range" min="8" max="16" step="0.5" value={settings.fontSize} onChange={(e) => onUpdateSettings({...settings, fontSize: parseFloat(e.target.value)})} className="h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer mt-2 accent-green-500"/>
                        </div>
                        <div className="flex flex-col w-20">
                            <label className="text-[9px] text-gray-500 uppercase font-bold">Height ({settings.lineHeight})</label>
                            <input type="range" min="1" max="2.5" step="0.1" value={settings.lineHeight} onChange={(e) => onUpdateSettings({...settings, lineHeight: parseFloat(e.target.value)})} className="h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer mt-2 accent-green-500"/>
                        </div>
                         <div className="flex flex-col w-20">
                            <label className="text-[9px] text-gray-500 uppercase font-bold">Headers ({settings.headingScale}x)</label>
                            <input type="range" min="1" max="3" step="0.1" value={settings.headingScale} onChange={(e) => onUpdateSettings({...settings, headingScale: parseFloat(e.target.value)})} className="h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer mt-2 accent-green-500"/>
                        </div>
                    </div>

                    <div className="h-6 w-px bg-gray-700"/>
                    
                    {/* Alignment Toggle */}
                     <div className="flex bg-gray-900 rounded p-0.5 border border-gray-700">
                        <button onClick={() => onUpdateSettings({...settings, alignment: 'left'})} className={`p-1 rounded ${settings.alignment === 'left' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'}`} title="Left Align"><AlignLeft className="w-3 h-3"/></button>
                        <button onClick={() => onUpdateSettings({...settings, alignment: 'justify'})} className={`p-1 rounded ${settings.alignment === 'justify' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'}`} title="Justify"><AlignJustify className="w-3 h-3"/></button>
                     </div>

                    {/* Edit Mode Toggle */}
                    <button 
                        onClick={() => setIsEditing(!isEditing)} 
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors ${isEditing ? 'bg-yellow-900/40 border-yellow-500 text-yellow-200 shadow-[0_0_10px_rgba(234,179,8,0.3)]' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'}`}
                        title={isEditing ? "Lock Page" : "Unlock to Edit Typo directly"}
                    >
                        {isEditing ? <Unlock className="w-3 h-3"/> : <Lock className="w-3 h-3"/>}
                        {isEditing ? "Unlocked" : "Locked"}
                    </button>
                </div>

                <div className="flex gap-2">
                    <Button onClick={handlePrint} className="bg-green-600 hover:bg-green-500 text-white shadow-lg"><Printer className="w-4 h-4 mr-2"/> Print / PDF</Button>
                    <button onClick={onClose} className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 text-white"><X className="w-5 h-5"/></button>
                </div>
            </div>

            {/* Preview Area */}
            <div className="flex-1 overflow-y-auto bg-[#525659] p-8 flex justify-center print:p-0 print:overflow-visible print:bg-white print:block">
                <style>{`
                    @media print {
                        @page {
                            size: ${settings.trimSize === '6x9' ? '6in 9in' : settings.trimSize === '5x8' ? '5in 8in' : 'A5'};
                            margin: 0; 
                        }
                        body {
                            background: white;
                            color: black;
                        }
                        .print-container {
                            width: 100% !important;
                            height: auto !important;
                            box-shadow: none !important;
                            margin: 0 !important;
                            overflow: visible !important;
                        }
                        /* Hide everything else */
                        body > *:not(.print-root) {
                            display: none;
                        }
                        .print-root {
                            display: block !important;
                            position: static !important;
                            background: white !important;
                            z-index: 9999;
                        }
                    }

                    .book-content {
                        font-family: ${
                            settings.fontFamily === 'merriweather' ? "'Merriweather', serif" :
                            settings.fontFamily === 'garamond' ? "'EB Garamond', 'Garamond', serif" :
                            settings.fontFamily === 'baskerville' ? "'Libre Baskerville', 'Baskerville', serif" :
                            "'Inter', sans-serif"
                        };
                        font-size: ${settings.fontSize}pt;
                        line-height: ${settings.lineHeight};
                        text-align: ${settings.alignment};
                        color: black;
                    }

                    .book-content p {
                        margin: 0;
                        text-indent: ${settings.firstLineIndent}em;
                    }

                    /* No indent for first paragraph after heading or break */
                    .book-content h1 + p, 
                    .book-content h2 + p, 
                    .book-content .scene-break + p {
                        text-indent: 0;
                    }
                    
                    .book-content h1.chapter-title {
                        page-break-before: always;
                        text-align: center;
                        margin-top: ${settings.marginTop * 2}in;
                        margin-bottom: ${settings.marginTop}in;
                        font-size: ${settings.fontSize * 2.5 * settings.headingScale}pt;
                        font-weight: bold;
                        text-indent: 0;
                        line-height: 1.2;
                    }

                    .book-content h2.section-title {
                        text-align: center;
                        margin-top: ${settings.marginTop}in;
                        margin-bottom: 0.5in;
                        font-size: ${settings.fontSize * 1.5 * settings.headingScale}pt;
                        font-style: italic;
                        text-indent: 0;
                    }

                    .book-content .scene-break {
                        text-align: center;
                        margin: 1.5rem 0;
                        font-weight: bold;
                        letter-spacing: 0.5em;
                        text-indent: 0;
                    }
                    
                    /* Edit Mode Visuals */
                    .editable-active {
                        outline: 2px dashed #eab308; /* Yellow-500 */
                        background-color: rgba(253, 224, 71, 0.05); /* Yellow-300 tint */
                        cursor: text;
                    }
                `}</style>

                {/* The "Paper" Page */}
                <div 
                    className="print-container bg-white shadow-2xl mx-auto relative print-root"
                    style={{
                        width: dims.width,
                        minHeight: dims.height,
                        paddingTop: `${settings.marginTop}in`,
                        paddingBottom: `${settings.marginBottom}in`,
                        paddingLeft: `${settings.marginLeft}in`,
                        paddingRight: `${settings.marginRight}in`,
                    }}
                >
                    <div 
                        className={`book-content ${isEditing ? 'editable-active' : ''}`}
                        contentEditable={isEditing}
                        suppressContentEditableWarning={true}
                        dangerouslySetInnerHTML={{ __html: formattedHtml }}
                    />
                </div>
            </div>
        </div>
    );
};
