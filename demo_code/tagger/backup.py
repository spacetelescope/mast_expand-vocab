import tkinter as tk
from tkinter import messagebox
import requests
import csv
from typeahead_web import run_api_in_background

class MASTDataProductTagger:
    def __init__(self, master):
        self.master = master
        self.master.title("MAST Data Product Tagger")

        self.rows = []
        self.suggestions_list = tk.Listbox(master, height=5, width=30)
        self.suggestions_list.place(relx=0, rely=0, anchor='nw')  # Start hidden off-screen

        # Header
        header = tk.Label(master, text="MAST Data Product Tagger", font=("Arial", 16))
        header.pack(pady=10)

        self.collection_label = tk.Label(master, text="Collection short name:")
        self.collection_label.pack(pady=5)
        self.collection_entry = tk.Entry(master)
        self.collection_entry.pack(pady=5)

        self.info_label = tk.Label(master, text=(
            "Please enter each suffix.extension pair that your data collection contains, then start tagging!\n"
            "For example, if your file looks like '*_spec.fits', then suffix='spec', extension='fits', "
            "and you might tag this product as 'Spectra'.\n"
            "You can tag each product type with as many tags as you like!"))
        self.info_label.pack(pady=10)

        self.table_frame = tk.Frame(master)
        self.table_frame.pack(pady=10)

        self.add_row_button = tk.Button(master, text="Add Row", command=self.add_row)
        self.add_row_button.pack(pady=5)

        self.export_button = tk.Button(master, text="Export CSV", command=self.export_to_csv)
        self.export_button.pack(pady=5)

        # Initial row
        self.add_row()

        self.result_label = tk.Label(master, text="", font=("Arial", 12), wraplength=400)
        self.result_label.pack(pady=10)

    def add_row(self):
        row = {}
        frame = tk.Frame(self.table_frame)

        suffix_label = tk.Label(frame, text="Suffix:")
        suffix_label.grid(row=0, column=0)
        suffix_entry = tk.Entry(frame)
        suffix_entry.grid(row=0, column=1)

        extension_label = tk.Label(frame, text="Extension:")
        extension_label.grid(row=0, column=2)
        extension_entry = tk.Entry(frame)
        extension_entry.grid(row=0, column=3)

        product_label = tk.Label(frame, text="Data Product Type:")
        product_label.grid(row=0, column=4)
        product_entry = tk.Entry(frame)
        product_entry.grid(row=0, column=5)

        product_entry.bind("<KeyRelease>", lambda event: self.fetch_suggestions(product_entry.get(), product_entry))
        product_entry.bind("<FocusOut>", lambda event: self.suggestions_list.place_forget())  # Hide on focus out

        frame.pack(pady=5)
        self.rows.append((suffix_entry, extension_entry, product_entry))

    def fetch_suggestions(self, query, product_entry):
        if not query:
            self.suggestions_list.place_forget()  # Hide initially
            return

        last_comma_index = query.rfind(',')
        query_to_send = query[last_comma_index + 1:].strip() if last_comma_index != -1 else query.strip()
        
        response = requests.get(f"http://127.0.0.1:5000/autocomplete?q={query_to_send}")
        if response.ok:
            suggestions = response.json()
            self.suggestions_list.delete(0, tk.END)
            for suggestion in suggestions:
                self.suggestions_list.insert(tk.END, suggestion)

        if suggestions:
            self.position_suggestions(product_entry)
            self.suggestions_list.place(relx=product_entry.winfo_x() / self.master.winfo_width(),
                                         rely=(product_entry.winfo_y() + product_entry.winfo_height()) / self.master.winfo_height(),
                                         anchor='nw')
            self.suggestions_list.lift()  # Bring it to the front
        else:
            self.suggestions_list.place_forget()  # Hide if no suggestions

    def position_suggestions(self, product_entry):
        # Calculate the relative position of the suggestions listbox
        x = product_entry.winfo_x()
        y = product_entry.winfo_y() + product_entry.winfo_height()
        self.suggestions_list.place(relx=x / self.master.winfo_width(), rely=y / self.master.winfo_height(), anchor='nw')

    def on_select(self, event, product_entry):
        selected = self.suggestions_list.curselection()
        if selected:
            suggestion = self.suggestions_list.get(selected)
            current_value = product_entry.get().strip()
            last_comma_index = current_value.rfind(',')
            new_value = current_value[:last_comma_index + 1] + ' ' + suggestion + ', ' if last_comma_index != -1 else suggestion + ', '
            product_entry.delete(0, tk.END)
            product_entry.insert(0, new_value.strip())

            # Clear the suggestions list
            self.suggestions_list.delete(0, tk.END)

            # Refocus and place the cursor
            self.master.after(100, lambda: product_entry.focus_set())
            self.master.after(100, lambda: product_entry.icursor(tk.END))

    def export_to_csv(self):
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
                        ptype = ptype.strip().replace(' ', '_')  # hacky nonsense to simulate using URIs
                        csvwriter.writerow([collection, suffix, extension, ptype])

        messagebox.showinfo("Export Complete", "Data exported to data_products.csv.")

if __name__ == "__main__":
    run_api_in_background()
    root = tk.Tk()
    app = MASTDataProductTagger(root)
    root.mainloop()
