import sys
import os
import json
import subprocess
import threading
import pyautogui
import cv2
import numpy as np
from PIL import Image, ImageGrab
import pytesseract
import git
from pathlib import Path
import re
from typing import Dict, List, Optional
import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqGeneration

class CodeAnalyzer:
    """Analyze and understand code across different languages"""
    def __init__(self):
        self.language_patterns = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx', '.ts', '.tsx'],
            'java': ['.java'],
            'cpp': ['.cpp', '.hpp', '.cc', '.h'],
            'rust': ['.rs'],
            'go': ['.go'],
            'ruby': ['.rb'],
            'php': ['.php'],
            'csharp': ['.cs'],
            'swift': ['.swift']
        }
        self.setup_language_detectors()
        
    def setup_language_detectors(self):
        """Initialize language-specific tokenizers and parsers"""
        self.tokenizers = {}
        for lang in self.language_patterns.keys():
            try:
                self.tokenizers[lang] = AutoTokenizer.from_pretrained(f"microsoft/codebert-{lang}")
            except:
                logging.warning(f"Could not load tokenizer for {lang}")

    def detect_language(self, code: str) -> str:
        """Detect programming language from code snippet"""
        # Use heuristics and token analysis to identify language
        patterns = {
            'python': r'import\s+|def\s+|class\s+|if\s+__name__\s*==\s*[\'"]__main__[\'"]',
            'javascript': r'const\s+|let\s+|function\s+|=>|import\s+from|export\s+',
            'java': r'public\s+class|private\s+|protected\s+|import\s+java\.',
            'cpp': r'#include\s+<|std::|namespace\s+|template\s*<',
            'rust': r'fn\s+main|let\s+mut|impl\s+|use\s+std::',
            'go': r'package\s+main|func\s+|import\s+\(|type\s+struct',
        }
        
        matches = {}
        for lang, pattern in patterns.items():
            matches[lang] = len(re.findall(pattern, code))
            
        if not any(matches.values()):
            return 'unknown'
            
        return max(matches.items(), key=lambda x: x[1])[0]

    def parse_code(self, code: str, language: Optional[str] = None) -> Dict:
        """Parse code structure and extract key components"""
        if not language:
            language = self.detect_language(code)
            
        structure = {
            'language': language,
            'imports': [],
            'classes': [],
            'functions': [],
            'variables': [],
            'dependencies': []
        }
        
        # Extract imports and dependencies
        if language == 'python':
            structure['imports'] = re.findall(r'import\s+(\w+)|from\s+(\w+)\s+import', code)
        elif language == 'javascript':
            structure['imports'] = re.findall(r'import\s+{\s*([^}]+)}\s+from|require\([\'"]([^\'"]+)[\'"]\)', code)
            
        # Extract classes and functions
        structure['classes'] = self.extract_classes(code, language)
        structure['functions'] = self.extract_functions(code, language)
        
        return structure

    def extract_classes(self, code: str, language: str) -> List[Dict]:
        """Extract class definitions and their methods"""
        classes = []
        
        if language == 'python':
            class_matches = re.finditer(r'class\s+(\w+)(?:\([^)]*\))?\s*:', code)
            for match in class_matches:
                class_name = match.group(1)
                class_start = match.start()
                # Find class body using indentation
                class_body = self.extract_indented_block(code[class_start:])
                classes.append({
                    'name': class_name,
                    'methods': self.extract_functions(class_body, language)
                })
                
        elif language in ['java', 'cpp']:
            class_pattern = r'(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[^{]+)?{'
            class_matches = re.finditer(class_pattern, code)
            for match in class_matches:
                class_name = match.group(1)
                class_start = match.start()
                class_body = self.extract_bracketed_block(code[class_start:])
                classes.append({
                    'name': class_name,
                    'methods': self.extract_functions(class_body, language)
                })
                
        return classes

    def extract_functions(self, code: str, language: str) -> List[Dict]:
        """Extract function definitions and their parameters"""
        functions = []
        
        if language == 'python':
            func_pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->?\s*[^:]+)?:'
        elif language == 'javascript':
            func_pattern = r'(?:function\s+(\w+)\s*\(([^)]*)\)|const\s+(\w+)\s*=\s*(?:\([^)]*\)|\w+)\s*=>)'
        else:
            func_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?[\w<>[\]]+\s+(\w+)\s*\(([^)]*)\)'
            
        func_matches = re.finditer(func_pattern, code)
        for match in func_matches:
            func_name = match.group(1)
            params = match.group(2) if len(match.groups()) > 1 else ''
            
            functions.append({
                'name': func_name,
                'parameters': [p.strip() for p in params.split(',') if p.strip()],
                'return_type': self.infer_return_type(code, func_name, language)
            })
            
        return functions

    def infer_return_type(self, code: str, func_name: str, language: str) -> str:
        """Attempt to infer function return type through static analysis"""
        if language == 'python':
            # Look for return type hints
            type_hint_pattern = f'def\s+{func_name}\s*\([^)]*\)\s*->\s*([^:]+):'
            match = re.search(type_hint_pattern, code)
            if match:
                return match.group(1).strip()
                
            # Analyze return statements
            func_body = self.extract_function_body(code, func_name)
            if func_body:
                return_values = re.findall(r'return\s+(.+)(?:\n|$)', func_body)
                if return_values:
                    # Basic type inference from return values
                    return self.infer_python_type(return_values[0])
                    
        return 'unknown'

    def extract_function_body(self, code: str, func_name: str) -> Optional[str]:
        """Extract the body of a function for analysis"""
        if func_name in code:
            start_idx = code.find(f'def {func_name}')
            if start_idx != -1:
                # Find the end of the function definition line
                def_end = code.find(':', start_idx) + 1
                # Extract indented block
                return self.extract_indented_block(code[def_end:])
        return None

class ScreenInteractor:
    """Handle screen interaction and OCR capabilities"""
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust path as needed
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
    def capture_screen(self, region=None) -> Image:
        """Capture full screen or specific region"""
        return ImageGrab.grab(bbox=region)
        
    def find_on_screen(self, template_path: str, confidence: float = 0.8) -> Optional[tuple]:
        """Find template image on screen"""
        screen = np.array(self.capture_screen())
        template = cv2.imread(template_path)
        
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            return max_loc
        return None
        
    def extract_text(self, region=None) -> str:
        """Extract text from screen region using OCR"""
        screenshot = self.capture_screen(region)
        return pytesseract.image_to_string(screenshot)
        
    def click_element(self, template_path: str):
        """Find and click on screen element"""
        location = self.find_on_screen(template_path)
        if location:
            x, y = location
            pyautogui.click(x + 10, y + 10)  # Offset to click center
            return True
        return False

class CodeGenerator:
    """Generate code across different programming languages"""
    def __init__(self):
        self.model = AutoModelForSeq2SeqGeneration.from_pretrained("microsoft/codebert-base")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.load_templates()
        
    def load_templates(self):
        """Load code templates for different languages"""
        self.templates = {}
        templates_dir = Path("templates")
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.json"):
                with open(template_file, 'r') as f:
                    self.templates[template_file.stem] = json.load(f)
                    
    def generate_code(self, description: str, language: str) -> str:
        """Generate code based on natural language description"""
        # Prepare input
        input_ids = self.tokenizer.encode(
            f"Generate {language} code: {description}",
            return_tensors="pt"
        )
        
        # Generate code
        outputs = self.model.generate(
            input_ids,
            max_length=512,
            num_return_sequences=1,
            temperature=0.7
        )
        
        generated_code = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Apply language-specific formatting
        return self.format_code(generated_code, language)
        
    def format_code(self, code: str, language: str) -> str:
        """Format generated code according to language conventions"""
        try:
            if language == 'python':
                import black
                return black.format_str(code, mode=black.FileMode())
            elif language == 'javascript':
                import jsbeautifier
                return jsbeautifier.beautify(code)
        except:
            return code  # Return unformatted if formatter unavailable

class BobAI:
    """Main BOB AI class integrating all components"""
    def __init__(self):
        self.code_analyzer = CodeAnalyzer()
        self.screen_interactor = ScreenInteractor()
        self.code_generator = CodeGenerator()
        self.init_logging()
        
    def init_logging(self):
        """Initialize logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bob_ai.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def learn_from_repository(self, repo_url: str):
        """Clone and analyze repository for learning"""
        try:
            # Clone repository
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = Path(f"repositories/{repo_name}")
            
            if not repo_path.exists():
                git.Repo.clone_from(repo_url, repo_path)
                
            # Analyze all code files
            for ext in [ext for patterns in self.code_analyzer.language_patterns.values() for ext in patterns]:
                for file_path in repo_path.glob(f"**/*{ext}"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            code = f.read()
                            analysis = self.code_analyzer.parse_code(code)
                            self.logger.info(f"Analyzed {file_path}: {len(analysis['functions'])} functions, {len(analysis['classes'])} classes")
                        except Exception as e:
                            self.logger.error(f"Error analyzing {file_path}: {str(e)}")
                            
        except Exception as e:
            self.logger.error(f"Error processing repository {repo_url}: {str(e)}")
            
    def generate_script(self, description: str, language: str) -> str:
        """Generate complete script based on description"""
        return self.code_generator.generate_code(description, language)
        
    def interact_with_screen(self, action: str, target: Optional[str] = None):
        """Interact with screen based on action type"""
        if action == 'capture':
            return self.screen_interactor.capture_screen()
        elif action == 'find':
            return self.screen_interactor.find_on_screen(target)
        elif action == 'click':
            return self.screen_interactor.click_element(target)
        elif action == 'read':
            return self.screen_interactor.extract_text()
            
    def execute_code(self, code: str, language: str) -> str:
        """Execute code in specified language"""
        try:
            if language == 'python':
                result = subprocess.run(
                    [sys.executable, '-c', code],
                    capture_output=True,
                    text=True
                )
                return result.stdout if result.returncode == 0 else result.stderr
                
            elif language == 'javascript':
                with open('temp.js', 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['node', 'temp.js'],
                    capture_output=True,
                    text=True
                )
                os.remove('temp.js')
                return result.stdout if result.returncode == 0 else result.stderr
                
            # Add support for other languages as needed
                
        except Exception as e:
            return f"Execution error: {str(e)}"

def main():
    bob = BobAI()
    
    # Example usage
    print("