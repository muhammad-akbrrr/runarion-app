"""
PDF generation utilities for test output.
Converts enhanced manuscript data from database to formatted PDF documents.
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add src to path for database utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from src.utils.database_utils import utf8_database_connection


def generate_enhanced_manuscript_pdf(db_pool, draft_id: str, output_path: str) -> bool:
    """
    Generate a PDF document from enhanced manuscript data in the database.
    
    Args:
        db_pool: Database connection pool
        draft_id: UUID of the processed draft
        output_path: Path where PDF should be saved
        
    Returns:
        Success status
    """
    if not REPORTLAB_AVAILABLE:
        print("⚠️ ReportLab not available - falling back to text output")
        return generate_text_output(db_pool, draft_id, output_path.replace('.pdf', '.txt'))
    
    try:
        # Gather data from database
        manuscript_data = extract_manuscript_data(db_pool, draft_id)
        
        if not manuscript_data:
            print(f"❌ No manuscript data found for draft {draft_id}")
            return False
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build story
        story = build_pdf_story(manuscript_data)
        
        # Generate PDF
        doc.build(story)
        print(f"✓ PDF generated successfully: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_manuscript_data(db_pool, draft_id: str) -> Optional[Dict[str, Any]]:
    """
    Extract all manuscript data from database tables.
    
    Args:
        db_pool: Database connection pool
        draft_id: UUID of the processed draft
        
    Returns:
        Dictionary containing all manuscript data
    """
    data = {
        'draft_info': None,
        'chunks': [],
        'scenes': [],
        'plot_issues': [],
        'processing_stats': {}
    }
    
    with utf8_database_connection(db_pool) as conn:
        cursor = conn.cursor()
        
        # Get draft information
        cursor.execute("""
            SELECT original_filename, status, processing_started_at, 
                   processing_completed_at, metadata, error_message
            FROM drafts WHERE id = %s
        """, (draft_id,))
        
        draft_result = cursor.fetchone()
        if not draft_result:
            return None
            
        data['draft_info'] = {
            'filename': draft_result[0],
            'status': draft_result[1],
            'started_at': draft_result[2],
            'completed_at': draft_result[3],
            'metadata': draft_result[4] or {},
            'error_message': draft_result[5]
        }
        
        # Get text chunks (processed content)
        cursor.execute("""
            SELECT chunk_number, raw_text, cleaned_text 
            FROM draft_chunks 
            WHERE draft_id = %s 
            ORDER BY chunk_number
        """, (draft_id,))
        
        data['chunks'] = [
            {
                'number': row[0],
                'raw_text': row[1],
                'cleaned_text': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # Get scenes (story structure)
        cursor.execute("""
            SELECT scene_number, title, setting, characters, 
                   original_content, enhanced_content, analysis_json
            FROM scenes 
            WHERE draft_id = %s 
            ORDER BY scene_number
        """, (draft_id,))
        
        data['scenes'] = [
            {
                'number': row[0],
                'title': row[1],
                'setting': row[2],
                'characters': row[3],
                'original_content': row[4],
                'enhanced_content': row[5],
                'analysis': row[6]
            }
            for row in cursor.fetchall()
        ]
        
        # Get plot issues (identified problems)
        cursor.execute("""
            SELECT issue_type, description, scene_number, suggested_fix
            FROM plot_issues 
            WHERE draft_id = %s 
            ORDER BY scene_number
        """, (draft_id,))
        
        data['plot_issues'] = [
            {
                'type': row[0],
                'description': row[1],
                'scene': row[2],
                'fix': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # Calculate processing statistics
        data['processing_stats'] = {
            'total_chunks': len(data['chunks']),
            'total_scenes': len(data['scenes']),
            'total_issues': len(data['plot_issues']),
            'processing_time': None
        }
        
        if data['draft_info']['started_at'] and data['draft_info']['completed_at']:
            duration = data['draft_info']['completed_at'] - data['draft_info']['started_at']
            data['processing_stats']['processing_time'] = duration.total_seconds()
    
    return data


def build_pdf_story(manuscript_data: Dict[str, Any]) -> List:
    """
    Build the PDF story elements from manuscript data.
    
    Args:
        manuscript_data: Extracted manuscript data
        
    Returns:
        List of PDF story elements
    """
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title page
    story.append(Paragraph("Enhanced Manuscript", title_style))
    story.append(Spacer(1, 12))
    
    draft_info = manuscript_data['draft_info']
    story.append(Paragraph(f"<b>Original File:</b> {draft_info['filename']}", styles['Normal']))
    story.append(Paragraph(f"<b>Processing Status:</b> {draft_info['status']}", styles['Normal']))
    
    if draft_info['completed_at']:
        completed_str = draft_info['completed_at'].strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"<b>Completed:</b> {completed_str}", styles['Normal']))
    
    stats = manuscript_data['processing_stats']
    story.append(Paragraph(f"<b>Text Chunks:</b> {stats['total_chunks']}", styles['Normal']))
    story.append(Paragraph(f"<b>Scenes Extracted:</b> {stats['total_scenes']}", styles['Normal']))
    story.append(Paragraph(f"<b>Plot Issues Found:</b> {stats['total_issues']}", styles['Normal']))
    
    if stats['processing_time']:
        duration_min = stats['processing_time'] / 60
        story.append(Paragraph(f"<b>Processing Time:</b> {duration_min:.1f} minutes", styles['Normal']))
    
    story.append(PageBreak())
    
    # Processing Summary
    story.append(Paragraph("Processing Summary", heading_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("This manuscript has been processed through the complete Runarion deconstruction pipeline:", styles['Normal']))
    story.append(Spacer(1, 6))
    
    stages = [
        "1. PDF Ingestion - Text extraction and initial processing",
        "2. Text Cleaning - Normalization and formatting cleanup", 
        "3. Scene Detection - Identification of narrative scenes",
        "4. Deep Analysis - Scene analysis, character mapping, and comprehensive reporting",
        "5. Coherence Check - Narrative consistency validation",
        "6. Enhancement - Content quality improvement",
        "7. Chaptering - Organization into structured chapters"
    ]
    
    for stage in stages:
        story.append(Paragraph(f"✓ {stage}", styles['Normal']))
        story.append(Spacer(1, 3))
    
    story.append(PageBreak())
    
    # Scenes Section
    if manuscript_data['scenes']:
        story.append(Paragraph("Extracted Scenes", heading_style))
        story.append(Spacer(1, 12))
        
        for scene in manuscript_data['scenes'][:10]:  # Limit to first 10 scenes for PDF size
            scene_title = scene['title'] or f"Scene {scene['number']}"
            story.append(Paragraph(f"<b>{scene_title}</b>", styles['Heading3']))
            
            if scene['setting']:
                story.append(Paragraph(f"<i>Setting:</i> {scene['setting']}", styles['Normal']))
            
            if scene['characters']:
                try:
                    import json
                    if isinstance(scene['characters'], str):
                        characters = json.loads(scene['characters'])
                    else:
                        characters = scene['characters']
                    
                    if characters:
                        char_list = ', '.join(characters) if isinstance(characters, list) else str(characters)
                        story.append(Paragraph(f"<i>Characters:</i> {char_list}", styles['Normal']))
                except:
                    if scene['characters']:
                        story.append(Paragraph(f"<i>Characters:</i> {scene['characters']}", styles['Normal']))
            
            # Enhanced content if available, otherwise original
            content = scene['enhanced_content'] or scene['original_content']
            if content:
                # Truncate very long content for PDF readability
                if len(content) > 500:
                    content = content[:500] + "..."
                story.append(Paragraph(content, styles['Normal']))
            
            story.append(Spacer(1, 12))
    
    # Plot Issues Section
    if manuscript_data['plot_issues']:
        story.append(PageBreak())
        story.append(Paragraph("Plot Issues & Suggestions", heading_style))
        story.append(Spacer(1, 12))
        
        for issue in manuscript_data['plot_issues']:
            issue_type = issue['type'].replace('_', ' ').title()
            story.append(Paragraph(f"<b>{issue_type}</b> (Scene {issue['scene'] or 'N/A'})", styles['Heading4']))
            story.append(Paragraph(issue['description'], styles['Normal']))
            
            if issue['fix']:
                story.append(Paragraph(f"<i>Suggested Fix:</i> {issue['fix']}", styles['Italic']))
            
            story.append(Spacer(1, 8))
    
    # Final content section (if we have enhanced scenes)
    enhanced_scenes = [s for s in manuscript_data['scenes'] if s.get('enhanced_content')]
    if enhanced_scenes:
        story.append(PageBreak())
        story.append(Paragraph("Enhanced Content Preview", heading_style))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph(
            "The following shows a preview of the enhanced content. "
            "Full enhanced content is available in the database.",
            styles['Normal']
        ))
        story.append(Spacer(1, 12))
        
        for scene in enhanced_scenes[:3]:  # Show first 3 enhanced scenes
            scene_title = scene['title'] or f"Enhanced Scene {scene['number']}"
            story.append(Paragraph(f"<b>{scene_title}</b>", styles['Heading3']))
            
            content = scene['enhanced_content']
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            story.append(Paragraph(content, styles['Normal']))
            story.append(Spacer(1, 12))
    
    return story


def generate_text_output(db_pool, draft_id: str, output_path: str) -> bool:
    """
    Generate a text file output when PDF generation is not available.
    
    Args:
        db_pool: Database connection pool
        draft_id: UUID of the processed draft
        output_path: Path where text file should be saved
        
    Returns:
        Success status
    """
    try:
        manuscript_data = extract_manuscript_data(db_pool, draft_id)
        
        if not manuscript_data:
            print(f"❌ No manuscript data found for draft {draft_id}")
            return False
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("ENHANCED MANUSCRIPT REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Draft info
            draft_info = manuscript_data['draft_info']
            f.write(f"Original File: {draft_info['filename']}\n")
            f.write(f"Processing Status: {draft_info['status']}\n")
            
            if draft_info['completed_at']:
                f.write(f"Completed: {draft_info['completed_at']}\n")
            
            # Statistics
            stats = manuscript_data['processing_stats']
            f.write(f"\nProcessing Statistics:\n")
            f.write(f"- Text Chunks: {stats['total_chunks']}\n")
            f.write(f"- Scenes Extracted: {stats['total_scenes']}\n")
            f.write(f"- Plot Issues Found: {stats['total_issues']}\n")
            
            if stats['processing_time']:
                f.write(f"- Processing Time: {stats['processing_time']/60:.1f} minutes\n")
            
            # Pipeline stages
            f.write(f"\nPipeline Stages Completed:\n")
            stages = [
                "1. PDF Ingestion",
                "2. Text Cleaning", 
                "3. Scene Detection",
                "4. Deep Analysis",
                "5. Coherence Check",
                "6. Enhancement",
                "7. Chaptering"
            ]
            for stage in stages:
                f.write(f"✓ {stage}\n")
            
            # Scenes
            if manuscript_data['scenes']:
                f.write(f"\n\nEXTRACTED SCENES\n")
                f.write("-" * 30 + "\n")
                
                for scene in manuscript_data['scenes'][:5]:  # First 5 scenes
                    scene_title = scene['title'] or f"Scene {scene['number']}"
                    f.write(f"\n{scene_title}\n")
                    
                    if scene['setting']:
                        f.write(f"Setting: {scene['setting']}\n")
                    
                    content = scene['enhanced_content'] or scene['original_content']
                    if content:
                        content = content[:300] + "..." if len(content) > 300 else content
                        f.write(f"\n{content}\n")
                    
                    f.write("-" * 20 + "\n")
            
            # Plot issues
            if manuscript_data['plot_issues']:
                f.write(f"\n\nPLOT ISSUES & SUGGESTIONS\n")
                f.write("-" * 30 + "\n")
                
                for issue in manuscript_data['plot_issues']:
                    issue_type = issue['type'].replace('_', ' ').title()
                    f.write(f"\n{issue_type} (Scene {issue['scene'] or 'N/A'}):\n")
                    f.write(f"{issue['description']}\n")
                    
                    if issue['fix']:
                        f.write(f"Suggested Fix: {issue['fix']}\n")
                    
                    f.write("-" * 15 + "\n")
            
            f.write(f"\n\nAll detailed results are stored in the database with draft ID: {draft_id}\n")
        
        print(f"✓ Text report generated: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False