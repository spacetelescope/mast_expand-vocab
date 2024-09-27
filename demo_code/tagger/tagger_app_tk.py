import tkinter as tk
import requests
import csv
from typeahead_web import run_api_in_background


class MASTDataProductTagger:
    def __init__(self, master):
        self.master = master
        self.master.title("MAST Data Product Tagger")

        # Set a minimum window size
        self.master.minsize(1400, 700)

        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(master)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        # Configure the canvas
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Pack the scrollbar and canvas
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        self.rows = []  # To hold the entries
        self.current_row = None  # To track the currently focused row
        self.current_product_entry = None  # To track the currently focused product entry

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
        self.suggestions_label = tk.Label(self.table_frame, text="Select from type-ahead suggestions:", font=("Arial", 18), fg='white')
        self.suggestions_label.pack(pady=(0, 5), anchor="e")  # Pack above the suggestions frame

        # Suggestions (typeahead) frame
        self.suggestions_frame = tk.Frame(self.table_frame, bd=8, relief="solid")
        self.suggestions_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Suggestions list and scrollbar
        self.suggestions_list = tk.Listbox(self.suggestions_frame, height=10, width=30, font=("Arial", 18))
        self.suggestions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.suggestions_scrollbar = tk.Scrollbar(self.suggestions_frame)
        self.suggestions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Attach scrollbar to listbox
        self.suggestions_list.config(yscrollcommand=self.suggestions_scrollbar.set)
        self.suggestions_scrollbar.config(command=self.suggestions_list.yview)

        # Initial row
        self.add_row()

        self.result_label = tk.Label(self.scrollable_frame, text="", font=("Arial", 18))
        self.result_label.pack(pady=10)

        # Bind the resize event to update wraplength
        self.master.bind("<Configure>", self.update_wraplength)

        # Bind hover events for suggestions
        self.suggestions_list.bind("<Motion>", self.on_hover)

    def update_wraplength(self, event):
        """Update the wraplength of the result_label based on the window width."""
        self.result_label.config(wraplength=self.master.winfo_width() - 20)

    def add_row(self):
        """Add a row to the entry table"""
        frame = tk.Frame(self.table_frame)

        suffix_label = tk.Label(frame, text="Suffix:", font=("Arial", 18))
        suffix_label.grid(row=0, column=0)
        suffix_entry = tk.Entry(frame, font=("Arial", 18), width=10)
        suffix_entry.grid(row=0, column=1)

        extension_label = tk.Label(frame, text="Extension:", font=("Arial", 18))
        extension_label.grid(row=0, column=2)
        extension_entry = tk.Entry(frame, font=("Arial", 18), width=10)
        extension_entry.grid(row=0, column=3)

        product_label = tk.Label(frame, text="Data Product Types:", font=("Arial", 18))
        product_label.grid(row=0, column=4)
        product_entry = tk.Entry(frame, font=("Arial", 18))
        product_entry.grid(row=0, column=5)

        # pink line to separate suggestions list
        line_canvas = tk.Canvas(frame, width=20, bg='white', highlightthickness=0)
        line_canvas.grid(row=0, column=6, stick='ns', padx=(30, 30))
        line_canvas.config(height=frame.winfo_height())

        # Bind entry to fetch suggestions and track focus
        suffix_entry.bind("<FocusIn>", lambda event: self.on_focus(product_entry, line_canvas))
        extension_entry.bind("<FocusIn>", lambda event: self.on_focus(product_entry, line_canvas))
        product_entry.bind("<KeyRelease>", lambda event: self.fetch_suggestions(product_entry.get()))
        product_entry.bind("<FocusIn>", lambda event: self.on_focus(product_entry, line_canvas))

        # Bind selection to the on_select method
        self.suggestions_list.bind("<<ListboxSelect>>", self.on_select)

        frame.pack(pady=5)
        self.rows.append((suffix_entry, extension_entry, product_entry, line_canvas))

    def on_focus(self, product_entry, line_canvas):
        """Handle focus on an entry field and clear suggestions if a different row is focused."""
        for row in self.rows:
            row[3].config(bg='white')  # Change line color to white
        if self.current_product_entry is not None and self.current_product_entry != product_entry:
            self.suggestions_list.delete(0, tk.END)  # Clear suggestions if a different row is focused

        self.current_product_entry = product_entry  # Update the current focused product entry
        line_canvas.config(bg='pink')

    def on_select(self, event):
        """Handle selection of a suggestion from the typeahead or descendants"""
        selected = self.suggestions_list.curselection()
        if selected and self.current_product_entry is not None:
            suggestion = self.suggestions_list.get(selected)  # Get the selected suggestion
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

    def fetch_suggestions(self, query):
        """Retrieve and display typeahead suggestions"""
        if not query:  # if no text has been entered
            self.suggestions_list.delete(0, tk.END)
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
            self.suggestions_label.config(text="Select from type-ahead suggestions:", font=("Arial", 18), fg='white')  # Reset label text
            suggestions = response.json()
            self.suggestions_list.delete(0, tk.END)
            for suggestion in suggestions:
                self.suggestions_list.insert(tk.END, suggestion)

    def fetch_descendants(self, suggestion):
        """Retrieve and display descendants"""
        self.suggestions_label.config(text="Consider these more specific tags too:", font=("Arial", 18), fg='#40E0D0')  # Update label text
        response = requests.get(f"http://127.0.0.1:5000/descendants?q={suggestion}")
        if response.ok:
            suggestions = response.json()
            self.suggestions_list.delete(0, tk.END)
            for suggestion in suggestions:
                self.suggestions_list.insert(tk.END, suggestion)

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
            for suffix_entry, extension_entry, product_entry in self.rows:
                suffix = suffix_entry.get().strip().lower()
                extension = extension_entry.get().strip().lower()
                data_product_types = product_entry.get().strip().split(',')
                for ptype in data_product_types:
                    if suffix and extension and ptype:
                        ptype = ptype.strip().replace(' ', '_')  # temporary fix for the fact that I haven't integrated URIs
                        csvwriter.writerow([collection, suffix, extension, ptype])


if __name__ == "__main__":
    run_api_in_background()
    root = tk.Tk()
    app = MASTDataProductTagger(root)
    root.mainloop()
