from backend.paper_analyzer import PaperAnalyzer
from ai.ai_manager import AIManager
from pathlib import Path
from pprint import pprint

# Initialize AI Manager and PaperAnalyzer
ai_manager = AIManager()
analyzer = PaperAnalyzer(ai_manager=ai_manager)

# Load the sample file
sample_file_path = Path("test_files/sample_paper.txt")

# Read file inside the with block
with open(sample_file_path, "rb") as f:
    file_content = f.read()

# Create mock file object
class MockFile:
    def __init__(self, content, filename):
        self.content = content
        self.filename = filename
    def read(self):
        return self.content

mock_file = MockFile(file_content, sample_file_path.name)

# Run analysis
result = analyzer.analyze_paper(mock_file, user_id="demo_user")

# Print full output
print("\n--- ANALYSIS OUTPUT ---")
pprint(result)
