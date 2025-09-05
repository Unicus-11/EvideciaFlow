import sys
import os

# Make sure Python can find your backend package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.idea_recombinator import IdeaRecombinator

# Dummy test
if __name__ == "__main__":
    recombinator = IdeaRecombinator()
    print("IdeaRecombinator instance created successfully!")

    # Example: call a method if it exists (replace with your actual method)
    try:
        # Replace with the actual method you want to test
        result = recombinator.generate_ideas(["machine learning", "healthcare"], 3)
        print("Generated ideas:", result)
    except AttributeError:
        print("No generate_ideas method yet — instance works!")
