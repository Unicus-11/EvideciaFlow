"""
Prompt Templates for Research Platform Features
Specialized prompts for academic writing and research analysis
"""

from typing import Dict, List, Any, Optional


class PromptTemplates:
    """Collection of prompt templates for research platform features"""
    
    def __init__(self):
        self.journal_requirements = {
            'Nature': {
                'style': 'concise, impactful, accessible to broad readership',
                'language': 'British English',
                'word_limits': {'abstract': 150, 'main_text': 3000},
                'voice': 'avoid first person (we, our), use active voice'
            },
            'Science': {
                'style': 'clear, significant findings emphasized',
                'language': 'American English', 
                'word_limits': {'abstract': 125, 'main_text': 2500},
                'voice': 'active voice, third person preferred'
            },
            'Cell': {
                'style': 'detailed methodology, clear significance',
                'language': 'American English',
                'word_limits': {'abstract': 150, 'main_text': 4000},
                'voice': 'active voice, detailed experimental procedures'
            },
            'The Lancet': {
                'style': 'clinical significance emphasized, patient impact',
                'language': 'British English',
                'word_limits': {'abstract': 300, 'main_text': 4500},
                'voice': 'first person acceptable, clinical focus'
            }
        }
    
    def get_rewrite_prompt(self, text: str, journal: str = 'Nature', language: str = 'American English') -> str:
        """Generate prompt for explain/rewrite feature"""
        
        journal_info = self.journal_requirements.get(journal, {
            'style': 'clear and academic',
            'language': language,
            'word_limits': {'abstract': 200, 'main_text': 4000},
            'voice': 'active voice preferred'
        })
        
        return f"""You are an expert academic writing assistant specialized in {journal} submissions.

TASK: Rewrite the following research text to meet {journal} publication standards.

TARGET JOURNAL: {journal}
LANGUAGE: {journal_info['language']}
STYLE REQUIREMENTS: {journal_info['style']}
VOICE: {journal_info['voice']}
WORD LIMITS: Abstract max {journal_info['word_limits']['abstract']} words, Main text max {journal_info['word_limits']['main_text']} words

ORIGINAL TEXT:
{text}

INSTRUCTIONS:
1. Rewrite the text maintaining all scientific accuracy and key findings
2. Follow {journal_info['language']} spelling and grammar conventions
3. Use {journal_info['voice']}
4. Ensure the writing style matches: {journal_info['style']}
5. Make the text more impactful and suitable for {journal} readership
6. Fix any grammatical, stylistic, or structural issues
7. Ensure proper academic tone and clarity

PROVIDE:
1. REWRITTEN TEXT: The improved version
2. KEY IMPROVEMENTS: List 3-5 specific changes made and why
3. COMPLIANCE CHECK: Confirm adherence to {journal} requirements

Format your response clearly with these three sections."""

    def get_protocol_optimization_prompt(self, protocol: str, field: str = 'general') -> str:
        """Generate prompt for protocol optimization feature"""
        
        return f"""You are an expert research methodology consultant specializing in {field} research protocols.

TASK: Analyze and optimize the following research protocol for scientific rigor, efficiency, and reproducibility.

RESEARCH FIELD: {field}
ORIGINAL PROTOCOL:
{protocol}

ANALYSIS REQUIREMENTS:
1. Scientific rigor and validity
2. Methodological soundness
3. Reproducibility and clarity
4. Efficiency and resource optimization
5. Potential risks and mitigation strategies
6. Ethical considerations
7. Statistical power and sample size considerations

PROVIDE:
1. OPTIMIZED PROTOCOL: Improved version with enhanced methodology
2. KEY IMPROVEMENTS: Specific changes made and scientific rationale
3. RISK ASSESSMENT: Potential issues and mitigation strategies
4. REPRODUCIBILITY CHECKLIST: Steps to ensure others can replicate
5. RESOURCE OPTIMIZATION: Ways to improve efficiency without compromising quality

Ensure all suggestions are evidence-based and follow current best practices in {field} research."""

    def get_figure_analysis_prompt(self, description: str, journal: str = 'Nature', specs: Dict = None) -> str:
        """Generate prompt for figure analysis feature"""
        
        current_specs = specs or {}
        
        return f"""You are an expert scientific figure consultant specializing in {journal} publication standards.

TASK: Analyze figure requirements and provide improvement recommendations.

TARGET JOURNAL: {journal}
FIGURE DESCRIPTION: {description}

CURRENT SPECIFICATIONS:
- DPI: {current_specs.get('dpi', 'unknown')}
- Format: {current_specs.get('format', 'unknown')}
- Color mode: {current_specs.get('color_mode', 'unknown')}
- Dimensions: {current_specs.get('dimensions', 'unknown')}

{journal} FIGURE REQUIREMENTS:
- Minimum 300 DPI for all figures
- Formats: PDF, PNG, or TIFF preferred
- Color mode: RGB for online, CMYK for print
- Clear legends and readable fonts
- Proper scaling and labeling
- High contrast and accessibility

PROVIDE:
1. COMPLIANCE ANALYSIS: Current figure vs {journal} requirements
2. ISSUES IDENTIFIED: Specific problems found
3. RECOMMENDATIONS: Step-by-step improvements needed
4. TECHNICAL SPECIFICATIONS: Exact DPI, format, color settings required
5. ACCESSIBILITY CHECK: Ensure figure is readable and accessible

Focus on practical, actionable improvements that will ensure acceptance by {journal}."""

    def get_citation_analysis_prompt(self, text: str, style: str = 'APA') -> str:
        """Generate prompt for citation context analysis"""
        
        return f"""You are an expert academic citation analyst specializing in {style} citation style.

TASK: Analyze citations in the text for accuracy, context, and completeness.

CITATION STYLE: {style}
TEXT TO ANALYZE:
{text}

ANALYSIS REQUIREMENTS:
1. Citation format accuracy (according to {style} style)
2. Citation context appropriateness
3. Missing citations for claims made
4. Over-citation or citation padding
5. Primary vs secondary source usage
6. Recency and relevance of sources
7. Bias in source selection

PROVIDE:
1. CITATIONS FOUND: List all citations with format assessment
2. CONTEXT ANALYSIS: How well citations support the claims
3. MISSING CITATIONS: Claims that need citation support
4. STYLE ISSUES: Format corrections needed for {style}
5. SOURCE QUALITY: Assessment of citation appropriateness
6. RECOMMENDATIONS: Specific improvements needed

Ensure all suggestions follow current {style} guidelines and academic best practices."""

    def get_idea_recombination_prompt(self, sources: List[str], question: str = '') -> str:
        """Generate prompt for idea recombination feature"""
        
        sources_text = '\n\n'.join([f"SOURCE {i+1}:\n{source}" for i, source in enumerate(sources)])
        
        return f"""You are an expert research innovation consultant specializing in interdisciplinary idea synthesis.

TASK: Analyze multiple research sources and generate novel research ideas through creative recombination.

RESEARCH QUESTION/FOCUS: {question if question else 'Open exploration'}

SOURCES TO ANALYZE:
{sources_text}

SYNTHESIS REQUIREMENTS:
1. Identify key concepts, methods, and findings from each source
2. Find unexpected connections between different sources
3. Generate novel research ideas combining insights
4. Suggest innovative methodological approaches
5. Identify research gaps and opportunities
6. Propose interdisciplinary collaboration possibilities

PROVIDE:
1. NOVEL IDEAS: 3-5 innovative research concepts combining insights from sources
2. METHODOLOGICAL COMBINATIONS: New approaches mixing different methodologies
3. RESEARCH GAPS: Unexplored areas identified through synthesis
4. COLLABORATION OPPORTUNITIES: Interdisciplinary partnerships suggested
5. FEASIBILITY ASSESSMENT: Practical considerations for each idea
6. NEXT STEPS: Specific actions to pursue the most promising ideas

Focus on creative, feasible ideas that advance knowledge through innovative combinations."""

    def get_contradiction_detection_prompt(self, text: str, check_type: str = 'internal') -> str:
        """Generate prompt for contradiction detection feature"""
        
        check_instructions = {
            'internal': 'Focus on internal logical consistency within the text',
            'external': 'Compare claims against established scientific knowledge',
            'methodological': 'Analyze methodology for internal contradictions'
        }
        
        return f"""You are an expert logical analysis consultant specializing in scientific reasoning.

TASK: Detect contradictions and logical inconsistencies in research text.

ANALYSIS TYPE: {check_type} - {check_instructions.get(check_type, 'General analysis')}

TEXT TO ANALYZE:
{text}

ANALYSIS REQUIREMENTS:
1. Logical contradictions (A contradicts B within the text)
2. Methodological inconsistencies
3. Statistical or mathematical errors
4. Claims unsupported by presented evidence
5. Inconsistent terminology or definitions
6. Temporal or causal logic problems
7. Data interpretation inconsistencies

PROVIDE:
1. CONTRADICTIONS FOUND: Specific logical conflicts identified
2. LOGICAL ISSUES: Problems with reasoning or argumentation
3. CONSISTENCY SCORE: Overall consistency rating (1-10) with explanation
4. EVIDENCE GAPS: Claims lacking adequate support
5. RECOMMENDATIONS: How to resolve identified contradictions
6. STRENGTHENING SUGGESTIONS: Ways to improve logical coherence

Provide specific quotes and page references where contradictions occur."""

    def get_system_prompts(self) -> Dict[str, str]:
        """Get system prompts for different AI models/contexts"""
        
        return {
            'academic_expert': """You are a world-class academic writing and research expert with decades of experience in scientific publishing. You understand the nuances of different journals, citation styles, and academic writing conventions. Your responses are always evidence-based, precise, and helpful for researchers at all levels.""",
            
            'methodology_expert': """You are an expert research methodologist with extensive experience in experimental design, statistical analysis, and protocol optimization across multiple scientific disciplines. You prioritize scientific rigor, reproducibility, and ethical considerations in all recommendations.""",
            
            'figure_specialist': """You are a scientific figure and visualization expert who understands the technical requirements of major academic publishers. You combine technical knowledge of image specifications with design principles to create clear, impactful scientific communications.""",
            
            'citation_analyst': """You are a library science and academic citation expert with comprehensive knowledge of all major citation styles and academic publishing standards. You understand both the technical formatting requirements and the scholarly principles underlying proper attribution.""",
            
            'innovation_consultant': """You are a creative research strategist who excels at finding unexpected connections between different fields and generating novel research ideas. You combine deep analytical thinking with creative synthesis to identify breakthrough research opportunities.""",
            
            'logic_analyst': """You are an expert in logical reasoning, argumentation, and scientific methodology. You have a keen eye for identifying logical fallacies, inconsistencies, and gaps in reasoning within academic texts. Your analysis is thorough and constructive."""
        }

    def get_feature_system_prompt(self, feature: str) -> str:
        """Get appropriate system prompt for specific feature"""
        
        feature_prompts = {
            'explain_rewrite': 'academic_expert',
            'protocol_optimizer': 'methodology_expert', 
            'figure_fixer': 'figure_specialist',
            'citation_context': 'citation_analyst',
            'idea_recombinator': 'innovation_consultant',
            'contradiction_detector': 'logic_analyst'
        }
        
        system_prompts = self.get_system_prompts()
        prompt_key = feature_prompts.get(feature, 'academic_expert')
        return system_prompts[prompt_key]

    def get_journal_specific_notes(self, journal: str) -> Dict[str, str]:
        """Get journal-specific writing guidelines"""
        
        journal_notes = {
            'Nature': {
                'abstract_structure': 'Background, Methods, Results, Conclusions',
                'special_requirements': 'Significance statement required, accessible to broad readership',
                'formatting': 'British spelling, avoid first person, line numbers required'
            },
            'Science': {
                'abstract_structure': 'One paragraph structured summary',
                'special_requirements': 'One-sentence summary (125 characters max)',
                'formatting': 'American spelling, broader significance emphasized'
            },
            'Cell': {
                'abstract_structure': 'Summary format',
                'special_requirements': 'Significance statement (120 words), graphical abstract required',
                'formatting': 'American spelling, maximum 8 main figures'
            },
            'The Lancet': {
                'abstract_structure': 'Background, Methods, Findings, Interpretation',
                'special_requirements': 'Research in context panel, ethics approval statement',
                'formatting': 'British spelling, first person acceptable'
            }
        }
        
        return journal_notes.get(journal, {
            'abstract_structure': 'Standard IMRAD format',
            'special_requirements': 'Follow journal-specific guidelines',
            'formatting': 'Check journal website for specific requirements'
        })
