import os

for root, dirs, files in os.walk("."):
    print(root)
    for file in files:
        print("   ", file)
