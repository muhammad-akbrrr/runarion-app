"""
PDF generation service for creating formatted book PDFs with chapter covers.
Features: Custom fonts, Drop caps, Chapter borders, Table of Contents, Page numbers.
"""

import os
import io
import logging
import re
import html
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor, black, grey, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, 
    Image as RLImage, Table, TableStyle, Flowable,
    KeepTogether, BaseDocTemplate, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime
from functools import partial

logger = logging.getLogger(__name__)


class NumberedCanvasWithTOC(canvas.Canvas):
    """Custom canvas that tracks page numbers and handles TOC vs content pages."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._toc_pages = 0  # Number of TOC pages to skip in numbering
        self._page_number_font = 'Times-Roman'
        self._page_number_size = 10
        self._show_page_numbers = True
    
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        """Add page numbers to all pages."""
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            if self._show_page_numbers and i >= self._toc_pages:
                self._draw_page_number(i - self._toc_pages + 1)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def _draw_page_number(self, page_num):
        """Draw page number at the bottom center of the page."""
        self.saveState()
        self.setFont(self._page_number_font, self._page_number_size)
        page_width = self._pagesize[0]
        self.drawCentredString(page_width / 2, 0.5 * inch, str(page_num))
        self.restoreState()


class ChapterBorderTemplate:
    """Template for drawing decorative borders on chapter pages."""
    
    def __init__(self, border_color: str = "#8B4513", border_width: float = 2):
        self.border_color = HexColor(border_color)
        self.border_width = border_width
    
    def draw_border(self, canvas, doc):
        """Draw a decorative border on the page."""
        page_width, page_height = doc.pagesize
        margin = 0.5 * inch
        
        canvas.saveState()
        canvas.setStrokeColor(self.border_color)
        canvas.setLineWidth(self.border_width)
        
        # Outer rectangle
        canvas.rect(
            margin, margin,
            page_width - 2 * margin,
            page_height - 2 * margin
        )
        
        # Inner rectangle (double border effect)
        inner_margin = margin + 8
        canvas.setLineWidth(0.5)
        canvas.rect(
            inner_margin, inner_margin,
            page_width - 2 * inner_margin,
            page_height - 2 * inner_margin
        )
        
        # Corner ornaments
        corners = [
            (margin + 5, margin + 5),
            (page_width - margin - 5, margin + 5),
            (margin + 5, page_height - margin - 5),
            (page_width - margin - 5, page_height - margin - 5),
        ]
        
        canvas.setFillColor(self.border_color)
        for x, y in corners:
            canvas.circle(x, y, 3, fill=1)
        
        canvas.restoreState()


class PDFGenerator:
    """Service for generating formatted PDF books with chapter covers."""
    
    PAPER_SIZES = {
        'a4': A4,
        'letter': letter,
    }
    
    FONT_MAPPINGS = {
        'Times-Roman': 'Times-Roman',
        'Times-Bold': 'Times-Bold',
        'Times-Italic': 'Times-Italic',
        'Helvetica': 'Helvetica',
        'Helvetica-Bold': 'Helvetica-Bold',
        'Courier': 'Courier',
        'Garamond': 'Times-Roman',
        'Georgia': 'Times-Roman',
        'Palatino': 'Times-Roman',
    }
    
    DROP_CAP_FONTS = {
        'UnifrakturCook': 'Times-Bold',
        'Tangerine': 'Times-Italic',
        'Cinzel': 'Times-Bold',
        'Times-Bold': 'Times-Bold',
    }
    
    def __init__(self):
        """Initialize the PDF generator."""
        self._fonts_registered = False
        self._register_custom_fonts()
        try:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        except Exception as e:
            logger.error(f"Failed to initialize PDF generator: {e}")
            self.styles = getSampleStyleSheet()
    
    def _register_custom_fonts(self):
        """Register custom TTF fonts if available."""
        if self._fonts_registered:
            return
            
        font_dirs = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'fonts'),
            '/usr/share/fonts/truetype',
            '/usr/local/share/fonts',
            'C:\\Windows\\Fonts',
            os.path.expanduser('~/.fonts'),
        ]
        
        fonts_to_register = {
            'Garamond': ['Garamond.ttf', 'EBGaramond-Regular.ttf', 'garamond.ttf'],
            'Georgia': ['Georgia.ttf', 'georgia.ttf'],
            'Palatino': ['Palatino.ttf', 'palatino.ttf', 'PalatinoLinotype-Roman.ttf'],
            'UnifrakturCook': ['UnifrakturCook-Bold.ttf', 'unifrakturcook.ttf'],
            'Tangerine': ['Tangerine-Regular.ttf', 'tangerine.ttf'],
            'Cinzel': ['Cinzel-Regular.ttf', 'cinzel.ttf'],
        }
        
        for font_name, possible_files in fonts_to_register.items():
            for font_dir in font_dirs:
                if not os.path.exists(font_dir):
                    continue
                for font_file in possible_files:
                    font_path = os.path.join(font_dir, font_file)
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            self.FONT_MAPPINGS[font_name] = font_name
                            if font_name in self.DROP_CAP_FONTS:
                                self.DROP_CAP_FONTS[font_name] = font_name
                            logger.info(f"Registered font: {font_name} from {font_path}")
                            break
                        except Exception as e:
                            logger.warning(f"Could not register font {font_name}: {e}")
        
        self._fonts_registered = True
    
    def _get_font(self, font_name: str) -> str:
        """Get the actual font name to use (with fallback)."""
        return self.FONT_MAPPINGS.get(font_name, 'Times-Roman')
    
    def _get_drop_cap_font(self, font_name: str) -> str:
        """Get the actual drop cap font name to use (with fallback)."""
        return self.DROP_CAP_FONTS.get(font_name, 'Times-Bold')
    
    def _setup_custom_styles(self, font_name: str = 'Times-Roman', 
                             font_size: int = 12, line_spacing: float = 1.5):
        """Setup custom paragraph styles."""
        actual_font = self._get_font(font_name)
        bold_font = actual_font.replace('-Roman', '-Bold').replace('-Regular', '-Bold')
        if bold_font == actual_font and not actual_font.endswith('-Bold'):
            bold_font = 'Times-Bold'
        
        leading = font_size * line_spacing
        
        try:
            # Chapter title style
            if 'ChapterTitle' not in self.styles.byName:
                self.styles.add(ParagraphStyle(
                    name='ChapterTitle',
                    parent=self.styles['Heading1'],
                    fontSize=24,
                    textColor='black',
                    spaceAfter=30,
                    alignment=TA_CENTER,
                    fontName=bold_font
                ))
            else:
                self.styles['ChapterTitle'].fontName = bold_font
            
            # Body text style
            if 'NovelBodyText' not in self.styles.byName:
                self.styles.add(ParagraphStyle(
                    name='NovelBodyText',
                    parent=self.styles['Normal'],
                    fontSize=font_size,
                    textColor='black',
                    spaceAfter=font_size * 0.8,
                    alignment=TA_JUSTIFY,
                    fontName=actual_font,
                    leading=leading,
                    firstLineIndent=20,
                ))
            else:
                style = self.styles['NovelBodyText']
                style.fontName = actual_font
                style.fontSize = font_size
                style.leading = leading
                style.firstLineIndent = 20
            
            # First paragraph style (no indent, for drop cap)
            # Extra spaceAfter to compensate for the taller drop cap line
            if 'FirstParagraph' not in self.styles.byName:
                self.styles.add(ParagraphStyle(
                    name='FirstParagraph',
                    parent=self.styles['Normal'],
                    fontSize=font_size,
                    textColor='black',
                    spaceAfter=font_size * 1.5,  # More space after drop cap paragraph
                    alignment=TA_JUSTIFY,
                    fontName=actual_font,
                    leading=leading * 1.2,  # Slightly more leading for drop cap line
                    firstLineIndent=0,
                ))
            
            # TOC styles
            if 'TOCHeading' not in self.styles.byName:
                self.styles.add(ParagraphStyle(
                    name='TOCHeading',
                    parent=self.styles['Heading1'],
                    fontSize=24,
                    textColor='black',
                    spaceAfter=40,
                    spaceBefore=20,
                    alignment=TA_CENTER,
                    fontName=bold_font
                ))
            
            if 'TOCEntry' not in self.styles.byName:
                self.styles.add(ParagraphStyle(
                    name='TOCEntry',
                    parent=self.styles['Normal'],
                    fontSize=12,
                    textColor='black',
                    spaceAfter=12,
                    alignment=TA_LEFT,
                    fontName=actual_font,
                    leftIndent=0
                ))
            
        except Exception as e:
            logger.warning(f"Could not setup custom PDF styles, using defaults: {e}")
    
    def _create_drop_cap_paragraph(self, text: str, drop_cap_font: str, 
                                    body_font: str, font_size: int,
                                    uppercase: bool = True) -> str:
        """Create HTML for a paragraph with a drop cap first letter."""
        if not text or len(text.strip()) == 0:
            return ""
        
        text = text.strip()
        
        # Find the first letter
        first_letter_idx = -1
        for i, char in enumerate(text):
            if char.isalpha():
                first_letter_idx = i
                break
        
        if first_letter_idx == -1:
            # No letter found, return as-is
            return html.escape(text)
        
        # Extract parts
        before = text[:first_letter_idx]
        first_letter = text[first_letter_idx]
        after = text[first_letter_idx + 1:]
        
        if uppercase:
            first_letter = first_letter.upper()
        
        # Create the drop cap with larger font
        drop_cap_size = int(font_size * 2.5)
        
        # Use simple inline styling - the drop cap is just a bigger, bold first letter
        formatted = (
            f'{html.escape(before)}'
            f'<font name="{drop_cap_font}" size="{drop_cap_size}"><b>{first_letter}</b></font>'
            f'{html.escape(after)}'
        )
        
        return formatted
    
    def _create_toc_entry(self, chapter_title: str, page_num: int, 
                          available_width: float, font_name: str) -> Table:
        """Create a TOC entry with chapter title, dotted leader, and page number."""
        # Clean up title
        title = html.escape(chapter_title)
        
        # Create table with title on left, page number on right
        # The middle column will have dots
        data = [[
            Paragraph(title, self.styles['TOCEntry']),
            Paragraph(str(page_num), ParagraphStyle(
                'TOCPageNum',
                parent=self.styles['TOCEntry'],
                alignment=TA_RIGHT
            ))
        ]]
        
        # Calculate column widths
        page_num_width = 40
        title_width = available_width - page_num_width
        
        table = Table(data, colWidths=[title_width, page_num_width])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (0, 0), 0.5, grey),  # Dotted line effect
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def generate_pdf(
        self,
        chapters: List[Dict],
        output_path: Optional[str] = None,
        paper_size: str = 'a4',
        margins: Dict[str, float] = None,
        font_name: str = 'Times-Roman',
        font_size: int = 12,
        line_spacing: float = 1.5,
        include_covers: bool = True,
        drop_cap: bool = True,
        drop_cap_font: str = 'UnifrakturCook',
        drop_cap_uppercase: bool = True,
        chapter_borders: bool = False,
        include_toc: bool = True
    ) -> bytes:
        """
        Generate a PDF book from chapters.
        """
        try:
            # Update styles with font settings
            self._setup_custom_styles(font_name, font_size, line_spacing)
            
            # Default margins
            if margins is None:
                margins = {
                    'top': 1.0,
                    'bottom': 1.0,
                    'left': 1.25,
                    'right': 1.25
                }
            
            # Get paper size
            pagesize = self.PAPER_SIZES.get(paper_size.lower(), A4)
            
            # Create PDF buffer
            buffer = io.BytesIO() if not output_path else None
            
            # Border template
            border_template = ChapterBorderTemplate() if chapter_borders else None
            
            # Calculate available width for content
            available_width = pagesize[0] - (margins['left'] + margins['right']) * inch
            
            # Get font settings
            actual_font = self._get_font(font_name)
            actual_drop_cap_font = self._get_drop_cap_font(drop_cap_font)
            
            # First pass: Count TOC pages to set up proper page numbering
            toc_pages = 1 if include_toc and len(chapters) > 1 else 0
            
            # Calculate chapter start pages for TOC
            chapter_start_pages = []
            current_page = 1  # Start at page 1 after TOC
            
            for i, chapter in enumerate(chapters):
                chapter_start_pages.append(current_page)
                # Estimate pages per chapter (rough estimate)
                content = chapter.get('content', '')
                # Roughly 3000 chars per page
                estimated_pages = max(1, len(content) // 3000 + 1)
                if include_covers and chapter.get('cover_image_bytes'):
                    estimated_pages += 1
                current_page += estimated_pages
            
            # Build story (content)
            story = []
            
            # Add Table of Contents if requested
            if include_toc and len(chapters) > 1:
                story.append(Paragraph("Table of Contents", self.styles['TOCHeading']))
                story.append(Spacer(1, 0.3 * inch))
                
                # Create TOC entries with page numbers
                for i, chapter in enumerate(chapters):
                    chapter_title = chapter.get('title', f'Chapter {i+1}')
                    page_num = chapter_start_pages[i] if i < len(chapter_start_pages) else i + 1
                    
                    # Simple TOC entry: "Chapter Title ............... Page"
                    toc_text = f'{html.escape(chapter_title)}'
                    
                    # Create a table row for proper alignment
                    toc_table = self._create_toc_entry(
                        chapter_title, page_num, available_width, actual_font
                    )
                    story.append(toc_table)
                
                story.append(PageBreak())
            
            # Process each chapter
            for i, chapter in enumerate(chapters):
                # Add chapter cover if available
                if include_covers and chapter.get('cover_image_bytes'):
                    try:
                        cover_bytes = chapter['cover_image_bytes']
                        if isinstance(cover_bytes, str):
                            import base64
                            if ',' in cover_bytes:
                                cover_bytes = cover_bytes.split(',', 1)[1]
                            cover_bytes = base64.b64decode(cover_bytes)
                        
                        cover_img = Image.open(io.BytesIO(cover_bytes))
                        page_width = available_width
                        aspect_ratio = cover_img.height / cover_img.width
                        img_width = page_width
                        img_height = img_width * aspect_ratio
                        
                        max_height = 4 * inch
                        if img_height > max_height:
                            img_height = max_height
                            img_width = img_height / aspect_ratio
                        
                        cover_buffer = io.BytesIO()
                        cover_img.save(cover_buffer, format='PNG')
                        cover_buffer.seek(0)
                        
                        rl_image = RLImage(cover_buffer, width=img_width, height=img_height, mask='auto')
                        story.append(rl_image)
                        story.append(Spacer(1, 0.5 * inch))
                    except Exception as e:
                        logger.warning(f"Failed to add cover for chapter {i+1}: {str(e)}")
                
                # Add chapter title
                chapter_title = chapter.get('title', f'Chapter {i+1}')
                story.append(Paragraph(chapter_title, self.styles['ChapterTitle']))
                story.append(Spacer(1, 0.3 * inch))
                
                # Add chapter content - preserve the full content
                content = chapter.get('content', '')
                if content:
                    # Split content into paragraphs (by double newline OR single newline for simplicity)
                    # Try double newline first
                    if '\n\n' in content:
                        paragraphs = content.split('\n\n')
                    else:
                        # If no double newlines, treat single newlines as paragraph breaks
                        paragraphs = content.split('\n')
                    
                    first_para = True
                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue
                        
                        # First paragraph of chapter gets drop cap if enabled
                        if drop_cap and first_para:
                            # Create paragraph with styled drop cap
                            formatted = self._create_drop_cap_paragraph(
                                para, actual_drop_cap_font, actual_font, 
                                font_size, drop_cap_uppercase
                            )
                            story.append(Paragraph(formatted, self.styles['FirstParagraph']))
                            first_para = False
                        else:
                            # Regular paragraph with first-line indent
                            formatted_content = self._format_content_for_pdf(para)
                            story.append(Paragraph(formatted_content, self.styles['NovelBodyText']))
                        
                        story.append(Spacer(1, 2))
                
                # Add page break between chapters (except last)
                if i < len(chapters) - 1:
                    story.append(PageBreak())
            
            # Page callback for borders
            def on_page(canvas_obj, doc, border=None):
                if border:
                    border.draw_border(canvas_obj, doc)
            
            # Create document with custom canvas for page numbers
            doc = SimpleDocTemplate(
                output_path or buffer,
                pagesize=pagesize,
                rightMargin=margins['right'] * inch,
                leftMargin=margins['left'] * inch,
                topMargin=margins['top'] * inch,
                bottomMargin=margins['bottom'] * inch
            )
            
            # Build with custom canvas
            def canvas_maker(filename, **kwargs):
                c = NumberedCanvasWithTOC(filename, **kwargs)
                c._toc_pages = toc_pages
                c._page_number_font = actual_font
                return c
            
            if chapter_borders:
                doc.build(
                    story, 
                    onFirstPage=partial(on_page, border=border_template),
                    onLaterPages=partial(on_page, border=border_template),
                    canvasmaker=canvas_maker
                )
            else:
                doc.build(story, canvasmaker=canvas_maker)
            
            # Return bytes if in-memory
            if not output_path:
                buffer.seek(0)
                return buffer.getvalue()
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _format_content_for_pdf(self, content: str) -> str:
        """
        Convert markdown-style content to HTML for ReportLab.
        """
        # Escape HTML special characters
        content = html.escape(content)
        
        # Convert markdown formatting
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Headers
            if line.startswith('# '):
                formatted_lines.append(f"<b><font size='16'>{line[2:]}</font></b>")
            elif line.startswith('## '):
                formatted_lines.append(f"<b><font size='14'>{line[3:]}</font></b>")
            elif line.startswith('### '):
                formatted_lines.append(f"<b><font size='12'>{line[4:]}</font></b>")
            else:
                # Bold
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                # Italic
                line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
                # Em-dash
                line = line.replace('--', '—')
                formatted_lines.append(line)
        
        return '<br/>'.join(formatted_lines)
