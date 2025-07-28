"""
GUI Application for TikTok Video Processing Tool
Modern interface with video selection, effects configuration, and rendering progress
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import queue
import time
from PIL import Image, ImageTk
import json

# Import from main.py
from main import VideoMerger, VideoConfig, EffectType, GIFProcessor

class VideoProcessingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Video Processing Tool")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2b2b2b')
        
        # Configuration
        self.config = VideoConfig()
        self.video_merger = VideoMerger(self.config)
        
        # Data storage
        self.video_files = []
        self.selected_videos = set()
        self.effects_files = []
        self.selected_effects = set()
        self.rendering_queue = queue.Queue()
        self.is_rendering = False
        self.current_rendering_thread = None
        
        # Load data
        self.load_video_files()
        self.load_effects_files()
        
        # Create GUI
        self.create_widgets()
        self.setup_styles()
        
        # Start progress update thread
        self.progress_update_thread = threading.Thread(target=self.update_progress, daemon=True)
        self.progress_update_thread.start()
    
    def setup_styles(self):
        """Setup modern styles for the GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', 
                       background='#2b2b2b', 
                       foreground='#ffffff', 
                       font=('Arial', 16, 'bold'))
        
        style.configure('Subtitle.TLabel', 
                       background='#2b2b2b', 
                       foreground='#cccccc', 
                       font=('Arial', 12, 'bold'))
        
        style.configure('Custom.TFrame', 
                       background='#3c3c3c', 
                       relief='raised', 
                       borderwidth=1)
        
        style.configure('Custom.TCheckbutton', 
                       background='#3c3c3c', 
                       foreground='#ffffff')
        
        style.configure('Custom.TButton', 
                       background='#4CAF50', 
                       foreground='#ffffff')
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="TikTok Video Processing Tool", 
                               style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Create three main sections
        content_frame = ttk.Frame(main_frame, style='Custom.TFrame')
        content_frame.pack(fill='both', expand=True)
        
        # Configure grid weights
        content_frame.columnconfigure(0, weight=1)  # Left panel
        content_frame.columnconfigure(1, weight=1)  # Center panel  
        content_frame.columnconfigure(2, weight=1)  # Right panel
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Video selection
        self.create_video_selection_panel(content_frame)
        
        # Center panel - Effects configuration
        self.create_effects_panel(content_frame)
        
        # Right panel - Rendering queue and progress
        self.create_rendering_panel(content_frame)
    
    def create_video_selection_panel(self, parent):
        """Create the left panel for video selection"""
        panel = ttk.Frame(parent, style='Custom.TFrame')
        panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Title
        title = ttk.Label(panel, text="Video Selection", style='Subtitle.TLabel')
        title.pack(pady=(10, 5))
        
        # Select all checkbox
        self.select_all_var = tk.BooleanVar()
        select_all_cb = ttk.Checkbutton(panel, text="Select All Videos", 
                                       variable=self.select_all_var,
                                       command=self.toggle_select_all)
        select_all_cb.pack(pady=(0, 10))
        
        # Video list frame
        list_frame = ttk.Frame(panel, style='Custom.TFrame')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Video listbox with scrollbar
        self.video_listbox = tk.Listbox(list_frame, 
                                       bg='#3c3c3c', 
                                       fg='#ffffff',
                                       selectmode='multiple',
                                       font=('Arial', 10))
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.video_listbox.yview)
        self.video_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.video_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind selection event
        self.video_listbox.bind('<<ListboxSelect>>', self.on_video_selection_change)
        
        # Refresh button
        refresh_btn = ttk.Button(panel, text="Refresh Videos", 
                                command=self.refresh_video_list)
        refresh_btn.pack(pady=(0, 10))
        
        # Populate video list
        self.populate_video_list()
    
    def create_effects_panel(self, parent):
        """Create the center panel for effects configuration"""
        panel = ttk.Frame(parent, style='Custom.TFrame')
        panel.grid(row=0, column=1, sticky='nsew', padx=5)
        
        # Title
        title = ttk.Label(panel, text="Effects Configuration", style='Subtitle.TLabel')
        title.pack(pady=(10, 5))
        
        # Opening Effects Section
        opening_frame = ttk.LabelFrame(panel, text="Opening Effects", 
                                      style='Custom.TFrame')
        opening_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Opening effects options
        self.opening_effect_var = tk.StringVar(value="none")
        self.opening_random_var = tk.BooleanVar()
        
        effects = [
            ("None", "none"),
            ("Slide Right to Left", "slide_right_to_left"),
            ("Slide Left to Right", "slide_left_to_right"),
            ("Slide Top to Bottom", "slide_top_to_bottom"),
            ("Slide Bottom to Top", "slide_bottom_to_top"),
            ("Circle Expand", "circle_expand"),
            ("Circle Contract", "circle_contract"),
            ("Circle Rotate CW", "circle_rotate_cw"),
            ("Circle Rotate CCW", "circle_rotate_ccw"),
            ("Fade In", "fade_in")
        ]
        
        for text, value in effects:
            rb = ttk.Radiobutton(opening_frame, text=text, value=value,
                                variable=self.opening_effect_var)
            rb.pack(anchor='w', padx=10, pady=2)
        
        # Random checkbox
        random_cb = ttk.Checkbutton(opening_frame, text="Random Effect", 
                                   variable=self.opening_random_var)
        random_cb.pack(anchor='w', padx=10, pady=(5, 0))
        
        # Effect duration
        duration_frame = ttk.Frame(opening_frame)
        duration_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        ttk.Label(duration_frame, text="Duration (seconds):").pack(side='left')
        self.duration_var = tk.StringVar(value="2.0")
        duration_entry = ttk.Entry(duration_frame, textvariable=self.duration_var, width=10)
        duration_entry.pack(side='right')
        
        # GIF Effects Section
        gif_frame = ttk.LabelFrame(panel, text="GIF Effects", style='Custom.TFrame')
        gif_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # GIF selection options
        self.gif_random_var = tk.BooleanVar()
        gif_random_cb = ttk.Checkbutton(gif_frame, text="Random GIF", 
                                       variable=self.gif_random_var)
        gif_random_cb.pack(anchor='w', padx=10, pady=5)
        
        # GIF list frame
        gif_list_frame = ttk.Frame(gif_frame, style='Custom.TFrame')
        gif_list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # GIF listbox
        self.gif_listbox = tk.Listbox(gif_list_frame, 
                                     bg='#3c3c3c', 
                                     fg='#ffffff',
                                     selectmode='multiple',
                                     font=('Arial', 10))
        gif_scrollbar = ttk.Scrollbar(gif_list_frame, orient='vertical', 
                                     command=self.gif_listbox.yview)
        self.gif_listbox.configure(yscrollcommand=gif_scrollbar.set)
        
        self.gif_listbox.pack(side='left', fill='both', expand=True)
        gif_scrollbar.pack(side='right', fill='y')
        
        # Bind GIF selection event
        self.gif_listbox.bind('<<ListboxSelect>>', self.on_gif_selection_change)
        
        # Populate GIF list
        self.populate_gif_list()
        
        # Preview button
        preview_btn = ttk.Button(panel, text="Preview Effects", 
                                command=self.preview_effects)
        preview_btn.pack(pady=(0, 10))
    
    def create_rendering_panel(self, parent):
        """Create the right panel for rendering queue and progress"""
        panel = ttk.Frame(parent, style='Custom.TFrame')
        panel.grid(row=0, column=2, sticky='nsew', padx=(5, 0))
        
        # Title
        title = ttk.Label(panel, text="Rendering Queue", style='Subtitle.TLabel')
        title.pack(pady=(10, 5))
        
        # Control buttons
        control_frame = ttk.Frame(panel)
        control_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.start_btn = ttk.Button(control_frame, text="Start Rendering", 
                                   command=self.start_rendering)
        self.start_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", 
                                  command=self.stop_rendering, state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 5))
        
        self.pause_btn = ttk.Button(control_frame, text="Pause", 
                                   command=self.pause_rendering, state='disabled')
        self.pause_btn.pack(side='left')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(panel, text="Progress", style='Custom.TFrame')
        progress_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Overall progress
        ttk.Label(progress_frame, text="Overall Progress:").pack(anchor='w', padx=10, pady=(5, 0))
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.pack(fill='x', padx=10, pady=(0, 10))
        
        # Current video progress
        ttk.Label(progress_frame, text="Current Video:").pack(anchor='w', padx=10, pady=(5, 0))
        self.current_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.current_progress.pack(fill='x', padx=10, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready", 
                                     style='Subtitle.TLabel')
        self.status_label.pack(pady=5)
        
        # Queue list frame
        queue_frame = ttk.LabelFrame(panel, text="Rendering Queue", style='Custom.TFrame')
        queue_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Queue listbox
        self.queue_listbox = tk.Listbox(queue_frame, 
                                       bg='#3c3c3c', 
                                       fg='#ffffff',
                                       font=('Arial', 10))
        queue_scrollbar = ttk.Scrollbar(queue_frame, orient='vertical', 
                                       command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        queue_scrollbar.pack(side='right', fill='y')
        
        # Log frame
        log_frame = ttk.LabelFrame(panel, text="Log", style='Custom.TFrame')
        log_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 bg='#3c3c3c', 
                                                 fg='#ffffff',
                                                 font=('Consolas', 9),
                                                 height=8)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def load_video_files(self):
        """Load video files from dongphuc folder"""
        video_pattern = f"{self.config.INPUT_DIR}/*.mp4"
        self.video_files = sorted(glob.glob(video_pattern))
    
    def load_effects_files(self):
        """Load GIF effects from effects folder"""
        effects_pattern = f"{self.config.EFFECTS_DIR}/*.gif"
        self.effects_files = sorted(glob.glob(effects_pattern))
    
    def populate_video_list(self):
        """Populate the video listbox"""
        self.video_listbox.delete(0, tk.END)
        for video_file in self.video_files:
            filename = Path(video_file).name
            self.video_listbox.insert(tk.END, filename)
    
    def populate_gif_list(self):
        """Populate the GIF listbox"""
        self.gif_listbox.delete(0, tk.END)
        for gif_file in self.effects_files:
            filename = Path(gif_file).name
            self.gif_listbox.insert(tk.END, filename)
    
    def toggle_select_all(self):
        """Toggle select all videos"""
        if self.select_all_var.get():
            self.video_listbox.selection_set(0, tk.END)
        else:
            self.video_listbox.selection_clear(0, tk.END)
        self.on_video_selection_change()
    
    def on_video_selection_change(self, event=None):
        """Handle video selection change"""
        selection = self.video_listbox.curselection()
        self.selected_videos = set(selection)
        
        # Update select all checkbox
        if len(selection) == len(self.video_files):
            self.select_all_var.set(True)
        else:
            self.select_all_var.set(False)
    
    def on_gif_selection_change(self, event=None):
        """Handle GIF selection change"""
        selection = self.gif_listbox.curselection()
        self.selected_effects = set(selection)
    
    def refresh_video_list(self):
        """Refresh the video list"""
        self.load_video_files()
        self.populate_video_list()
        self.log_message("Video list refreshed")
    
    def preview_effects(self):
        """Preview effects on a selected video"""
        if not self.selected_videos:
            messagebox.showwarning("Warning", "Please select at least one video for preview")
            return
        
        # Get first selected video
        video_index = list(self.selected_videos)[0]
        video_file = self.video_files[video_index]
        
        # Get selected effects
        opening_effect = self.opening_effect_var.get()
        gif_effect = None
        if self.selected_effects:
            gif_index = list(self.selected_effects)[0]
            gif_effect = self.effects_files[gif_index]
        
        # Show preview dialog
        self.show_preview_dialog(video_file, opening_effect, gif_effect)
    
    def show_preview_dialog(self, video_file, opening_effect, gif_effect):
        """Show preview dialog"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Effect Preview")
        preview_window.geometry("600x400")
        preview_window.configure(bg='#2b2b2b')
        
        # Preview content
        content = f"Video: {Path(video_file).name}\n"
        content += f"Opening Effect: {opening_effect}\n"
        content += f"GIF Effect: {Path(gif_effect).name if gif_effect else 'None'}\n"
        content += f"Duration: {self.duration_var.get()} seconds"
        
        text_widget = tk.Text(preview_window, bg='#3c3c3c', fg='#ffffff', 
                             font=('Arial', 12))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', content)
        text_widget.config(state='disabled')
        
        # Close button
        close_btn = ttk.Button(preview_window, text="Close", 
                              command=preview_window.destroy)
        close_btn.pack(pady=10)
    
    def start_rendering(self):
        """Start the rendering process"""
        if not self.selected_videos:
            messagebox.showwarning("Warning", "Please select at least one video to render")
            return
        
        # Prepare rendering queue
        self.prepare_rendering_queue()
        
        # Start rendering thread
        self.is_rendering = True
        self.current_rendering_thread = threading.Thread(target=self.rendering_worker, daemon=True)
        self.current_rendering_thread.start()
        
        # Update UI
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.pause_btn.config(state='normal')
        
        self.log_message("Rendering started")
    
    def prepare_rendering_queue(self):
        """Prepare the rendering queue with selected videos"""
        # Clear queue
        self.queue_listbox.delete(0, tk.END)
        
        # Add selected videos to queue
        for video_index in self.selected_videos:
            video_file = self.video_files[video_index]
            filename = Path(video_file).name
            self.queue_listbox.insert(tk.END, f"⏳ {filename}")
        
        # Update progress
        self.overall_progress['maximum'] = len(self.selected_videos)
        self.overall_progress['value'] = 0
        self.current_progress['value'] = 0
    
    def rendering_worker(self):
        """Worker thread for rendering videos"""
        try:
            total_videos = len(self.selected_videos)
            completed = 0
            
            for video_index in self.selected_videos:
                if not self.is_rendering:
                    break
                
                video_file = self.video_files[video_index]
                filename = Path(video_file).name
                
                # Update status
                self.root.after(0, lambda: self.status_label.config(text=f"Processing: {filename}"))
                self.root.after(0, lambda: self.queue_listbox.itemconfig(completed, {'bg': '#4CAF50'}))
                
                # Get random background video
                background_videos = glob.glob(f"{self.config.BACKGROUND_DIR}/*.mp4")
                if not background_videos:
                    self.log_message(f"Error: No background videos found")
                    continue
                
                import random
                bg_video = random.choice(background_videos)
                
                # Configure effects
                self.configure_effects()
                
                # Render video
                success = self.render_single_video(video_file, bg_video, completed)
                
                if success:
                    self.root.after(0, lambda: self.queue_listbox.itemconfig(completed, {'bg': '#4CAF50'}))
                    self.log_message(f"✓ Completed: {filename}")
                else:
                    self.root.after(0, lambda: self.queue_listbox.itemconfig(completed, {'bg': '#f44336'}))
                    self.log_message(f"✗ Failed: {filename}")
                
                completed += 1
                self.root.after(0, lambda: self.overall_progress.config(value=completed))
                
                # Update current progress
                self.current_progress['value'] = 0
                for i in range(100):
                    if not self.is_rendering:
                        break
                    self.root.after(0, lambda v=i: self.current_progress.config(value=v))
                    time.sleep(0.1)
            
            # Rendering completed
            self.root.after(0, self.rendering_completed)
            
        except Exception as e:
            self.log_message(f"Rendering error: {str(e)}")
            self.root.after(0, self.rendering_completed)
    
    def configure_effects(self):
        """Configure effects based on user selection"""
        # Opening effect
        if self.opening_random_var.get():
            import random
            effects = list(EffectType)
            self.config.OPENING_EFFECT = random.choice(effects)
        else:
            effect_map = {
                "none": EffectType.NONE,
                "slide_right_to_left": EffectType.SLIDE_RIGHT_TO_LEFT,
                "slide_left_to_right": EffectType.SLIDE_LEFT_TO_RIGHT,
                "slide_top_to_bottom": EffectType.SLIDE_TOP_TO_BOTTOM,
                "slide_bottom_to_top": EffectType.SLIDE_BOTTOM_TO_TOP,
                "circle_expand": EffectType.CIRCLE_EXPAND,
                "circle_contract": EffectType.CIRCLE_CONTRACT,
                "circle_rotate_cw": EffectType.CIRCLE_ROTATE_CW,
                "circle_rotate_ccw": EffectType.CIRCLE_ROTATE_CCW,
                "fade_in": EffectType.FADE_IN
            }
            self.config.OPENING_EFFECT = effect_map.get(self.opening_effect_var.get(), EffectType.NONE)
        
        # Duration
        try:
            self.config.OPENING_DURATION = float(self.duration_var.get())
        except ValueError:
            self.config.OPENING_DURATION = 2.0
    
    def render_single_video(self, video_file, bg_video, index):
        """Render a single video with effects"""
        try:
            # Update queue status
            self.root.after(0, lambda: self.queue_listbox.itemconfig(index, {'bg': '#FF9800'}))
            
            # Use the existing VideoMerger to render
            success = self.video_merger.render_single_video(video_file, bg_video, index, add_effects=True)
            
            return success
            
        except Exception as e:
            self.log_message(f"Error rendering {Path(video_file).name}: {str(e)}")
            return False
    
    def stop_rendering(self):
        """Stop the rendering process"""
        self.is_rendering = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(state='disabled')
        self.status_label.config(text="Stopped")
        self.log_message("Rendering stopped")
    
    def pause_rendering(self):
        """Pause/resume rendering"""
        if self.pause_btn.cget('text') == "Pause":
            self.is_rendering = False
            self.pause_btn.config(text="Resume")
            self.status_label.config(text="Paused")
            self.log_message("Rendering paused")
        else:
            self.is_rendering = True
            self.pause_btn.config(text="Pause")
            self.status_label.config(text="Resumed")
            self.log_message("Rendering resumed")
    
    def rendering_completed(self):
        """Handle rendering completion"""
        self.is_rendering = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(state='disabled')
        self.status_label.config(text="Completed")
        self.log_message("Rendering completed")
    
    def update_progress(self):
        """Update progress bars"""
        while True:
            time.sleep(0.1)
            if self.is_rendering:
                # Progress updates are handled in the rendering worker
                pass
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: self.log_text.insert(tk.END, log_entry))
        self.root.after(0, lambda: self.log_text.see(tk.END))

def main():
    """Main entry point for GUI application"""
    root = tk.Tk()
    app = VideoProcessingGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 