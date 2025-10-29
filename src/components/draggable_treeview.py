import tkinter as tk
from tkinter import ttk

class DraggableTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self._drag_data = {}
        self._drag_callback = None

        self.bind("<ButtonPress-1>", self.on_drag_start)
        self.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<ButtonRelease-1>", self.on_drag_stop)

    def set_drag_callback(self, callback):
        """Set callback function to be called when drag operation completes.
        Callback receives (start_index, final_index)"""
        self._drag_callback = callback

    def on_drag_start(self, event):
        """Start drag operation"""
        iid = self.identify_row(event.y)
        if iid:
            self._drag_data = {
                'item': iid,
                'index': self.index(iid)
            }

    def on_drag_motion(self, event):
        """Handle item movement during drag"""
        if not self._drag_data.get('item'):
            return
        
        target_iid = self.identify_row(event.y)
        if target_iid:
            # Get the target index
            target_index = self.index(target_iid)
            curr_index = self.index(self._drag_data['item'])
            
            if target_index != curr_index:
                # Move the item
                self.move(self._drag_data['item'], '', target_index)

    def on_drag_stop(self, event):
        """Complete drag operation and notify callback"""
        if not self._drag_data.get('item'):
            return

        start_index = self._drag_data.get('index', -1)
        final_index = self.index(self._drag_data['item'])
        item_id = self._drag_data['item']
        self._drag_data = {}
        
        if start_index != -1 and start_index != final_index and self._drag_callback:
            self._drag_callback(start_index, final_index)
