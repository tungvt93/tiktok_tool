"""
Effects Configuration Widget

Widget for configuring video effects.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

from ....application.models.effect_models import EffectInfo, EffectPreset
from ....domain.value_objects.effect_type import EffectType


class EffectsConfigWidget:
    """Widget for configuring video effects"""

    def __init__(self, parent, on_config_changed: Optional[Callable] = None):
        """
        Initialize effects configuration widget.

        Args:
            parent: Parent widget
            on_config_changed: Callback when configuration changes
        """
        self.parent = parent
        self.on_config_changed = on_config_changed
        self._available_effects: List[EffectInfo] = []
        self._presets: List[EffectPreset] = []
        self._create_widgets()
        self._setup_events()

    def _create_widgets(self):
        """Create widget components with modern design"""
        # Main frame with modern styling
        self.frame = ttk.LabelFrame(self.parent, text="🎨 Effects Configuration")

        # Notebook for different configuration modes with improved styling
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Single effect tab with modern design
        self._create_single_effect_tab()

        # Preset tab with improved layout
        self._create_preset_tab()

        # Random effects tab with better organization
        self._create_random_tab()

        # Preview frame with modern styling
        self._create_preview_frame()

    def _create_single_effect_tab(self):
        """Create single effect configuration tab with modern design"""
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="🎯 Single Effect")

        # Effect type selection with improved layout
        effect_frame = ttk.LabelFrame(self.single_frame, text="Effect Type")
        effect_frame.pack(fill="x", padx=10, pady=8)

        # Effect selection row
        effect_select_frame = ttk.Frame(effect_frame)
        effect_select_frame.pack(fill="x", padx=10, pady=8)
        effect_select_frame.columnconfigure(1, weight=1)

        ttk.Label(effect_select_frame, text="Type:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.effect_var = tk.StringVar(value="none")
        self.effect_combo = ttk.Combobox(effect_select_frame, textvariable=self.effect_var, 
                                        state="readonly", width=25)
        self.effect_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # Effect info button with icon
        self.info_btn = ttk.Button(effect_select_frame, text="ℹ️ Info", width=8)
        self.info_btn.grid(row=0, column=2, padx=(5, 0))

        # Duration configuration with modern slider
        duration_frame = ttk.LabelFrame(self.single_frame, text="Duration Settings")
        duration_frame.pack(fill="x", padx=10, pady=8)

        duration_content = ttk.Frame(duration_frame)
        duration_content.pack(fill="x", padx=10, pady=8)
        duration_content.columnconfigure(2, weight=1)

        ttk.Label(duration_content, text="Duration:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.duration_var = tk.StringVar(value="2.0")
        self.duration_spin = ttk.Spinbox(duration_content, from_=0.1, to=10.0, increment=0.1,
                                        textvariable=self.duration_var, width=10)
        self.duration_spin.grid(row=0, column=1, sticky="w", padx=(0, 15))

        # Duration scale with better styling
        self.duration_scale = ttk.Scale(duration_content, from_=0.1, to=10.0, orient="horizontal",
                                       variable=self.duration_var, length=200)
        self.duration_scale.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        # Parameters frame with modern design
        self.params_frame = ttk.LabelFrame(self.single_frame, text="Effect Parameters")
        self.params_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self._param_widgets = {}

    def _create_preset_tab(self):
        """Create preset configuration tab with improved design"""
        self.preset_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.preset_frame, text="📋 Presets")

        # Preset selection with modern layout
        preset_select_frame = ttk.LabelFrame(self.preset_frame, text="Preset Selection")
        preset_select_frame.pack(fill="x", padx=10, pady=8)

        preset_content = ttk.Frame(preset_select_frame)
        preset_content.pack(fill="x", padx=10, pady=8)
        preset_content.columnconfigure(1, weight=1)

        ttk.Label(preset_content, text="Preset:").pack(side="left", padx=(0, 10))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_content, textvariable=self.preset_var,
                                        state="readonly", width=20)
        self.preset_combo.pack(side="left", padx=(0, 10))

        # Preset info button
        self.preset_info_btn = ttk.Button(preset_content, text="ℹ️ Info")
        self.preset_info_btn.pack(side="left", padx=(5, 0))

        # Preset description with better styling
        desc_frame = ttk.LabelFrame(self.preset_frame, text="Description")
        desc_frame.pack(fill="x", padx=10, pady=8)

        self.preset_desc_label = ttk.Label(desc_frame, text="", wraplength=350)
        self.preset_desc_label.pack(fill="x", padx=10, pady=8)

        # Preset effects list with modern design
        effects_list_frame = ttk.LabelFrame(self.preset_frame, text="Effects in Preset")
        effects_list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # Listbox for preset effects with better styling
        self.preset_effects_listbox = tk.Listbox(effects_list_frame, height=8, 
                                                bg='#3d3d3d', fg='#ffffff', 
                                                selectbackground='#007acc',
                                                font=("Segoe UI", 9))
        preset_scrollbar = ttk.Scrollbar(effects_list_frame, orient="vertical",
                                        command=self.preset_effects_listbox.yview)
        self.preset_effects_listbox.configure(yscrollcommand=preset_scrollbar.set)

        self.preset_effects_listbox.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        preset_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    def _create_random_tab(self):
        """Create random effects configuration tab with modern design"""
        self.random_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.random_frame, text="🎲 Random")

        # Enable random effects with modern checkbox
        enable_frame = ttk.LabelFrame(self.random_frame, text="Random Effects")
        enable_frame.pack(fill="x", padx=10, pady=8)

        self.random_enabled_var = tk.BooleanVar()
        random_check = ttk.Checkbutton(enable_frame, text="Enable Random Effects",
                                      variable=self.random_enabled_var)
        random_check.pack(anchor="w", padx=10, pady=8)

        # Random configuration frame with improved layout
        self.random_config_frame = ttk.LabelFrame(self.random_frame, text="Random Configuration")
        self.random_config_frame.pack(fill="x", padx=10, pady=8)

        # Duration range with modern layout
        duration_range_frame = ttk.LabelFrame(self.random_config_frame, text="Duration Range")
        duration_range_frame.pack(fill="x", padx=10, pady=8)

        duration_content = ttk.Frame(duration_range_frame)
        duration_content.pack(fill="x", padx=10, pady=8)
        duration_content.columnconfigure(2, weight=1)
        duration_content.columnconfigure(4, weight=1)

        ttk.Label(duration_content, text="Min:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.min_duration_var = tk.StringVar(value="0.5")
        min_spin = ttk.Spinbox(duration_content, from_=0.1, to=5.0, increment=0.1,
                              textvariable=self.min_duration_var, width=8)
        min_spin.grid(row=0, column=1, sticky="w", padx=(0, 20))

        ttk.Label(duration_content, text="Max:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.max_duration_var = tk.StringVar(value="3.0")
        max_spin = ttk.Spinbox(duration_content, from_=0.5, to=10.0, increment=0.1,
                              textvariable=self.max_duration_var, width=8)
        max_spin.grid(row=0, column=3, sticky="w")

        # Effect categories with modern checkboxes
        categories_frame = ttk.LabelFrame(self.random_config_frame, text="Effect Categories")
        categories_frame.pack(fill="x", padx=10, pady=8)

        categories_content = ttk.Frame(categories_frame)
        categories_content.pack(fill="x", padx=10, pady=8)

        self.category_vars = {}
        categories = [
            ("Slide", "📱"),
            ("Circle", "⭕"), 
            ("Fade", "🌅"),
            ("Other", "✨")
        ]

        for i, (category, icon) in enumerate(categories):
            var = tk.BooleanVar(value=True)
            self.category_vars[category] = var
            check = ttk.Checkbutton(categories_content, text=f"{icon} {category}", 
                                   variable=var)
            check.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)

    def _create_preview_frame(self):
        """Create preview frame with modern styling"""
        preview_frame = ttk.LabelFrame(self.frame, text="👁️ Preview & Estimation")
        preview_frame.pack(fill="x", padx=10, pady=8)

        # Preview controls with modern buttons
        controls_frame = ttk.Frame(preview_frame)
        controls_frame.pack(fill="x", padx=10, pady=8)

        self.preview_btn = ttk.Button(controls_frame, text="👁️ Preview Effect")
        self.preview_btn.pack(side="left", padx=(0, 10))

        self.estimate_btn = ttk.Button(controls_frame, text="⏱️ Estimate Time")
        self.estimate_btn.pack(side="left")

        # Estimate label with better styling
        self.estimate_label = ttk.Label(preview_frame, text="")
        self.estimate_label.pack(fill="x", padx=10, pady=(0, 8))

    def _setup_events(self):
        """Setup event handlers"""
        self.effect_var.trace("w", self._on_effect_changed)
        self.duration_var.trace("w", self._on_duration_changed)
        self.preset_var.trace("w", self._on_preset_changed)
        self.random_enabled_var.trace("w", self._on_random_enabled_changed)

        # Update random config state initially
        self._update_random_config_state()

    def pack(self, **kwargs):
        """Pack the widget"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the widget"""
        self.frame.grid(**kwargs)

    def update_available_effects(self, effects: List[EffectInfo]) -> None:
        """
        Update available effects.

        Args:
            effects: List of available effect info
        """
        self._available_effects = effects

        # Update effect combo
        effect_values = [effect.type for effect in effects]
        self.effect_combo['values'] = effect_values

        if effect_values and not self.effect_var.get():
            self.effect_var.set(effect_values[0])

    def update_presets(self, presets: List[EffectPreset]) -> None:
        """
        Update available presets.

        Args:
            presets: List of effect presets
        """
        self._presets = presets

        # Update preset combo
        preset_names = [preset.name for preset in presets]
        self.preset_combo['values'] = preset_names

        if preset_names and not self.preset_var.get():
            self.preset_var.set(preset_names[0])

    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current effect configuration.

        Returns:
            Dictionary with current configuration
        """
        current_tab = self.notebook.tab(self.notebook.select(), "text")

        if current_tab == "🎯 Single Effect":
            return self._get_single_effect_config()
        elif current_tab == "📋 Presets":
            return self._get_preset_config()
        elif current_tab == "🎲 Random":
            return self._get_random_config()

        return {"mode": "none"}

    def _get_single_effect_config(self) -> Dict[str, Any]:
        """Get single effect configuration"""
        effect_type = self.effect_var.get()
        duration = float(self.duration_var.get())

        # Get parameters from dynamic widgets
        parameters = {}
        for param_name, widget_info in self._param_widgets.items():
            widget = widget_info["widget"]
            param_type = widget_info["type"]

            if param_type == "string":
                parameters[param_name] = widget.get()
            elif param_type == "float":
                parameters[param_name] = float(widget.get())
            elif param_type == "int":
                parameters[param_name] = int(widget.get())
            elif param_type == "bool":
                parameters[param_name] = widget.get()

        return {
            "mode": "single",
            "effect_type": effect_type,
            "duration": duration,
            "parameters": parameters
        }

    def _get_preset_config(self) -> Dict[str, Any]:
        """Get preset configuration"""
        preset_name = self.preset_var.get()
        return {
            "mode": "preset",
            "preset_name": preset_name
        }

    def _get_random_config(self) -> Dict[str, Any]:
        """Get random configuration"""
        if not self.random_enabled_var.get():
            return {"mode": "none"}

        # Get selected categories
        selected_categories = []
        for category, var in self.category_vars.items():
            if var.get():
                selected_categories.append(category)

        return {
            "mode": "random",
            "min_duration": float(self.min_duration_var.get()),
            "max_duration": float(self.max_duration_var.get()),
            "categories": selected_categories
        }

    def _on_effect_changed(self, *args):
        """Handle effect type change"""
        self._update_parameters_ui()
        self._notify_config_changed()

    def _on_duration_changed(self, *args):
        """Handle duration change"""
        self._notify_config_changed()

    def _on_preset_changed(self, *args):
        """Handle preset change"""
        self._update_preset_info()
        self._notify_config_changed()

    def _on_random_enabled_changed(self, *args):
        """Handle random enabled change"""
        self._update_random_config_state()
        self._notify_config_changed()

    def _update_parameters_ui(self):
        """Update parameters UI based on selected effect"""
        # Clear existing parameter widgets
        for widget_info in self._param_widgets.values():
            widget_info["widget"].destroy()
            if "label" in widget_info:
                widget_info["label"].destroy()
        self._param_widgets.clear()

        # Get current effect info
        effect_type = self.effect_var.get()
        effect_info = next((e for e in self._available_effects if e.type == effect_type), None)

        if not effect_info:
            return

        # Add effect-specific parameters
        row = 0

        if effect_info.is_slide_effect:
            # Easing parameter for slide effects
            label = ttk.Label(self.params_frame, text="Easing:")
            label.grid(row=row, column=0, sticky="w", padx=5, pady=2)

            easing_var = tk.StringVar(value="linear")
            easing_combo = ttk.Combobox(self.params_frame, textvariable=easing_var,
                                       values=["linear", "ease-in", "ease-out", "ease-in-out"],
                                       state="readonly", width=15)
            easing_combo.grid(row=row, column=1, sticky="w", padx=5, pady=2)

            self._param_widgets["easing"] = {
                "widget": easing_combo,
                "label": label,
                "type": "string"
            }
            row += 1

        elif effect_info.is_circle_effect:
            # Radius parameter for circle effects
            label = ttk.Label(self.params_frame, text="Radius:")
            label.grid(row=row, column=0, sticky="w", padx=5, pady=2)

            radius_var = tk.StringVar(value="100")
            radius_spin = ttk.Spinbox(self.params_frame, from_=10, to=500, increment=10,
                                     textvariable=radius_var, width=10)
            radius_spin.grid(row=row, column=1, sticky="w", padx=5, pady=2)

            self._param_widgets["radius"] = {
                "widget": radius_spin,
                "label": label,
                "type": "int"
            }
            row += 1

    def _update_preset_info(self):
        """Update preset information display"""
        preset_name = self.preset_var.get()
        preset = next((p for p in self._presets if p.name == preset_name), None)

        if preset:
            self.preset_desc_label.config(text=preset.description)

            # Update effects list
            self.preset_effects_listbox.delete(0, tk.END)
            for effect in preset.effects:
                effect_text = f"{effect.get('type', 'unknown')} ({effect.get('duration', 0)}s)"
                self.preset_effects_listbox.insert(tk.END, effect_text)
        else:
            self.preset_desc_label.config(text="")
            self.preset_effects_listbox.delete(0, tk.END)

    def _update_random_config_state(self):
        """Update random configuration state"""
        enabled = self.random_enabled_var.get()

        # Enable/disable random config widgets
        state = "normal" if enabled else "disabled"

        for child in self.random_config_frame.winfo_children():
            if hasattr(child, 'configure'):
                try:
                    child.configure(state=state)
                except tk.TclError:
                    pass  # Widget doesn't support state configuration
            # Handle nested widgets
            for grandchild in child.winfo_children():
                if hasattr(grandchild, 'configure'):
                    try:
                        grandchild.configure(state=state)
                    except tk.TclError:
                        pass  # Widget doesn't support state configuration
    def _notify_config_changed(self):
        """Notify configuration changed callback"""
        if self.on_config_changed:
            try:
                config = self.get_current_config()
                self.on_config_changed(config)
            except Exception as e:
                print(f"Error in config changed callback: {e}")  # Use logger in real implementation
