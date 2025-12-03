

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Editor } from './components/Editor';
import { Sidebar } from './components/Sidebar';
import { ChainBuilder } from './components/ChainBuilder';
import { RelationshipMatrix } from './components/RelationshipMatrix';
import { BookPreview } from './components/BookPreview';
import { continueStory } from './services/geminiService';
import { Menu } from 'lucide-react';
import { ModelType, BibleItem, StyleProfile, BibleSchema, DEFAULT_SCHEMAS, GraphTemplate, AdvisorMessage, BookSettings, DEFAULT_BOOK_SETTINGS, EditorIssue } from './types';

const App: React.FC = () => {
  const [content, setContent] = useState<string>('');
  const [instruction, setInstruction] = useState<string>('');
  const [negativeInstruction, setNegativeInstruction] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [isChainBuilderOpen, setIsChainBuilderOpen] = useState<boolean>(false);
  const [isMatrixOpen, setIsMatrixOpen] = useState<boolean>(false);
  const [isBookPreviewOpen, setIsBookPreviewOpen] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<ModelType>(ModelType.GEMINI_3_PRO);
  
  // --- Feature State with Persistence ---
  const [bibleItems, setBibleItems] = useState<BibleItem[]>(() => {
    const saved = localStorage.getItem('coauth_bible');
    return saved ? JSON.parse(saved) : [];
  });

  const [bibleSchemas, setBibleSchemas] = useState<BibleSchema[]>(() => {
    const saved = localStorage.getItem('coauth_schemas');
    if (saved) {
        return JSON.parse(saved);
    }
    return DEFAULT_SCHEMAS;
  });

  const [styles, setStyles] = useState<StyleProfile[]>(() => {
    const saved = localStorage.getItem('coauth_styles');
    return saved ? JSON.parse(saved) : [];
  });
  
  const [graphTemplates, setGraphTemplates] = useState<GraphTemplate[]>(() => {
      const saved = localStorage.getItem('coauth_templates');
      return saved ? JSON.parse(saved) : [];
  });
  
  const [advisorHistory, setAdvisorHistory] = useState<AdvisorMessage[]>(() => {
      const saved = localStorage.getItem('coauth_advisor');
      return saved ? JSON.parse(saved) : [];
  });

  const [bookSettings, setBookSettings] = useState<BookSettings>(() => {
      const saved = localStorage.getItem('coauth_book_settings');
      return saved ? JSON.parse(saved) : DEFAULT_BOOK_SETTINGS;
  });
  
  const [activeStyleId, setActiveStyleId] = useState<string | null>(null);
  const [prefillItem, setPrefillItem] = useState<{name: string, description: string} | null>(null);

  // --- Lifted Scan/Audit State ---
  const [auditResults, setAuditResults] = useState<EditorIssue[]>([]);

  // Persistence Effects
  useEffect(() => { localStorage.setItem('coauth_bible', JSON.stringify(bibleItems)); }, [bibleItems]);
  useEffect(() => { localStorage.setItem('coauth_schemas', JSON.stringify(bibleSchemas)); }, [bibleSchemas]);
  useEffect(() => { localStorage.setItem('coauth_styles', JSON.stringify(styles)); }, [styles]);
  useEffect(() => { localStorage.setItem('coauth_templates', JSON.stringify(graphTemplates)); }, [graphTemplates]);
  useEffect(() => { localStorage.setItem('coauth_advisor', JSON.stringify(advisorHistory)); }, [advisorHistory]);
  useEffect(() => { localStorage.setItem('coauth_book_settings', JSON.stringify(bookSettings)); }, [bookSettings]);

  // Load Content
  useEffect(() => {
    const savedContent = localStorage.getItem('coauth_content');
    if (savedContent) setContent(savedContent);
  }, []);

  useEffect(() => {
    localStorage.setItem('coauth_content', content);
  }, [content]);

  // Computed active style
  const activeStyleProfile = useMemo(() => 
    styles.find(s => s.id === activeStyleId) || null
  , [styles, activeStyleId]);

  // Calculate simple word count
  const wordCount = useMemo(() => {
    return content.trim().split(/\s+/).filter(w => w.length > 0).length;
  }, [content]);

  const handleGenerate = useCallback(async () => {
    if (isGenerating) return;

    if (!content.trim() && !instruction.trim()) {
      alert("Please write something or provide an instruction to start.");
      return;
    }

    setIsGenerating(true);

    await continueStory(content, instruction, selectedModel, activeStyleProfile, {
      onChunk: (text) => {
        setContent((prev) => prev + text);
      },
      onComplete: () => {
        setIsGenerating(false);
      },
      onError: (error) => {
        console.error(error);
        setIsGenerating(false);
        alert("Failed to generate content. See console for details.");
      }
    }, negativeInstruction); // Pass negative instruction
  }, [content, instruction, negativeInstruction, isGenerating, selectedModel, activeStyleProfile]);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  // Schema Management
  const handleUpdateSchema = (updatedSchema: BibleSchema) => {
      setBibleSchemas(prev => {
          const exists = prev.find(s => s.id === updatedSchema.id);
          if (exists) {
              return prev.map(s => s.id === updatedSchema.id ? updatedSchema : s);
          }
          return [...prev, updatedSchema];
      });
  };

  const handleUpdateBibleItem = (updatedItem: BibleItem) => {
      setBibleItems(prev => prev.map(item => item.id === updatedItem.id ? updatedItem : item));
  };
  
  const handleUpdateStyle = (updatedStyle: StyleProfile) => {
      setStyles(prev => prev.map(s => s.id === updatedStyle.id ? updatedStyle : s));
  };
  
  const handleResetProject = () => {
      // Nuclear option: Clear EVERYTHING
      localStorage.clear();
      // Force reload immediately. 
      // We do NOT update state here to avoid race conditions where 
      // useEffects might write empty arrays back to localStorage before the reload happens.
      window.location.reload();
  };

  return (
    <div className="flex h-screen bg-paper overflow-hidden text-gray-200">
      
      {/* Main Content Area */}
      <main className={`flex-1 flex flex-col h-full transition-all duration-300 ease-in-out ${isSidebarOpen ? 'mr-80' : 'mr-0'}`}>
        
        {/* Top Navigation / Toolbar */}
        <header className="h-14 border-b border-gray-800 flex items-center justify-between px-6 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-4">
             <h1 className="font-serif text-lg text-gray-100 tracking-wide font-bold italic">
               CoAuth
             </h1>
             <span className="px-2 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400 border border-gray-700">Beta</span>
          </div>
          
          {!isSidebarOpen && (
            <button 
              onClick={toggleSidebar}
              className="p-2 text-gray-400 hover:text-white rounded-md hover:bg-gray-800 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
        </header>

        {/* Editor Wrapper */}
        <div className="flex-1 overflow-hidden relative">
          <div className="max-w-4xl mx-auto h-full shadow-2xl bg-[#1a1b26]">
             <Editor 
               content={content} 
               onChange={setContent} 
               isGenerating={isGenerating}
               selectedModel={selectedModel}
               activeStyleProfile={activeStyleProfile}
               auditResults={auditResults} // Pass down visual markers
             />
          </div>
        </div>
      </main>

      {/* Sidebar Controls */}
      <Sidebar 
        instruction={instruction}
        setInstruction={setInstruction}
        negativeInstruction={negativeInstruction}
        setNegativeInstruction={setNegativeInstruction}
        onGenerate={handleGenerate}
        isGenerating={isGenerating}
        wordCount={wordCount}
        isOpen={isSidebarOpen}
        onToggle={toggleSidebar}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onOpenChainBuilder={() => setIsChainBuilderOpen(true)}
        onOpenRelationshipMatrix={() => setIsMatrixOpen(true)}
        onOpenBookPreview={() => setIsBookPreviewOpen(true)}
        
        // Pass LIVE content from React state
        storyContent={content}
        
        // Content Updater for Auto-Fix
        onUpdateContent={setContent}

        // Bible Props
        bibleItems={bibleItems}
        bibleSchemas={bibleSchemas}
        onAddBibleItem={(item) => setBibleItems(prev => [...prev, item])}
        onUpdateBibleItem={handleUpdateBibleItem}
        onDeleteBibleItem={(id) => setBibleItems(prev => prev.filter(i => i.id !== id))}
        onAddSchema={handleUpdateSchema} 
        
        prefillItem={prefillItem}
        onClearPrefill={() => setPrefillItem(null)}

        // Style Props
        styles={styles}
        activeStyleId={activeStyleId}
        onAddStyle={(style) => setStyles(prev => [...prev, style])}
        onUpdateStyle={handleUpdateStyle}
        onDeleteStyle={(id) => {
            setStyles(prev => prev.filter(s => s.id !== id));
            if (activeStyleId === id) setActiveStyleId(null);
        }}
        onSelectStyle={setActiveStyleId}
        
        onResetProject={handleResetProject}
        
        advisorHistory={advisorHistory}
        setAdvisorHistory={setAdvisorHistory}

        // Scan Props
        auditResults={auditResults}
        setAuditResults={setAuditResults}
      />
      
      {/* Modals */}
      <ChainBuilder 
        isOpen={isChainBuilderOpen}
        onClose={() => setIsChainBuilderOpen(false)}
        storyContext={content}
        selectedModel={selectedModel}
        onApplyResult={(text) => setContent(prev => prev + '\n' + text)}
        bibleItems={bibleItems}
        bibleSchemas={bibleSchemas}
        activeStyleProfile={activeStyleProfile}
        templates={graphTemplates}
        onSaveTemplate={(tmpl) => setGraphTemplates(prev => [...prev, tmpl])}
        onLoadTemplate={(tmpl) => { /* Handled locally */ }}
        onDeleteTemplate={(id) => setGraphTemplates(prev => prev.filter(t => t.id !== id))}
        onPromoteNode={(name, description) => {
            setPrefillItem({name, description});
            setIsChainBuilderOpen(false); // Close modal to focus on sidebar form
        }}
      />
      
      <RelationshipMatrix 
        isOpen={isMatrixOpen}
        onClose={() => setIsMatrixOpen(false)}
        bibleItems={bibleItems}
      />

      <BookPreview
        isOpen={isBookPreviewOpen}
        onClose={() => setIsBookPreviewOpen(false)}
        content={content}
        settings={bookSettings}
        onUpdateSettings={setBookSettings}
      />
      
    </div>
  );
};

export default App;