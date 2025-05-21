import re

def add_get_track_length_method():
    ui_file_path = 'trackpro/race_coach/ui.py'
    
    # Method to add
    method = """    def get_track_length(self):
        \"\"\"Get the current track length in meters.\"\"\"
        # Try to get track length from session info
        if hasattr(self, 'session_info') and self.session_info:
            track_length = self.session_info.get('track_length', 0)
            if track_length > 0:
                return track_length
                
        # Fall back to checking context of currently loaded data
        if hasattr(self, 'throttle_graph') and hasattr(self.throttle_graph, 'track_length'):
            graph_track_length = self.throttle_graph.track_length
            if graph_track_length > 0:
                return graph_track_length
                
        # Default value if we can't find track length anywhere
        return 1000  # 1000 meters default

"""
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            # Read the file with this encoding
            with open(ui_file_path, 'r', encoding=encoding) as file:
                content = file.read()
            print(f"Successfully read file with {encoding} encoding")
            break
        except UnicodeDecodeError:
            print(f"Failed to read with {encoding} encoding, trying next...")
    
    if content is None:
        print("Could not read the file with any of the attempted encodings")
        return False
    
    # Find the RaceCoachWidget class definition
    match = re.search(r'class RaceCoachWidget\(QWidget\):', content)
    if not match:
        print('RaceCoachWidget class not found')
        return False
    
    # Find a good spot to add the method - look for a method that's already defined
    # to ensure we're inside the class
    method_match = re.search(r'def _format_time\(self, time_in_seconds\):', content)
    if not method_match:
        print('_format_time method not found, finding another insertion point')
        # Try another method
        method_match = re.search(r'def set_driver_data\(self, is_left_driver, data\):', content)
        if not method_match:
            print('Could not find a suitable insertion point')
            return False
    
    # Get the position right after the method and find the next method
    method_pos = method_match.end()
    next_method = re.search(r'def [a-zA-Z_]+\(self', content[method_pos:])
    if next_method:
        insert_pos = method_pos + next_method.start() - 4  # Insert before the next method
    else:
        print('Could not find next method, using class end')
        return False
    
    # Insert the method
    new_content = content[:insert_pos] + method + content[insert_pos:]
    
    # Write the updated content back to the file using the same encoding
    with open(ui_file_path, 'w', encoding=encoding) as file:
        file.write(new_content)
    
    print('Method added successfully')
    return True

if __name__ == '__main__':
    add_get_track_length_method() 