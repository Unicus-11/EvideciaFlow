# EvidenciaFlow - AI-Powered Research Platform 🧬📊

**Transform your academic research with AI-powered tools designed for scholars, researchers, and students.**

EvidenciaFlow is a comprehensive platform offering 6 specialized AI features to enhance research papers, optimize protocols, analyze citations, and detect inconsistencies in academic work.

## ✨ Features

### 🔄 **Explain/Rewrite** 
- Rewrite research papers for specific journals
- Journal-specific formatting and style requirements
- Academic tone optimization
- Word limit compliance

### 📊 **Figure Fixer**
- Analyze figures for publication compliance
- DPI, format, and size optimization  
- Publication-specific figure requirements
- Automated figure enhancement

### 🧪 **Protocol Optimizer**
- Improve research methodologies
- Protocol clarity and reproducibility
- Best practice recommendations
- Method validation suggestions

### 📚 **Citation Context**
- Analyze citation usage and context
- Improve citation relevance and accuracy
- Citation style compliance (APA, IEEE, Nature, etc.)
- Reference quality assessment

### 💡 **Idea Recombinator** 
- Synthesize novel research ideas
- Cross-disciplinary connections
- Literature gap identification
- Research direction suggestions

### 🔍 **Contradiction Detector**
- Find logical inconsistencies in papers
- Methodology vs. results alignment
- Internal consistency analysis
- Argument flow validation


## 🛠️ Technology Stack

- **AI Engine**: Groq API with Llama 3 models (70B/8B)
- **Backend**: Python Flask
- **Database**: SQLite 
- **File Processing**: PIL, PyPDF2, python-docx
- **Frontend**: HTML5, CSS3, JavaScript
- **Rate Limiting**: Built-in Groq API management

## 📁 Project Structure

```
EvidenciaFlow/
├── app.py                      # Flask application entry point
├── ai/                         # AI integration layer
│   ├── ai_manager.py          # Central AI routing system
│   ├── groq_client.py         # Groq API client with rate limiting
│   ├── prompt_templates.py    # Academic-specific prompts
│   └── response_parser.py     # AI response processing
├── backend/                   # Feature implementations
│   ├── citation_context.py   # Citation analysis handler
│   ├── contradiction_detector.py # Logic inconsistency detection
│   ├── explain_rewrite.py     # Paper rewriting handler
│   ├── figure_fixer.py        # Figure compliance checker
│   ├── idea_recombinator.py   # Research idea synthesis
│   ├── protocol_optimizer.py  # Protocol improvement
│   └── utils/
│       ├── database_helper.py # Database operations manager
│       └── file_processor.py  # File upload and processing
├── database/                  # SQLite databases
│   ├── figures.db            # Figure analysis data
│   ├── journal_requirements.db # Publication requirements
│   ├── knowledge_base.db     # Research knowledge base
│   ├── protocols.db          # Protocol optimization data
│   ├── references.db         # Citation and reference data
│   ├── research_paper_content.db # Paper content analysis
│   └── users.db              # User preferences and history
└── templates/                # Frontend HTML templates
    ├── citation_context.html
    ├── contradiction_detector.html
    ├── explain_rewrite.html
    ├── figure_fixer.html
    ├── idea_recombinator.html
    └── protocol_optimizer.html
```

## 🔧 Configuration


### Database Configuration
The platform uses SQLite databases for:
- **Journal requirements** 
- **Figure analysis results**
- **Citation and reference data**
- **Protocol optimization history**
- **Knowledge base for idea generation**

## 💡 Usage Examples

### Rewrite Paper for Nature Journal
```python
# Upload your paper
# Select "Nature" as target journal
# AI analyzes word limits, citation style, formatting requirements
# Returns journal-compliant rewritten version
```

### Fix Figure for IEEE Publication
```python
# Upload figure (PNG, JPG, PDF)
# Select "IEEE" as target publication
# AI checks DPI, format, size compliance
# Returns optimized figure meeting IEEE standards
```

### Detect Contradictions in Research Paper
```python
# Upload research paper (PDF, DOCX)
# AI analyzes methodology vs results
# Identifies logical inconsistencies
# Provides specific recommendations for fixes
```

## 🐛 Troubleshooting

### Common Issues

**"Groq API rate limit exceeded"**
```bash
# Solution: Wait 1 minute or upgrade API plan
# Free tier: 30 requests/minute
```

**"Database not found"**
```bash
# Solution: Initialize databases
python -c "from backend.utils.database_helper import DatabaseHelper; DatabaseHelper.initialize_all_databases()"
```

**"File upload failed"**
```bash
# Check file size (max 10MB)
# Supported formats: PDF, DOCX, PNG, JPG
```

**"AI analysis taking too long"**
```bash
# Large papers may take 30-60 seconds
# Check your internet connection
# Verify Groq API key is valid
```



##  Acknowledgments

- **Groq** for fast AI inference
- **Llama 3** models for academic writing capabilities
- **Flask** community for web framework
- **Academic community** for feedback and testing

##  Support

- **Email**: mandukya8@gmail.com

## ⭐ Star History

If EvidenciaFlow helps your research, consider giving us a star! ⭐

---

**Built with ❤️ for the academic community**

*Transform your research. Elevate your papers. Accelerate discovery.*
