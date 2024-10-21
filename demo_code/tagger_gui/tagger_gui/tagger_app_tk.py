import tkinter as tk
from tkinter import filedialog
import requests
import csv
import os
import re
from .typeahead_web import run_api_in_background


class MASTDataProductTagger:
    def __init__(self, master):
        self.master = master
        self.master.title("MAST Data Product Tagger")

        self.pink = 'white'
        self.blue = '#40E0D0'
        self.yellow = 'black'

        # Set a minimum window size
        self.master.minsize(1200, 700)

        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(master)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.master.bind("<MouseWheel>", self.on_vertical)

        # Configure the canvas
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Pack the scrollbar and canvas
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        self.rows = []  # To hold the entries
        self.current_row_index = None  # To track the currently focused row
        self.current_product_entry = None  # To track the currently focused product entry
        self.current_suffix_entry = None
        self.current_extension_entry = None

        # Header
        header = tk.Label(self.scrollable_frame, text="MAST Data Product Tagger", font=("Arial", 18))
        header.pack(pady=10)

        self.info_label = tk.Label(self.scrollable_frame, text=(
            "Please enter each suffix.extension pair that your data collection contains, then start tagging!\n"
            "For example, if your file looks like '*_spec.fits', then suffix='spec', extension='fits', "
            "and you might tag this product as 'Spectra'.\n"
            "You can tag each product type with as many tags as you like!"), font=("Arial", 18))
        self.info_label.pack(pady=10)

        # Entry box for collection name
        self.collection_entry_label = tk.Label(self.scrollable_frame, text="Collection name:", font=("Arial", 18))
        self.collection_entry_label.pack(pady=5)
        self.collection_entry = tk.Entry(self.scrollable_frame, font=("Arial", 18))
        self.collection_entry.pack(pady=5)

        # Set up table with scrollbar
        self.table_frame = tk.Frame(self.scrollable_frame)
        self.table_frame.pack(pady=10)

        # "Add row" button
        self.add_row_button = tk.Button(self.scrollable_frame, text="Add Row", command=self.add_row)
        self.add_row_button.pack(pady=5)

        # "Export to csv" button; will be converted to github merge request later
        self.export_button = tk.Button(self.scrollable_frame, text="Export CSV", command=self.export_to_csv)
        self.export_button.pack(pady=5)

        # Suggestions (typeahead) label above the suggestions list
        self.suggestions_label = tk.Label(self.table_frame, text="Select from type-ahead suggestions:", font=("Arial", 18))
        self.suggestions_label.pack(pady=(0, 5), anchor="e")  # Pack above the suggestions frame

        # Suggestions (typeahead) frame
        self.suggestions_frame = tk.Frame(self.table_frame, bd=8, relief="raised")
        self.suggestions_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Suggestions list and scrollbar
        self.suggestions_list = tk.Listbox(self.suggestions_frame, height=10, width=30, font=("Arial", 18))
        self.suggestions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.suggestions_scrollbar = tk.Scrollbar(self.suggestions_frame)
        self.suggestions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Attach scrollbar to listbox
        self.suggestions_list.config(yscrollcommand=self.suggestions_scrollbar.set)
        self.suggestions_scrollbar.config(command=self.suggestions_list.yview)

        # Add "Read Directory" button
        self.read_directory_button = tk.Button(self.scrollable_frame, text="Read Directory", command=self.read_directory)
        self.read_directory_button.pack(pady=5)

        # Initial row
        self.add_row()

        self.result_label = tk.Label(self.scrollable_frame, text="", font=("Arial", 18))
        self.result_label.pack(pady=10)

        # Bind the resize event to update wraplength
        self.master.bind("<Configure>", self.update_wraplength)

        # Bind hover events for suggestions
        self.suggestions_list.bind("<Motion>", self.on_hover)

        # Temporary hack: set list of suffix and extension suggestions
        self.extension_suggestions = ["asdf", "csv", "db", "ecsv", "fits", "jpeg", "jpg", "md", "pdf", "png", "txt"]
        self.suffix_suggestions = ['cat', 'drz', 'img', 'model', 'spec']
        self.basis_suggestions = ['Observations', 'Derived properties', 'Synthetic models']
        self.intent_suggestions = ['Science', 'Preview', 'Background map', 'Error map', 'Exposure map', 'Noise map', 'Weight map', 'Bias frame', 'Dark frame', 'Flat field', 'Other']

    def on_vertical(self, event):
        """Handle mouse wheel scroll."""
        widget_at_mouse = self.master.winfo_containing(event.x_root, event.y_root)
        if widget_at_mouse != self.suggestions_list:
            self.canvas.yview_scroll(-1 * event.delta, 'units')

    def update_wraplength(self, event):
        """Update the wraplength of the result_label based on the window width."""
        self.result_label.config(wraplength=self.master.winfo_width() - 20)

    def add_row(self):
        """Add a row to the entry table"""
        frame = tk.Frame(self.table_frame)

        defaultentrywidth = 10

        # Create label row
        tk.Label(frame, text="Suffix", font=("Arial", 18)).grid(row=0, column=0)
        tk.Label(frame, text="Extension", font=("Arial", 18)).grid(row=0, column=2)
        tk.Label(frame, text="Basis", font=("Arial", 18)).grid(row=0, column=4)
        tk.Label(frame, text="Role", font=("Arial", 18)).grid(row=0, column=6)
        tk.Label(frame, text="Data Product Type", font=("Arial", 18)).grid(row=0, column=8)

        # Create entry row
        suffix_entry = tk.Entry(frame, font=("Arial", 18), width=defaultentrywidth)
        suffix_entry.grid(row=1, column=0)

        extension_entry = tk.Entry(frame, font=("Arial", 18), width=defaultentrywidth)
        extension_entry.grid(row=1, column=2)

        basis_entry = tk.Entry(frame, font=("Arial", 18), width=defaultentrywidth)
        basis_entry.grid(row=1, column=4)

        intent_entry = tk.Entry(frame, font=("Arial", 18), width=defaultentrywidth)
        intent_entry.grid(row=1, column=6)

        product_entry = tk.Entry(frame, font=("Arial", 18))
        product_entry.grid(row=1, column=8)
        product_entry.config(state=tk.DISABLED)

        # pink line to separate suggestions list
        line_canvas = tk.Canvas(frame, width=20, bg='white', highlightthickness=0)
        line_canvas.grid(row=1, column=10, stick='ns', padx=(30, 30))
        line_canvas.config(height=frame.winfo_height())

        # Bind entry to fetch suggestions and track focus
        suffix_entry.bind("<FocusIn>", lambda event: self.on_suffix_focus(suffix_entry, line_canvas))
        extension_entry.bind("<FocusIn>", lambda event: self.on_extension_focus(extension_entry, line_canvas))
        product_entry.bind("<KeyRelease>", lambda event: self.fetch_suggestions(product_entry.get()))
        product_entry.bind("<FocusIn>", lambda event: self.on_product_focus(product_entry, line_canvas))
        basis_entry.bind("<FocusIn>", lambda event: self.on_basis_focus(basis_entry, line_canvas))
        intent_entry.bind("<FocusIn>", lambda event: self.on_intent_focus(intent_entry, line_canvas))

        # Bind selection to the on_select method
        self.suggestions_list.bind("<<ListboxSelect>>", lambda event: self.on_select(event, product_entry))

        frame.pack(pady=5)
        self.rows.append((suffix_entry, extension_entry, product_entry, line_canvas, intent_entry))

    def on_product_focus(self, product_entry, line_canvas):
        """Handle focus on an entry field and clear suggestions if a different row is focused."""
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        if self.current_product_entry is not None and self.current_product_entry != product_entry:
            self.suggestions_list.delete(0, tk.END)  # Clear suggestions if a different row is focused
        if not self.current_product_entry:
            self.suggestions_list.delete(0, tk.END)  # Clear suggestions if a different column was previously focused

        self.current_product_entry = product_entry  # Update the current focused product entry
        self.current_extension_entry = None  # Clear the extension focus
        self.current_suffix_entry = None  # Clear the suffix focus
        self.current_basis_entry = None  # Clear basis focus
        self.current_intent_entry = None  # Clear intent focus

        if 'specific' not in self.suggestions_label.cget("text"):
            self.suggestions_label.config(text="Select from type-ahead suggestions:", font=("Arial", 18))  # Reset label text

        line_canvas.config(bg=self.yellow)

    def on_select(self, event, product_entry):
        """Handle selection of a suggestion from the typeahead or descendants"""
        selected = self.suggestions_list.curselection()
        if selected:
            suggestion = self.suggestions_list.get(selected)  # Get the selected suggestion
            if self.current_product_entry is not None:
                current_value = self.current_product_entry.get().strip()  # Get the focused row's product entry
                last_comma_index = current_value.rfind(',')
                # Get new value for tag list: append selected tag to everything before the most recent comma
                new_value = current_value[:last_comma_index + 1] + ' ' + suggestion + ', ' if last_comma_index != -1 else suggestion + ', '
                self.current_product_entry.delete(0, tk.END)  # Clear the entered tags
                self.current_product_entry.insert(0, new_value.strip())  # and set to new value for entered tags

                # Retrieve and display descendants of the selected tags
                self.fetch_descendants(suggestion)

                # Refocus and place the cursor
                self.master.after(100, lambda: self.current_product_entry.focus_set())
                self.master.after(100, lambda: self.current_product_entry.icursor(tk.END))
                self.current_product_entry.xview(tk.END)

            elif self.current_suffix_entry is not None:
                self.current_suffix_entry.delete(0, tk.END)
                self.current_suffix_entry.insert(0, suggestion)

            elif self.current_extension_entry is not None:
                self.current_extension_entry.delete(0, tk.END)
                self.current_extension_entry.insert(0, suggestion)

            elif self.current_basis_entry is not None:
                self.current_basis_entry.delete(0, tk.END)
                self.current_basis_entry.insert(0, suggestion)

            elif self.current_intent_entry is not None:
                self.current_intent_entry.delete(0, tk.END)
                self.current_intent_entry.insert(0, suggestion)
                self.check_intent(self.current_intent_entry)

    def fetch_suggestions(self, query):
        """Retrieve and display typeahead suggestions"""

        if not query:  # if no text has been entered
            self.clear_suggestions()
            return

        # query to send is everything after the most recent comma
        last_comma_index = query.rfind(',')
        query_to_send = query[last_comma_index + 1:].strip() if last_comma_index != -1 else query.strip()

        if not query_to_send:  # if no text has been entered after the most recent comma
            self.suggestions_list.delete(0, tk.END)
            return

        # Send query to autocomplete and display results
        response = requests.get(f"http://127.0.0.1:5000/autocomplete?q={query_to_send}")
        if response.ok:
            self.suggestions_label.config(text="Select from type-ahead suggestions:", font=("Arial", 18))  # Reset label text
            suggestions = response.json()
            self.suggestions_list.delete(0, tk.END)
            for suggestion in suggestions:
                self.suggestions_list.insert(tk.END, suggestion)

    def fetch_descendants(self, suggestion):
        """Retrieve and display descendants"""
        self.suggestions_label.config(text="Consider these more specific tags too:", font=("Arial", 18), fg=self.blue, bg='black')  # Update label text
        response = requests.get(f"http://127.0.0.1:5000/descendants?q={suggestion}")
        if response.ok:
            suggestions = response.json()
            self.suggestions_list.delete(0, tk.END)
            for suggestion in suggestions:
                self.suggestions_list.insert(tk.END, suggestion)

    def show_suffix_suggestions(self):
        """Display suffix suggestions when the suffix entry is focused."""
        self.suggestions_list.delete(0, tk.END)
        self.suggestions_label.config(text="Non-exclusive list of common filename suffixes:", font=("Arial", 18), fg=self.pink, bg='black')  # Update label text
        for suggestion in self.suffix_suggestions:
            self.suggestions_list.insert(tk.END, suggestion)

    def show_extension_suggestions(self):
        """Display extension suggestions when the extension entry is focused."""
        self.suggestions_list.delete(0, tk.END)
        self.suggestions_label.config(text="Non-exclusive list of common filename extensions:", font=("Arial", 18), fg=self.pink, bg='black')  # Update label text
        for suggestion in self.extension_suggestions:
            self.suggestions_list.insert(tk.END, suggestion)

    def show_basis_suggestions(self):
        """Display basis suggestions when the basis entry is focused."""
        self.suggestions_list.delete(0, tk.END)
        self.suggestions_label.config(text="Select the one best-fitting basis from this list:", font=("Arial", 18), fg=self.pink, bg='black')  # Update label text
        for suggestion in self.basis_suggestions:
            self.suggestions_list.insert(tk.END, suggestion)

    def show_intent_suggestions(self):
        """Display intent suggestions when the intent entry is focused."""
        self.suggestions_list.delete(0, tk.END)
        self.suggestions_label.config(text="Select the one best-fitting role from this list:", font=("Arial", 18), fg=self.pink, bg='black')  # Update label text
        for suggestion in self.intent_suggestions:
            self.suggestions_list.insert(tk.END, suggestion)

    def clear_suggestions(self):
        """Clear suggestions when suffix or extension entry is focused."""
        self.suggestions_list.delete(0, tk.END)

    def on_hover(self, event):
        """Highlight the item under the mouse pointer."""
        index = self.suggestions_list.nearest(event.y)
        if index != -1:
            self.suggestions_list.selection_clear(0, tk.END)  # Clear all selections
            self.suggestions_list.selection_set(index)  # Highlight the current item
            self.suggestions_list.activate(index)  # Activate it for visual feedback

    def export_to_csv(self):
        """Export table to csv"""
        collection = self.collection_entry.get().strip().lower()
        with open(f'{collection}_map.csv', 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['ingest_id', 'ingest_suffix', 'ingest_format', 'ingest_uri_short'])
            for suffix_entry, extension_entry, product_entry, line_canvas, intent_entry in self.rows:
                suffix = suffix_entry.get().strip().lower()
                extension = extension_entry.get().strip().lower()
                data_product_types = product_entry.get().strip().split(',')
                for ptype in data_product_types:
                    if suffix and extension and ptype:
                        ptype = ptype.strip().replace(' ', '_')  # temporary fix for the fact that I haven't integrated URIs
                        csvwriter.writerow([collection, suffix, extension, ptype])

    def read_directory(self):
        """Read the specified directory and populate unique suffixes."""
        directory = filedialog.askdirectory()  # Open a dialog to choose a directory
        if directory:
            suffix_extensions = find_suffix_extensions(directory)
            self.populate_suffix_extensions(suffix_extensions)

    def populate_suffix_extensions(self, suffix_extensions):
        """Populate the suffix column with unique suffixes."""

        for suffix_extension in suffix_extensions:
            suffix, extension = suffix_extension.split('.', 1)
            self.add_row()  # Add a new row for each unique suffix-extension pair
            self.rows[-1][0].insert(0, suffix)  # Populate the suffix entry
            self.rows[-1][1].insert(0, extension)  # Populate the extension entry

    def on_suffix_focus(self, suffix_entry, line_canvas):
        self.current_suffix_entry = suffix_entry
        self.current_extension_entry = None  # Clear the extension focus
        self.current_product_entry = None  # Clear product focus
        self.current_basis_entry = None  # Clear basis focus
        self.current_intent_entry = None  # Clear intent focus
        self.show_suffix_suggestions()
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        line_canvas.config(bg=self.yellow)

    def on_extension_focus(self, extension_entry, line_canvas):
        self.current_extension_entry = extension_entry
        self.current_suffix_entry = None  # Clear the suffix focus
        self.current_product_entry = None  # Clear product focus
        self.current_basis_entry = None  # Clear basis focus
        self.current_intent_entry = None  # Clear intent focus
        self.show_extension_suggestions()
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        line_canvas.config(bg=self.yellow)

    def on_basis_focus(self, basis_entry, line_canvas):
        self.current_basis_entry = basis_entry
        self.current_suffix_entry = None  # Clear the suffix focus
        self.current_product_entry = None  # Clear product focus
        self.current_extension_entry = None  # Clear extension focus
        self.current_intent_entry = None  # Clear intent focus
        self.show_basis_suggestions()
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        line_canvas.config(bg=self.yellow)

    def on_intent_focus(self, intent_entry, line_canvas):
        self.current_intent_entry = intent_entry
        self.current_suffix_entry = None  # Clear the suffix focus
        self.current_extension_entry = None  # Clear extension focus
        self.current_product_entry = None  # Clear product focus
        self.current_basis_entry = None  # Clear basis focus

        # Fine the row index of the focused intent entry
        self.current_row_index = next(i for i, row in enumerate(self.rows) if row[4] == intent_entry)  # row[4] is intent_entry

        self.show_intent_suggestions()
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        line_canvas.config(bg=self.yellow)

    def check_intent(self, intent_entry):
        """Enable or disable product_entry based on intent_entry value."""
        intent_value = intent_entry.get().strip()
        if self.current_row_index is not None:
            product_entry = self.rows[self.current_row_index][2]  # Access the product_entry using the current row index
            if intent_value in ["Science", "Other"]:
                product_entry.config(state=tk.NORMAL)  # Enable editing
            else:
                product_entry.config(state=tk.DISABLED)  # Disable editing


def find_suffix_extensions(directory) -> list:
    unique_suffix_extensions = set()

    pattern = re.compile(r'_([^_]*)(\.[\w.]+)$')

    for _, _, files in os.walk(directory):
        for file in files:
            match = pattern.search(file)
            if match:
                suffix_extension = match.group(1) + match.group(2)
                unique_suffix_extensions.add(suffix_extension)

    return list(unique_suffix_extensions)


def main():
    run_api_in_background()
    root = tk.Tk()
    app = MASTDataProductTagger(root)
    root.mainloop()


if __name__ == "__main__":
    main()
