import os

def check_file_for_null_bytes(file_path):
    """Check if a file contains null bytes."""
    with open(file_path, 'rb') as f:
        content = f.read()
        null_positions = [i for i, byte in enumerate(content) if byte == 0]
        return null_positions

def main():
    """Check all Python files in the race_coach directory for null bytes."""
    base_dir = os.path.join('trackpro', 'race_coach')
    
    for filename in os.listdir(base_dir):
        if filename.endswith('.py'):
            file_path = os.path.join(base_dir, filename)
            null_positions = check_file_for_null_bytes(file_path)
            
            if null_positions:
                print(f"Found {len(null_positions)} null bytes in {file_path} at positions: {null_positions[:10]} {'...' if len(null_positions) > 10 else ''}")
            else:
                print(f"No null bytes found in {file_path}")

if __name__ == "__main__":
    main() 