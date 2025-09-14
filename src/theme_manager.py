import os

class ThemeManager:
    def __init__(self, styles_dir='src/styles'):
        self.styles_dir = styles_dir
        self.themes = self._discover_themes()

    def _discover_themes(self):
        themes = {}
        if not os.path.isdir(self.styles_dir):
            return themes

        for filename in os.listdir(self.styles_dir):
            if filename.endswith('.qss'):
                theme_name = os.path.splitext(filename)[0]
                themes[theme_name] = os.path.join(self.styles_dir, filename)
        return themes

    def get_theme_names(self):
        return list(self.themes.keys())

    def get_stylesheet(self, theme_name):
        if theme_name not in self.themes:
            return ""

        filepath = self.themes[theme_name]
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return ""
