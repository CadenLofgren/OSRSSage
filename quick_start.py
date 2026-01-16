"""
Quick Start Script
Helps set up and verify the OSRS Wiki RAG system.
"""

import sys
from pathlib import Path
import subprocess

def check_python_version():
    """Check if Python version is 3.8+."""
    if sys.version_info < (3, 8):
        print("[X] Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'requests', 'beautifulsoup4', 'yaml', 'chromadb', 
        'sentence_transformers', 'ollama', 'streamlit'
    ]
    
    missing = []
    for package in required_packages:
            try:
                if package == 'yaml':
                    __import__('yaml')
                elif package == 'beautifulsoup4':
                    __import__('bs4')
                elif package == 'sentence_transformers':
                    __import__('sentence_transformers')
                else:
                    __import__(package)
                print(f"[OK] {package}")
            except ImportError:
                print(f"[X] {package} (not installed)")
                missing.append(package)
    
    if missing:
        print(f"\nInstall missing packages with: pip install {' '.join(missing)}")
        return False
    return True

def check_ollama():
    """Check if Ollama is running and has the model."""
    try:
        import ollama
        client = ollama.Client()
        
        # Check if Ollama is accessible
        models_response = client.list()
        
        # Handle different response formats
        if isinstance(models_response, dict):
            models_list = models_response.get('models', [])
        elif hasattr(models_response, 'models'):
            models_list = models_response.models
        else:
            models_list = models_response if isinstance(models_response, list) else []
        
        # Extract model names - handle different structures
        model_names = []
        for m in models_list:
            if hasattr(m, 'model'):  # Model object with .model attribute
                name = m.model
            elif hasattr(m, 'name'):  # Model object with .name attribute
                name = m.name
            elif isinstance(m, dict):
                # Try different possible keys
                name = m.get('name') or m.get('model') or str(m)
            else:
                name = str(m)
            model_names.append(name)
        
        print(f"[OK] Ollama is running")
        print(f"  Available models: {', '.join(model_names) if model_names else 'None'}")
        
        # Check for Qwen 2.5 14B
        qwen_models = [m for m in model_names if 'qwen2.5' in m.lower() and '14b' in m.lower()]
        if qwen_models:
            print(f"[OK] Qwen 2.5 14B found: {qwen_models[0]}")
            return True
        else:
            print("[!] Qwen 2.5 14B not found. Install with: ollama pull qwen2.5:14b")
            return False
            
    except Exception as e:
        print(f"[X] Ollama check failed: {e}")
        print("  Make sure Ollama is installed and running")
        return False

def check_directories():
    """Create necessary directories."""
    directories = [
        "data/raw",
        "data/processed",
        "data/vector_db",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("[OK] Directories created")
    return True

def check_config():
    """Check if config file exists."""
    if Path("config.yaml").exists():
        print("[OK] config.yaml exists")
        return True
    else:
        print("[X] config.yaml not found")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("OSRS Wiki RAG System - Quick Start Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Configuration", check_config),
        ("Ollama", check_ollama),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("[SUCCESS] All checks passed! You're ready to start.")
        print("\nNext steps:")
        print("1. python scrape_wiki.py")
        print("2. python process_data.py")
        print("3. python create_vector_db.py")
        print("4. python cli_interface.py  OR  streamlit run streamlit_ui.py")
    else:
        print("[WARNING] Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
