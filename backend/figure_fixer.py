"""
Figure Fixer Backend - Main Module
Academic research figure compliance analysis and optimization system
"""

import os
import io
import json
import uuid
import sqlite3
import logging
import hashlib
import mimetypes
from PIL import Image, ImageDraw
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FigureAnalysis:
    """Data class for figure analysis results"""
    filename: str
    file_format: str
    file_size_mb: float
    dimensions_px: Tuple[int, int]
    dimensions_inches: Tuple[float, float]
    dpi: Tuple[int, int]
    min_dpi: int
    color_mode: str
    has_transparency: bool
    estimated_print_quality: str
    issues: List[str]
    quality_score: int


@dataclass
class PublicationRequirement:
    """Data class for publication requirements"""
    name: str
    type: str
    description: str
    formats: List[str]
    min_dpi: int
    color_modes: List[str]
    max_file_size_mb: int
    width_range_inches: Tuple[float, float]
    height_range_inches: Optional[Tuple[float, float]]
    special_requirements: List[str]


@dataclass
class ComplianceResult:
    """Data class for compliance check results"""
    overall_compliant: bool
    score: int
    issues: List[str]
    checks: Dict[str, Any]
    priority_fixes: List[str]


class DatabaseManager:
    """Handles all database operations for Figure Fixer"""
    
    def __init__(self, db_path: str = "figure_fixer.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tables from the schema
            cursor.executescript("""
            -- Publication requirements table
            CREATE TABLE IF NOT EXISTS publication_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publication_type TEXT NOT NULL,
                publication_name TEXT NOT NULL,
                category TEXT,
                requirements TEXT NOT NULL,
                file_formats TEXT NOT NULL,
                min_dpi INTEGER DEFAULT 300,
                color_mode TEXT,
                max_file_size_mb INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Uploaded figures table
            CREATE TABLE IF NOT EXISTS uploaded_figures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_format TEXT NOT NULL,
                file_size_kb INTEGER,
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'uploaded',
                publication_type TEXT,
                publication_name TEXT
            );

            -- Figure analysis results table
            CREATE TABLE IF NOT EXISTS figure_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                figure_id INTEGER NOT NULL,
                analysis_data TEXT NOT NULL,
                compliance_score REAL,
                issues_found TEXT,
                recommendations TEXT,
                analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (figure_id) REFERENCES uploaded_figures(id)
            );

            -- Processing sessions table
            CREATE TABLE IF NOT EXISTS processing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_files_processed INTEGER DEFAULT 0,
                settings TEXT
            );

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_figures_session ON uploaded_figures(session_id);
            CREATE INDEX IF NOT EXISTS idx_analysis_figure ON figure_analysis(figure_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_id ON processing_sessions(session_id);
            """)
            
            # Insert default publication requirements
            self._insert_default_requirements(cursor)
            conn.commit()
    
    def _insert_default_requirements(self, cursor):
        """Insert default publication requirements"""
        requirements = [
            # Journals
            ('journal', 'Nature', 'International Journals', 
             'PDF/PNG/TIFF; ≥300 dpi; RGB/CMYK; follow Nature figure style guidelines; clear legends and readable fonts.',
             'PDF,PNG,TIFF', 300, 'RGB/CMYK', 30),
            ('journal', 'Science', 'International Journals',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; adhere to Science figure style; ensure font readability.',
             'PDF,PNG,TIFF', 300, 'RGB', 20),
            ('journal', 'Cell', 'International Journals',
             'PDF/PNG/TIFF; ≥300 dpi; RGB/CMYK; include scale bars and clear legends; follow Cell submission rules.',
             'PDF,PNG,TIFF', 300, 'RGB/CMYK', 50),
            ('journal', 'The Lancet', 'International Journals',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; high-resolution figures with clear labeling.',
             'PDF,PNG,TIFF', 300, 'RGB', 25),
            ('journal', 'New England Journal of Medicine', 'International Journals',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; clear legends and appropriate font size.',
             'PDF,PNG,TIFF', 300, 'RGB', 25),
            
            # Conferences
            ('conference', 'ACM CHI', 'Computer Science',
             'PDF/PNG; ≥300 dpi; RGB; follow ACM CHI figure guidelines; readable fonts and clear labels.',
             'PDF,PNG', 300, 'RGB', 15),
            ('conference', 'IEEE ICCV', 'Computer Science',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; follow IEEE figure guidelines.',
             'PDF,PNG,TIFF', 300, 'RGB', 20),
            ('conference', 'NeurIPS', 'Computer Science',
             'PDF/PNG; ≥300 dpi; RGB; legible fonts and clear diagrams.',
             'PDF,PNG', 300, 'RGB', 15),
            ('conference', 'American Medical Association', 'Medicine',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; ensure clarity and proper labeling.',
             'PDF,PNG,TIFF', 300, 'RGB', 25),
            
            # Thesis
            ('thesis', "Master's Thesis", 'Academic',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; follow department template; include legends, labels, scale bars if needed.',
             'PDF,PNG,TIFF', 300, 'RGB', 50),
            ('thesis', 'PhD Thesis', 'Academic',
             'PDF/PNG/TIFF; ≥300 dpi; RGB/CMYK; follow institution thesis guidelines.',
             'PDF,PNG,TIFF', 300, 'RGB/CMYK', 100),
            ('thesis', 'Institution-Specific', 'Academic',
             'PDF/PNG/TIFF; ≥300 dpi; RGB; follow specific institution formatting requirements.',
             'PDF,PNG,TIFF', 300, 'RGB', 75),
        ]
        
        for req in requirements:
            cursor.execute("""
                INSERT OR IGNORE INTO publication_requirements 
                (publication_type, publication_name, category, requirements, file_formats, min_dpi, color_mode, max_file_size_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, req)
    
    def create_session(self) -> str:
        """Create new processing session"""
        session_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_sessions (session_id, settings)
                VALUES (?, ?)
            """, (session_id, json.dumps({})))
            conn.commit()
        return session_id
    
    def save_figure_upload(self, session_id: str, filename: str, file_path: str, 
                          file_format: str, file_size_kb: int, pub_type: str = None, 
                          pub_name: str = None) -> int:
        """Save uploaded figure information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO uploaded_figures 
                (session_id, original_filename, file_path, file_format, file_size_kb, publication_type, publication_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, filename, file_path, file_format, file_size_kb, pub_type, pub_name))
            
            figure_id = cursor.lastrowid
            
            # Update session activity
            cursor.execute("""
                UPDATE processing_sessions 
                SET last_activity = CURRENT_TIMESTAMP,
                    total_files_processed = total_files_processed + 1
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            return figure_id
    
    def save_figure_analysis(self, figure_id: int, analysis: FigureAnalysis, 
                           compliance: ComplianceResult, recommendations: List[Dict]) -> bool:
        """Save figure analysis results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO figure_analysis 
                    (figure_id, analysis_data, compliance_score, issues_found, recommendations)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    figure_id,
                    json.dumps(asdict(analysis)),
                    compliance.score,
                    json.dumps(compliance.issues),
                    json.dumps(recommendations)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save analysis for figure {figure_id}: {e}")
            return False
    
    def get_publication_requirements(self, pub_type: str, pub_name: str) -> Optional[Dict]:
        """Get requirements for specific publication"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM publication_requirements 
                WHERE publication_type = ? AND publication_name = ?
            """, (pub_type, pub_name))
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
        return None
    
    def get_session_figures(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get figures for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, a.compliance_score, a.issues_found
                FROM uploaded_figures f
                LEFT JOIN figure_analysis a ON f.id = a.figure_id
                WHERE f.session_id = ?
                ORDER BY f.upload_timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


class FigureAnalyzer:
    """Handles figure analysis and quality assessment"""
    
    def __init__(self):
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.pdf', '.eps', '.svg'}
        self.temp_dir = tempfile.mkdtemp(prefix='figure_fixer_')
    
    def __del__(self):
        """Cleanup temporary directory"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def analyze_figure(self, file_data: bytes, filename: str) -> Tuple[bool, Union[FigureAnalysis, str]]:
        """Analyze uploaded figure file"""
        try:
            # Determine file format
            file_format = self._get_file_format(filename, file_data)
            if not file_format:
                return False, "Unsupported file format"
            
            # Save temporary file
            temp_path = os.path.join(self.temp_dir, f"{uuid.uuid4().hex}_{filename}")
            with open(temp_path, 'wb') as f:
                f.write(file_data)
            
            # Analyze based on format
            if file_format.lower() in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
                return self._analyze_raster_image(temp_path, filename, file_data)
            elif file_format.lower() == '.pdf':
                return self._analyze_pdf(temp_path, filename, file_data)
            else:
                return self._analyze_generic_file(temp_path, filename, file_data)
            
        except Exception as e:
            logger.error(f"Analysis failed for {filename}: {e}")
            return False, f"Analysis error: {str(e)}"
        finally:
            # Cleanup temp file
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _get_file_format(self, filename: str, file_data: bytes) -> Optional[str]:
        """Determine file format from filename and content"""
        # Check by extension
        ext = Path(filename).suffix.lower()
        if ext in self.supported_formats:
            return ext
        
        # Check by magic bytes
        if file_data[:4] == b'\x89PNG':
            return '.png'
        elif file_data[:3] == b'\xff\xd8\xff':
            return '.jpg'
        elif file_data[:4] == b'%PDF':
            return '.pdf'
        elif file_data[:2] == b'II' or file_data[:2] == b'MM':
            return '.tiff'
        
        return None
    
    def _analyze_raster_image(self, file_path: str, filename: str, file_data: bytes) -> Tuple[bool, FigureAnalysis]:
        """Analyze raster image (PNG, JPEG, TIFF)"""
        try:
            with Image.open(file_path) as img:
                # Basic image properties
                width_px, height_px = img.size
                file_format = img.format or Path(filename).suffix.upper().lstrip('.')
                
                # DPI information
                dpi = img.info.get('dpi', (72, 72))
                if isinstance(dpi, (int, float)):
                    dpi = (dpi, dpi)
                min_dpi = min(dpi)
                
                # Calculate dimensions in inches
                width_inches = width_px / dpi[0] if dpi[0] > 0 else width_px / 72
                height_inches = height_px / dpi[1] if dpi[1] > 0 else height_px / 72
                
                # Color mode
                color_mode = img.mode
                if color_mode == 'P':  # Palette mode
                    color_mode = 'RGB' if img.getcolors(maxcolors=256) else 'RGB'
                
                # Transparency check
                has_transparency = (
                    img.mode in ('RGBA', 'LA') or
                    (img.mode == 'P' and 'transparency' in img.info)
                )
                
                # Quality assessment
                issues = []
                quality_score = 100
                
                # Check DPI
                if min_dpi < 300:
                    issues.append(f"Low DPI: {min_dpi} (recommended: 300+)")
                    quality_score -= 25
                elif min_dpi < 600:
                    quality_score -= 10
                
                # Check dimensions
                if width_px < 1000 or height_px < 1000:
                    issues.append("Small pixel dimensions may affect print quality")
                    quality_score -= 15
                
                # Check file size vs resolution
                file_size_mb = len(file_data) / (1024 * 1024)
                expected_size = (width_px * height_px * 3) / (1024 * 1024)  # Rough estimate
                
                if file_size_mb > expected_size * 10:
                    issues.append("File size unusually large for resolution")
                    quality_score -= 10
                elif file_size_mb < expected_size * 0.1:
                    issues.append("File may be over-compressed")
                    quality_score -= 15
                
                # Estimate print quality
                if min_dpi >= 600:
                    print_quality = "Excellent"
                elif min_dpi >= 300:
                    print_quality = "Good"
                elif min_dpi >= 150:
                    print_quality = "Fair"
                else:
                    print_quality = "Poor"
                
                return True, FigureAnalysis(
                    filename=filename,
                    file_format=file_format,
                    file_size_mb=file_size_mb,
                    dimensions_px=(width_px, height_px),
                    dimensions_inches=(width_inches, height_inches),
                    dpi=dpi,
                    min_dpi=min_dpi,
                    color_mode=color_mode,
                    has_transparency=has_transparency,
                    estimated_print_quality=print_quality,
                    issues=issues,
                    quality_score=max(0, quality_score)
                )
                
        except Exception as e:
            logger.error(f"Raster analysis failed for {filename}: {e}")
            return False, f"Image analysis error: {str(e)}"
    
    def _analyze_pdf(self, file_path: str, filename: str, file_data: bytes) -> Tuple[bool, FigureAnalysis]:
        """Analyze PDF file"""
        try:
            # Basic file info
            file_size_mb = len(file_data) / (1024 * 1024)
            
            # For PDF analysis, we'd typically use PyPDF2 or similar
            # This is a simplified implementation
            issues = []
            quality_score = 90  # PDFs generally maintain quality well
            
            if file_size_mb > 50:
                issues.append("Large PDF file size")
                quality_score -= 10
            
            # Estimate based on file size and content
            estimated_dpi = 300 if file_size_mb > 1 else 150
            
            return True, FigureAnalysis(
                filename=filename,
                file_format='PDF',
                file_size_mb=file_size_mb,
                dimensions_px=(0, 0),  # Not easily determined for PDF
                dimensions_inches=(0, 0),
                dpi=(estimated_dpi, estimated_dpi),
                min_dpi=estimated_dpi,
                color_mode='RGB',
                has_transparency=False,
                estimated_print_quality="Good" if estimated_dpi >= 300 else "Fair",
                issues=issues,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"PDF analysis failed for {filename}: {e}")
            return False, f"PDF analysis error: {str(e)}"
    
    def _analyze_generic_file(self, file_path: str, filename: str, file_data: bytes) -> Tuple[bool, FigureAnalysis]:
        """Analyze other file formats"""
        file_size_mb = len(file_data) / (1024 * 1024)
        file_format = Path(filename).suffix.upper().lstrip('.')
        
        return True, FigureAnalysis(
            filename=filename,
            file_format=file_format,
            file_size_mb=file_size_mb,
            dimensions_px=(0, 0),
            dimensions_inches=(0, 0),
            dpi=(300, 300),  # Assume vector format
            min_dpi=300,
            color_mode='RGB',
            has_transparency=True,
            estimated_print_quality="Good",
            issues=["Cannot determine detailed properties for this format"],
            quality_score=75
        )


class ComplianceChecker:
    """Checks figure compliance against publication requirements"""
    
    def check_compliance(self, analysis: FigureAnalysis, requirements: Dict[str, Any]) -> ComplianceResult:
        """Check figure compliance against requirements"""
        issues = []
        score = 100
        checks = {}
        priority_fixes = []
        
        # Extract requirements
        min_dpi = requirements.get('min_dpi', 300)
        allowed_formats = requirements.get('file_formats', 'PDF,PNG,TIFF').split(',')
        max_size_mb = requirements.get('max_file_size_mb', 50)
        color_modes = requirements.get('color_mode', 'RGB').split('/')
        
        # DPI check
        dpi_compliant = analysis.min_dpi >= min_dpi
        checks['dpi'] = {
            'required': min_dpi,
            'actual': analysis.min_dpi,
            'compliant': dpi_compliant,
            'description': f'Minimum {min_dpi} DPI required'
        }
        
        if not dpi_compliant:
            issues.append(f'DPI too low: {analysis.min_dpi} (required: {min_dpi}+)')
            priority_fixes.append('Increase image DPI/resolution')
            score -= 30
        
        # Format check
        format_compliant = analysis.file_format.upper() in [f.strip().upper() for f in allowed_formats]
        checks['format'] = {
            'required': allowed_formats,
            'actual': analysis.file_format,
            'compliant': format_compliant,
            'description': f'Accepted formats: {", ".join(allowed_formats)}'
        }
        
        if not format_compliant:
            issues.append(f'Format not accepted: {analysis.file_format} (allowed: {", ".join(allowed_formats)})')
            priority_fixes.append(f'Convert to {allowed_formats[0]} format')
            score -= 20
        
        # File size check
        size_compliant = analysis.file_size_mb <= max_size_mb
        checks['file_size'] = {
            'required': f'≤{max_size_mb}MB',
            'actual': f'{analysis.file_size_mb:.1f}MB',
            'compliant': size_compliant,
            'description': f'Maximum file size: {max_size_mb}MB'
        }
        
        if not size_compliant:
            issues.append(f'File too large: {analysis.file_size_mb:.1f}MB (max: {max_size_mb}MB)')
            priority_fixes.append('Reduce file size through compression or resizing')
            score -= 15
        
        # Color mode check (if available)
        if analysis.color_mode:
            color_compliant = analysis.color_mode in color_modes or 'RGB' in color_modes
            checks['color_mode'] = {
                'required': color_modes,
                'actual': analysis.color_mode,
                'compliant': color_compliant,
                'description': f'Accepted color modes: {", ".join(color_modes)}'
            }
            
            if not color_compliant:
                issues.append(f'Color mode not preferred: {analysis.color_mode} (preferred: {", ".join(color_modes)})')
                score -= 10
        
        # Dimension checks (basic)
        if analysis.dimensions_inches[0] > 0:
            width_inches = analysis.dimensions_inches[0]
            if width_inches < 3.0:
                issues.append(f'Figure may be too narrow: {width_inches:.1f}" (consider 3"+ for readability)')
                score -= 10
            elif width_inches > 8.0:
                issues.append(f'Figure may be too wide: {width_inches:.1f}" (consider <8" for publications)')
                score -= 10
        
        # Additional quality issues from analysis
        for issue in analysis.issues:
            issues.append(issue)
            score -= 5
        
        # Overall compliance
        overall_compliant = (
            dpi_compliant and 
            format_compliant and 
            size_compliant and 
            score >= 70
        )
        
        return ComplianceResult(
            overall_compliant=overall_compliant,
            score=max(0, score),
            issues=issues,
            checks=checks,
            priority_fixes=priority_fixes
        )


class RecommendationGenerator:
    """Generates specific recommendations for figure improvement"""
    
    def generate_recommendations(self, analysis: FigureAnalysis, compliance: ComplianceResult, 
                               requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # DPI recommendations
        if not compliance.checks.get('dpi', {}).get('compliant', True):
            min_dpi = requirements.get('min_dpi', 300)
            current_dpi = analysis.min_dpi
            
            recommendations.append({
                'type': 'dpi',
                'priority': 'critical',
                'title': 'Increase Image Resolution',
                'description': f'Current DPI: {current_dpi}, Required: {min_dpi}+',
                'steps': [
                    'Open image in professional editing software (Photoshop, GIMP)',
                    f'Go to Image → Image Size',
                    f'Set resolution to {min_dpi} DPI or higher',
                    'Ensure "Resample" is checked for quality preservation',
                    'Save in original format'
                ],
                'tools_needed': ['Image editing software'],
                'estimated_time': '5-10 minutes',
                'difficulty': 'easy'
            })
        
        # Format recommendations
        format_check = compliance.checks.get('format', {})
        if not format_check.get('compliant', True):
            allowed_formats = format_check.get('required', ['PNG'])
            recommended = allowed_formats[0] if allowed_formats else 'PNG'
            
            recommendations.append({
                'type': 'format',
                'priority': 'high',
                'title': 'Convert File Format',
                'description': f'Convert from {analysis.file_format} to {recommended}',
                'steps': [
                    'Open image in editing software',
                    'Go to File → Export As or Save As',
                    f'Select {recommended} format',
                    'Choose highest quality settings',
                    'Save with descriptive filename'
                ],
                'tools_needed': ['Image editing software or online converter'],
                'estimated_time': '2-5 minutes',
                'difficulty': 'easy'
            })
        
        # File size recommendations
        if not compliance.checks.get('file_size', {}).get('compliant', True):
            max_size = requirements.get('max_file_size_mb', 50)
            current_size = analysis.file_size_mb
            
            techniques = []
            if analysis.file_format.upper() in ['JPEG', 'JPG']:
                techniques = ['Adjust JPEG quality to 85-90%', 'Remove metadata/EXIF data']
            elif analysis.file_format.upper() == 'PNG':
                techniques = ['Use PNG optimization tools', 'Consider converting to JPEG if no transparency needed']
            else:
                techniques = ['Reduce image dimensions by 10-20%', 'Compress using format-specific tools']
            
            recommendations.append({
                'type': 'file_size',
                'priority': 'medium',
                'title': 'Reduce File Size',
                'description': f'Reduce from {current_size:.1f}MB to under {max_size}MB',
                'steps': techniques + [
                    'Check file size before final save',
                    'Verify image quality is still acceptable'
                ],
                'tools_needed': ['Image editing software', 'Compression tools'],
                'estimated_time': '5-15 minutes',
                'difficulty': 'intermediate'
            })
        
        # Quality-specific recommendations
        if analysis.quality_score < 80:
            quality_issues = []
            if analysis.min_dpi < 300:
                quality_issues.append('Resolution too low for print quality')
            if analysis.dimensions_px[0] < 1200 or analysis.dimensions_px[1] < 1200:
                quality_issues.append('Pixel dimensions may be insufficient')
            
            if quality_issues:
                recommendations.append({
                    'type': 'quality',
                    'priority': 'high',
                    'title': 'Improve Overall Quality',
                    'description': 'Address quality issues that may affect publication',
                    'steps': [
                        'Create figure at higher resolution from original data',
                        'Ensure text and labels are crisp and readable',
                        'Use vector formats (PDF, SVG) when possible',
                        'Avoid upscaling low-resolution images'
                    ],
                    'tools_needed': ['Original data/software', 'Professional graphics software'],
                    'estimated_time': '30-60 minutes',
                    'difficulty': 'advanced'
                })
        
        # Publication-specific recommendations
        pub_name = requirements.get('publication_name', '')
        if pub_name:
            specific_guidance = self._get_publication_specific_guidance(pub_name)
            if specific_guidance:
                recommendations.append({
                    'type': 'publication_specific',
                    'priority': 'medium',
                    'title': f'{pub_name} Specific Guidelines',
                    'description': f'Follow {pub_name} figure requirements',
                    'steps': specific_guidance,
                    'tools_needed': ['Publication style guide'],
                    'estimated_time': '15-30 minutes',
                    'difficulty': 'intermediate'
                })
        
        return recommendations
    
    def _get_publication_specific_guidance(self, publication_name: str) -> List[str]:
        """Get publication-specific guidance"""
        guidance = {
            'Nature': [
                'Use Arial or Helvetica fonts at 5-7pt minimum',
                'Include clear figure legends below each figure',
                'Use consistent color schemes across related figures',
                'Ensure figures are understandable without referencing text'
            ],
            'Science': [
                'Use sans-serif fonts (Arial, Helvetica) at readable sizes',
                'Make figures self-explanatory with comprehensive captions',
                'Use high contrast for key elements',
                'Follow Science color accessibility guidelines'
            ],
            'Cell': [
                'Include scale bars where appropriate',
                'Use consistent labeling scheme (A, B, C) for multi-panel figures',
                'Ensure high contrast between text and background',
                'Follow Cell Press figure formatting guidelines'
            ],
            'The Lancet': [
                'Use clear, professional presentation',
                'Include descriptive figure titles',
                'Ensure accessibility for color-blind readers',
                'Follow medical journal standards'
            ],
            'New England Journal of Medicine': [
                'Use professional medical figure standards',
                'Include appropriate statistical annotations',
                'Ensure clinical relevance is clear',
                'Follow NEJM submission guidelines'
            ],
            'ACM CHI': [
                'Use readable fonts (minimum 8pt)',
                'Ensure figures work in grayscale',
                'Include clear axis labels and legends',
                'Follow ACM digital library standards'
            ],
            'IEEE ICCV': [
                'Use high-quality technical illustrations',
                'Include detailed captions explaining methodology',
                'Ensure reproducibility from figure alone',
                'Follow IEEE formatting requirements'
            ],
            'NeurIPS': [
                'Focus on clarity of experimental setup',
                'Use consistent notation across figures',
                'Include error bars and statistical significance',
                'Optimize for both print and digital viewing'
            ]
        }
        return guidance.get(publication_name, [])


class FigureFixer:
    """Main Figure Fixer class that orchestrates all components"""
    
    def __init__(self, db_path: str = "database/figures.db"):
        self.db_manager = DatabaseManager(db_path)
        self.analyzer = FigureAnalyzer()
        self.compliance_checker = ComplianceChecker()
        self.recommendation_generator = RecommendationGenerator()
        
        # Create upload directory if it doesn't exist
        self.upload_dir = Path("uploads/figures")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Figure Fixer initialized successfully")
    
    def process_figure_submission(self, session_id: str, files: List[Dict[str, Any]], 
                                publication_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Main entry point for processing figure submissions
        
        Args:
            session_id: User session identifier
            files: List of uploaded files [{'filename': str, 'data': bytes}]
            publication_info: {'type': str, 'name': str, 'custom_requirements': str}
        
        Returns:
            Processing results with analysis, compliance, and recommendations
        """
        try:
            # Get publication requirements
            pub_type = publication_info.get('type', 'journal')
            pub_name = publication_info.get('name', 'Nature')
            custom_req = publication_info.get('custom_requirements', '')
            
            if pub_type == 'custom':
                requirements = self._parse_custom_requirements(custom_req)
            else:
                requirements = self.db_manager.get_publication_requirements(pub_type, pub_name)
                if not requirements:
                    requirements = self._get_default_requirements()
            
            # Process each uploaded file
            results = []
            for file_info in files:
                filename = file_info['filename']
                file_data = file_info['data']
                
                logger.info(f"Processing figure: {filename}")
                
                # Analyze the figure
                success, analysis_result = self.analyzer.analyze_figure(file_data, filename)
                
                if not success:
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': analysis_result,
                        'analysis': None,
                        'compliance': None,
                        'recommendations': []
                    })
                    continue
                
                # Check compliance
                compliance = self.compliance_checker.check_compliance(analysis_result, requirements)
                
                # Generate recommendations
                recommendations = self.recommendation_generator.generate_recommendations(
                    analysis_result, compliance, requirements
                )
                
                # Save to database
                try:
                    # Save file to disk
                    file_path = self._save_uploaded_file(file_data, filename, session_id)
                    
                    # Save to database
                    figure_id = self.db_manager.save_figure_upload(
                        session_id, filename, file_path, 
                        analysis_result.file_format, 
                        int(analysis_result.file_size_mb * 1024),
                        pub_type, pub_name
                    )
                    
                    # Save analysis results
                    self.db_manager.save_figure_analysis(figure_id, analysis_result, compliance, recommendations)
                    
                    results.append({
                        'filename': filename,
                        'success': True,
                        'figure_id': figure_id,
                        'analysis': asdict(analysis_result),
                        'compliance': asdict(compliance),
                        'recommendations': recommendations,
                        'file_path': str(file_path)
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to save figure {filename}: {e}")
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': f"Save failed: {str(e)}",
                        'analysis': asdict(analysis_result),
                        'compliance': asdict(compliance),
                        'recommendations': recommendations
                    })
            
            # Generate summary
            summary = self._generate_processing_summary(results, requirements)
            
            return {
                'success': True,
                'session_id': session_id,
                'publication': {
                    'type': pub_type,
                    'name': pub_name,
                    'requirements': requirements
                },
                'results': results,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Figure processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def get_session_figures(self, session_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get all figures for a session"""
        try:
            figures = self.db_manager.get_session_figures(session_id, limit)
            return {
                'success': True,
                'session_id': session_id,
                'figures': figures,
                'total_count': len(figures)
            }
        except Exception as e:
            logger.error(f"Failed to get session figures: {e}")
            return {
                'success': False,
                'error': str(e),
                'figures': []
            }
    
    def get_available_publications(self) -> Dict[str, List[str]]:
        """Get list of available publication types and names"""
        return {
            'journal': [
                'Nature', 'Science', 'Cell', 'The Lancet', 
                'New England Journal of Medicine'
            ],
            'conference': [
                'ACM CHI', 'IEEE ICCV', 'NeurIPS', 
                'American Medical Association'
            ],
            'thesis': [
                "Master's Thesis", 'PhD Thesis', 'Institution-Specific'
            ]
        }
    
    def get_publication_requirements(self, pub_type: str, pub_name: str) -> Dict[str, Any]:
        """Get detailed requirements for a specific publication"""
        requirements = self.db_manager.get_publication_requirements(pub_type, pub_name)
        if requirements:
            return requirements
        return self._get_default_requirements()
    
    def create_session(self) -> str:
        """Create a new processing session"""
        return self.db_manager.create_session()
    
    def _save_uploaded_file(self, file_data: bytes, filename: str, session_id: str) -> Path:
        """Save uploaded file to disk"""
        # Create session-specific directory
        session_dir = self.upload_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        file_path = session_dir / safe_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return file_path
    
    def _parse_custom_requirements(self, custom_text: str) -> Dict[str, Any]:
        """Parse custom requirements text into structured format"""
        # Basic parsing - could be enhanced with AI/NLP
        requirements = {
            'publication_type': 'custom',
            'publication_name': 'Custom Requirements',
            'category': 'Custom',
            'requirements': custom_text,
            'file_formats': 'PDF,PNG,TIFF',
            'min_dpi': 300,
            'color_mode': 'RGB',
            'max_file_size_mb': 50
        }
        
        # Extract specific requirements from text
        text_lower = custom_text.lower()
        
        # DPI requirements
        import re
        dpi_match = re.search(r'(\d+)\s*dpi', text_lower)
        if dpi_match:
            requirements['min_dpi'] = int(dpi_match.group(1))
        
        # File size requirements
        size_match = re.search(r'(\d+)\s*mb', text_lower)
        if size_match:
            requirements['max_file_size_mb'] = int(size_match.group(1))
        
        # Color mode
        if 'cmyk' in text_lower:
            requirements['color_mode'] = 'RGB/CMYK'
        elif 'grayscale' in text_lower:
            requirements['color_mode'] = 'RGB/Grayscale'
        
        # File formats
        formats = []
        if 'pdf' in text_lower:
            formats.append('PDF')
        if 'png' in text_lower:
            formats.append('PNG')
        if 'tiff' in text_lower or 'tif' in text_lower:
            formats.append('TIFF')
        if 'jpg' in text_lower or 'jpeg' in text_lower:
            formats.append('JPEG')
        
        if formats:
            requirements['file_formats'] = ','.join(formats)
        
        return requirements
    
    def _get_default_requirements(self) -> Dict[str, Any]:
        """Get default publication requirements"""
        return {
            'publication_type': 'journal',
            'publication_name': 'Generic Academic',
            'category': 'Academic',
            'requirements': 'Standard academic figure requirements: PDF/PNG/TIFF; ≥300 dpi; RGB; clear labeling.',
            'file_formats': 'PDF,PNG,TIFF',
            'min_dpi': 300,
            'color_mode': 'RGB',
            'max_file_size_mb': 25
        }
    
    def _generate_processing_summary(self, results: List[Dict], requirements: Dict) -> Dict[str, Any]:
        """Generate summary of processing results"""
        total_files = len(results)
        successful = len([r for r in results if r['success']])
        failed = total_files - successful
        
        # Compliance statistics
        compliant_files = 0
        avg_score = 0
        total_issues = 0
        issue_types = defaultdict(int)
        
        for result in results:
            if result['success'] and result['compliance']:
                compliance = result['compliance']
                if compliance['overall_compliant']:
                    compliant_files += 1
                avg_score += compliance['score']
                total_issues += len(compliance['issues'])
                
                # Categorize issues
                for issue in compliance['issues']:
                    if 'dpi' in issue.lower():
                        issue_types['DPI/Resolution'] += 1
                    elif 'format' in issue.lower():
                        issue_types['File Format'] += 1
                    elif 'size' in issue.lower():
                        issue_types['File Size'] += 1
                    elif 'dimension' in issue.lower() or 'width' in issue.lower():
                        issue_types['Dimensions'] += 1
                    else:
                        issue_types['Other'] += 1
        
        if successful > 0:
            avg_score = avg_score / successful
        
        return {
            'total_files': total_files,
            'successful_analyses': successful,
            'failed_analyses': failed,
            'compliant_files': compliant_files,
            'compliance_rate': (compliant_files / total_files * 100) if total_files > 0 else 0,
            'average_compliance_score': round(avg_score, 1),
            'total_issues': total_issues,
            'common_issue_types': dict(issue_types),
            'publication_info': {
                'type': requirements.get('publication_type'),
                'name': requirements.get('publication_name'),
                'requirements_summary': requirements.get('requirements', '')
            }
        }
    
    def generate_detailed_report(self, session_id: str) -> Dict[str, Any]:
        """Generate detailed report for all figures in a session"""
        try:
            figures_data = self.get_session_figures(session_id)
            
            if not figures_data['success']:
                return figures_data
            
            figures = figures_data['figures']
            
            # Aggregate statistics
            total_figures = len(figures)
            compliant_figures = len([f for f in figures if f.get('compliance_score', 0) >= 70])
            avg_compliance = sum([f.get('compliance_score', 0) for f in figures]) / total_figures if total_figures > 0 else 0
            
            # Publication breakdown
            publication_stats = defaultdict(int)
            for figure in figures:
                pub_name = figure.get('publication_name', 'Unknown')
                publication_stats[pub_name] += 1
            
            # Generate recommendations summary
            priority_recommendations = []
            if avg_compliance < 70:
                priority_recommendations.append({
                    'type': 'general',
                    'priority': 'high',
                    'title': 'Improve Overall Compliance',
                    'description': f'Average compliance score is {avg_compliance:.1f}%. Focus on addressing common issues across all figures.'
                })
            
            return {
                'success': True,
                'session_id': session_id,
                'report_generated': datetime.now().isoformat(),
                'statistics': {
                    'total_figures': total_figures,
                    'compliant_figures': compliant_figures,
                    'compliance_rate': (compliant_figures / total_figures * 100) if total_figures > 0 else 0,
                    'average_compliance_score': round(avg_compliance, 1),
                    'publication_breakdown': dict(publication_stats)
                },
                'figures': figures,
                'priority_recommendations': priority_recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report for session {session_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health and component status"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'capabilities': {
                'figure_analysis': True,
                'compliance_checking': True,
                'recommendation_generation': True,
                'database_storage': True,
                'file_upload': True
            }
        }
        
        # Check database connection
        try:
            test_session = self.db_manager.create_session()
            health_status['components']['database'] = {
                'status': 'healthy',
                'test_session_created': test_session is not None
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'error',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check file analyzer
        try:
            # Test with a small dummy image
            test_image_data = self._create_test_image()
            success, result = self.analyzer.analyze_figure(test_image_data, 'test.png')
            health_status['components']['analyzer'] = {
                'status': 'healthy' if success else 'error',
                'test_analysis_success': success
            }
        except Exception as e:
            health_status['components']['analyzer'] = {
                'status': 'error',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check upload directory
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            health_status['components']['file_storage'] = {
                'status': 'healthy',
                'upload_directory': str(self.upload_dir),
                'directory_writable': os.access(self.upload_dir, os.W_OK)
            }
        except Exception as e:
            health_status['components']['file_storage'] = {
                'status': 'error',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        return health_status
    
    def _create_test_image(self) -> bytes:
        """Create a small test image for health checking"""
        # Create a 100x100 test image
        img = Image.new('RGB', (100, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 90, 90], fill='blue', outline='black')
        draw.text((20, 40), 'TEST', fill='white')
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', dpi=(300, 300))
        return img_buffer.getvalue()


# Convenience functions for direct usage
def process_figures(session_id: str, files: List[Dict[str, Any]], publication_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Standalone function for processing figures
    Can be used directly by web frameworks
    """
    fixer = FigureFixer()
    return fixer.process_figure_submission(session_id, files, publication_info)


def get_publication_requirements(pub_type: str, pub_name: str) -> Dict[str, Any]:
    """Get requirements for a specific publication"""
    fixer = FigureFixer()
    return fixer.get_publication_requirements(pub_type, pub_name)


def create_processing_session() -> str:
    """Create a new processing session"""
    fixer = FigureFixer()
    return fixer.create_session()


# Flask integration helper
def create_flask_routes(app):
    """
    Create Flask routes for Figure Fixer
    Usage: create_flask_routes(app) in your Flask application
    """
    from flask import request, jsonify, session
    
    fixer = FigureFixer()
    
    @app.route('/api/figure-fixer/process', methods=['POST'])
    def process_figures_endpoint():
        """Process uploaded figures"""
        try:
            # Get or create session
            if 'session_id' not in session:
                session['session_id'] = fixer.create_session()
            
            session_id = session['session_id']
            
            # Extract form data
            pub_type = request.form.get('pubType', 'journal')
            pub_name = None
            
            if pub_type == 'journal':
                pub_name = request.form.get('journalChoice', 'Nature')
            elif pub_type == 'conference':
                pub_name = request.form.get('conferenceChoice', 'ACM CHI')
            elif pub_type == 'thesis':
                pub_name = request.form.get('thesisChoice', "Master's Thesis")
            elif pub_type == 'custom':
                pub_name = 'Custom Requirements'
            
            custom_requirements = request.form.get('customText', '')
            
            # Process uploaded files
            files = request.files.getlist('file')
            file_data_list = []
            
            for file in files:
                if file and file.filename:
                    file_data_list.append({
                        'filename': file.filename,
                        'data': file.read()
                    })
            
            if not file_data_list:
                return jsonify({
                    'success': False,
                    'error': 'No files uploaded'
                }), 400
            
            # Process the submission
            result = fixer.process_figure_submission(
                session_id,
                file_data_list,
                {
                    'type': pub_type,
                    'name': pub_name,
                    'custom_requirements': custom_requirements
                }
            )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Figure processing endpoint failed: {e}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500
    
    @app.route('/api/figure-fixer/publications', methods=['GET'])
    def get_publications():
        """Get available publications"""
        return jsonify({
            'success': True,
            'publications': fixer.get_available_publications()
        })
    
    @app.route('/api/figure-fixer/requirements/<pub_type>/<pub_name>', methods=['GET'])
    def get_requirements(pub_type, pub_name):
        """Get requirements for specific publication"""
        try:
            requirements = fixer.get_publication_requirements(pub_type, pub_name)
            return jsonify({
                'success': True,
                'requirements': requirements
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/figure-fixer/session-figures', methods=['GET'])
    def get_session_figures():
        """Get figures for current session"""
        if 'session_id' not in session:
            return jsonify({
                'success': True,
                'figures': [],
                'total_count': 0
            })
        
        result = fixer.get_session_figures(session['session_id'])
        return jsonify(result)
    
    @app.route('/api/figure-fixer/report', methods=['GET'])
    def get_detailed_report():
        """Generate detailed report for session"""
        if 'session_id' not in session:
            return jsonify({
                'success': False,
                'error': 'No active session'
            }), 400
        
        result = fixer.generate_detailed_report(session['session_id'])
        return jsonify(result)
    
    @app.route('/api/figure-fixer/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        health = fixer.health_check()
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code


if __name__ == "__main__":
    # Example usage and testing
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Run basic tests
        print("Testing Figure Fixer...")
        
        fixer = FigureFixer()
        
        # Test health check
        health = fixer.health_check()
        print(f"Health check: {health['status']}")
        
        # Test session creation
        session_id = fixer.create_session()
        print(f"Created session: {session_id}")
        
        # Test publication requirements
        requirements = fixer.get_publication_requirements('journal', 'Nature')
        print(f"Nature requirements: {requirements['requirements']}")
        
        print("Basic tests completed successfully!")
    
    else:
        print("Figure Fixer Backend Module")
        print("Usage:")
        print("  python figure_fixer.py test  - Run basic tests")
        print("  from figure_fixer import FigureFixer  - Import for use")
        print("  create_flask_routes(app)  - Add Flask routes")
        
        # Show available publications
        fixer = FigureFixer()
        pubs = fixer.get_available_publications()
        print("\nAvailable publications:")
        for pub_type, names in pubs.items():
            print(f"  {pub_type.title()}: {', '.join(names)}")
