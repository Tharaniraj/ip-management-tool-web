"""Theme and UI configuration for the application."""

# Dark theme - GitHub-inspired
DARK_THEME = {
    "name": "Dark",
    "bg_main": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "fg_primary": "#c9d1d9",
    "fg_secondary": "#8b949e",
    "fg_accent": "#58a6ff",
    "fg_success": "#3fb950",
    "fg_danger": "#f85149",
    "fg_warning": "#d29922",
    "button_primary": "#1f6feb",
    "button_primary_hover": "#388bfd",
    "button_success": "#238636",
    "button_success_hover": "#2ea043",
    "button_danger": "#7d1a1a",
    "button_danger_hover": "#b91c1c",
    "button_secondary": "#21262d",
    "button_secondary_hover": "#30363d",
    "tree_selected": "#1f6feb",
    "tree_selected_fg": "#ffffff",
    "tree_even": "#0d1117",
    "tree_odd": "#161b22",
}

# Light theme - Clean and modern
LIGHT_THEME = {
    "name": "Light",
    "bg_main": "#ffffff",
    "bg_secondary": "#f6f8fa",
    "bg_tertiary": "#eaeef2",
    "fg_primary": "#24292f",
    "fg_secondary": "#57606a",
    "fg_accent": "#0969da",
    "fg_success": "#1a7f0e",
    "fg_danger": "#d1242f",
    "fg_warning": "#bf8700",
    "button_primary": "#0969da",
    "button_primary_hover": "#0860ca",
    "button_success": "#1a7f0e",
    "button_success_hover": "#175d0f",
    "button_danger": "#d1242f",
    "button_danger_hover": "#b5161f",
    "button_secondary": "#eaeef2",
    "button_secondary_hover": "#dae8f0",
    "tree_selected": "#0969da",
    "tree_selected_fg": "#ffffff",
    "tree_even": "#ffffff",
    "tree_odd": "#f6f8fa",
}

THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def get_theme(theme_name: str = "dark") -> dict:
    """Get theme configuration by name."""
    return THEMES.get(theme_name.lower(), DARK_THEME)


def get_available_themes() -> list:
    """Get list of available theme names."""
    return list(THEMES.keys())
