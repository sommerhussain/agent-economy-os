import os

def print_tree(startpath, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', 'venv', '.venv', '__pycache__', '.pytest_cache', '.cursor', 'node_modules', 'agent-transcripts', 'terminals'}
    
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f.endswith('.pyc'): continue
            print(f"{subindent}{f}")

if __name__ == '__main__':
    print_tree('.')