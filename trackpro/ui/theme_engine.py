"""Theme engine for processing SCSS variables and generating QSS stylesheets.

This module provides functionality to read SCSS variable files and process
SCSS-style stylesheets into Qt-compatible QSS stylesheets.
"""

import re
from pathlib import Path
from typing import Dict, Optional, Any
from .icon_manager import IconManager, process_qss_for_icons


class ThemeEngine:
    """Engine for processing themes and generating QSS stylesheets."""
    
    def __init__(self, ui_resources_path: str):
        """Initialize the theme engine.
        
        Args:
            ui_resources_path: Path to the ui_resources directory
        """
        self.ui_resources_path = Path(ui_resources_path)
        self.qss_path = self.ui_resources_path / "Qss"
        self.scss_path = self.qss_path / "scss"
        self.variables: Dict[str, str] = {}
        self.icon_manager: Optional[IconManager] = None
        
    def set_icon_manager(self, icon_manager: IconManager):
        """Set the icon manager for processing icon paths.
        
        Args:
            icon_manager: IconManager instance
        """
        self.icon_manager = icon_manager
        
    def load_variables(self, variables_file: str = "_variables.scss") -> bool:
        """Load SCSS variables from file.
        
        Args:
            variables_file: Name of the variables file
            
        Returns:
            True if variables loaded successfully
        """
        variables_path = self.scss_path / variables_file
        
        if not variables_path.exists():
            print(f"Variables file not found: {variables_path}")
            return False
            
        try:
            with open(variables_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse SCSS variables
            self.variables = self._parse_scss_variables(content)
            return True
            
        except Exception as e:
            print(f"Error loading variables: {e}")
            return False
            
    def _parse_scss_variables(self, content: str) -> Dict[str, str]:
        """Parse SCSS variables from content.
        
        Args:
            content: SCSS file content
            
        Returns:
            Dictionary of variable names to values
        """
        variables = {}
        
        # Match SCSS variable declarations: $VARIABLE_NAME: value;
        pattern = r'\$([A-Z_][A-Z0-9_]*)\s*:\s*([^;]+);'
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            
            # Remove quotes if present
            if var_value.startswith('"') and var_value.endswith('"'):
                var_value = var_value[1:-1]
            elif var_value.startswith("'") and var_value.endswith("'"):
                var_value = var_value[1:-1]
                
            variables[var_name] = var_value
            
        return variables
        
    def process_scss_to_qss(self, scss_file: str) -> Optional[str]:
        """Process SCSS file to QSS stylesheet.
        
        Args:
            scss_file: Name of the SCSS file to process
            
        Returns:
            Processed QSS content or None if failed
        """
        scss_path = self.scss_path / scss_file
        
        if not scss_path.exists():
            print(f"SCSS file not found: {scss_path}")
            return None
            
        try:
            with open(scss_path, 'r', encoding='utf-8') as f:
                scss_content = f.read()
                
            # Process the SCSS content
            qss_content = self._process_scss_content(scss_content)
            
            # Process icon paths if icon manager is available
            if self.icon_manager:
                qss_content = process_qss_for_icons(qss_content, self.icon_manager)
                
            return qss_content
            
        except Exception as e:
            print(f"Error processing SCSS file: {e}")
            return None
            
    def _process_scss_content(self, content: str) -> str:
        """Process SCSS content to QSS.
        
        Args:
            content: Raw SCSS content
            
        Returns:
            Processed QSS content
        """
        # Start with the original content
        processed = content
        
        # Replace SCSS variables with their values
        processed = self._replace_variables(processed)
        
        # Remove SCSS-specific syntax that isn't needed
        processed = self._clean_scss_syntax(processed)
        
        return processed
        
    def _replace_variables(self, content: str) -> str:
        """Replace SCSS variables with their values.
        
        Args:
            content: Content with SCSS variables
            
        Returns:
            Content with variables replaced
        """
        processed = content
        
        # Replace variables in order (longer names first to avoid partial matches)
        sorted_vars = sorted(self.variables.keys(), key=len, reverse=True)
        
        for var_name in sorted_vars:
            var_value = self.variables[var_name]
            
            # Replace $VARIABLE_NAME with the actual value
            pattern = r'\$' + re.escape(var_name) + r'\b'
            processed = re.sub(pattern, var_value, processed)
            
        return processed
        
    def _clean_scss_syntax(self, content: str) -> str:
        """Clean SCSS-specific syntax.
        
        Args:
            content: SCSS content
            
        Returns:
            Cleaned content
        """
        processed = content
        
        # Remove SCSS variable declarations (they've already been processed)
        processed = re.sub(r'\$[A-Z_][A-Z0-9_]*\s*:\s*[^;]+;\s*\n?', '', processed, flags=re.MULTILINE)
        
        # Remove SCSS comments starting with //
        processed = re.sub(r'//.*$', '', processed, flags=re.MULTILINE)
        
        # Remove file header comments
        processed = re.sub(r'/\*[\s\S]*?\*/', '', processed)
        
        # Convert SCSS nested selectors to QSS format (basic conversion)
        processed = self._convert_nested_selectors(processed)
        
        # Clean up excessive whitespace
        processed = re.sub(r'\n\s*\n\s*\n', '\n\n', processed)
        processed = re.sub(r'^\s*\n', '', processed, flags=re.MULTILINE)
        
        return processed
        
    def _convert_nested_selectors(self, content: str) -> str:
        """Convert SCSS nested selectors to flat QSS selectors.
        
        This is a basic implementation that handles simple nesting.
        
        Args:
            content: SCSS content with nested selectors
            
        Returns:
            Content with flattened selectors
        """
        # This is a simplified implementation
        # For production use, you might want to use a proper SCSS processor
        
        # Handle basic & references
        content = re.sub(r'&:([a-zA-Z-]+)', r':\1', content)
        content = re.sub(r'&::([a-zA-Z-]+)', r'::\1', content)
        content = re.sub(r'&\[([^\]]+)\]', r'[\1]', content)
        
        return content
        
    def generate_qss_from_main(self, main_scss: str = "main.scss") -> Optional[str]:
        """Generate complete QSS from main SCSS file.
        
        Args:
            main_scss: Main SCSS file that imports others
            
        Returns:
            Complete QSS stylesheet or None if failed
        """
        # First, make sure variables are loaded
        if not self.variables:
            if not self.load_variables():
                return None
                
        # Process the main SCSS file
        return self.process_scss_to_qss(main_scss)
        
    def get_precompiled_css(self) -> Optional[str]:
        """Get precompiled CSS from generated-files.
        
        Returns:
            CSS content or None if not found
        """
        css_path = self.ui_resources_path / "generated-files" / "css" / "main.css"
        
        if not css_path.exists():
            return None
            
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
                
            # Process icon paths if icon manager is available
            if self.icon_manager:
                css_content = process_qss_for_icons(css_content, self.icon_manager)
                
            return css_content
            
        except Exception as e:
            print(f"Error reading precompiled CSS: {e}")
            return None
            
    def get_theme_variables(self) -> Dict[str, str]:
        """Get the current theme variables.
        
        Returns:
            Dictionary of theme variables
        """
        return self.variables.copy()
        
    def update_theme_variable(self, variable_name: str, value: str):
        """Update a theme variable.
        
        Args:
            variable_name: Name of the variable (without $)
            value: New value for the variable
        """
        self.variables[variable_name] = value
        
    def get_color_scheme(self) -> Dict[str, str]:
        """Extract color scheme from variables.
        
        Returns:
            Dictionary of color variables
        """
        colors = {}
        
        for var_name, var_value in self.variables.items():
            if var_name.startswith('COLOR_') and var_value.startswith('#'):
                # Clean name for easier access
                clean_name = var_name.replace('COLOR_', '').lower()
                colors[clean_name] = var_value
                
        return colors


def create_theme_engine(ui_resources_path: str) -> ThemeEngine:
    """Create a theme engine instance.
    
    Args:
        ui_resources_path: Path to the ui_resources directory
        
    Returns:
        ThemeEngine instance
    """
    return ThemeEngine(ui_resources_path)