# pip install gitpython tk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from git import Repo

class GitSplitUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Git Split Tool")

        self.repo = None
        self.changed_files = []
        self.splits = []

        self.create_repo_picker()

    def create_repo_picker(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="x")

        ttk.Label(frame, text="Select Git Repository:").pack(side="left")
        ttk.Button(frame, text="Browse", command=self.load_repo).pack(side="left", padx=5)

    def load_repo(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if not path:
            return
        try:
            self.repo = Repo(path)
            branches = [b.name for b in self.repo.branches]
        except Exception as e:
            messagebox.showerror("Error", f"Not a valid Git repo: {e}")
            return

        self.repo_path = path

        # Clear any existing UI
        for w in self.root.winfo_children():
            if isinstance(w, ttk.Frame) and w != self.root.children["!frame"]:
                w.destroy()

        self.create_branch_selector(branches)

    def create_branch_selector(self, branches):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="x")

        ttk.Label(frame, text="Base Branch:").pack(side="left")
        self.base_var = tk.StringVar()
        base_menu = ttk.Combobox(frame, textvariable=self.base_var, values=branches, state="readonly", width=15)
        base_menu.pack(side="left", padx=5)

        ttk.Label(frame, text="Feature Branch:").pack(side="left", padx=5)
        self.feature_var = tk.StringVar()
        feature_menu = ttk.Combobox(frame, textvariable=self.feature_var, values=branches, state="readonly", width=15)
        feature_menu.pack(side="left", padx=5)

        ttk.Label(frame, text="No. of splits (1–5):").pack(side="left", padx=5)
        self.split_var = tk.IntVar(value=2)
        ttk.Spinbox(frame, from_=1, to=5, textvariable=self.split_var, width=5).pack(side="left")

        ttk.Button(frame, text="Load Changed Files", command=self.load_changes).pack(side="left", padx=10)

    def load_changes(self):
        base_branch = self.base_var.get()
        feature_branch = self.feature_var.get()

        if not base_branch or not feature_branch:
            messagebox.showwarning("Missing selection", "Please select both base and feature branches.")
            return
        if base_branch == feature_branch:
            messagebox.showwarning("Invalid selection", "Base and feature branches must be different.")
            return

        repo = self.repo
        try:
            repo.git.checkout(feature_branch)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to checkout feature branch: {e}")
            return

        try:
            base_commit = repo.commit(base_branch)
            feature_commit = repo.commit(feature_branch)
            diff = feature_commit.diff(base_commit, paths=None)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compute diff: {e}")
            return

        self.changed_files = [d.b_path for d in diff if d.change_type in ("A", "M", "R")]

        if not self.changed_files:
            messagebox.showinfo("No changes", "No changed files found between selected branches.")
            return

        self.create_split_ui()

    def create_split_ui(self):
        # Main frame
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # Left: Changed files
        left_frame = ttk.Frame(frame)
        left_frame.pack(side="left", fill="y", padx=5)

        ttk.Label(left_frame, text="Changed Files").pack()
        self.file_vars = {}
        canvas = tk.Canvas(left_frame)
        scroll = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        list_frame = ttk.Frame(canvas)

        list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="y", expand=True)
        scroll.pack(side="right", fill="y")

        self.file_checkbox_frame = list_frame  # store reference for later
        for f in self.changed_files:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.file_checkbox_frame, text=f, variable=var)
            cb.pack(anchor="w")
            self.file_vars[f] = var

        # Right: Splits
        right_frame = ttk.Frame(frame)
        right_frame.pack(side="left", fill="both", expand=True)

        num_splits = self.split_var.get()
        self.splits = []
        for i in range(num_splits):
            self.add_split_panel(right_frame, i + 1)

        ttk.Button(frame, text="Apply Splits", command=self.apply_splits).pack(side="bottom", pady=10)

    def add_split_panel(self, parent, idx):
        frame = ttk.LabelFrame(parent, text=f"Split {idx}", padding=10)
        frame.pack(fill="both", expand=True, padx=5, pady=5, side="left")

        ttk.Label(frame, text="Branch name:").pack(anchor="w")
        branch_var = tk.StringVar(value=f"split_{idx}")
        ttk.Entry(frame, textvariable=branch_var).pack(fill="x", pady=2)

        listbox = tk.Listbox(frame, height=10, selectmode="extended")
        listbox.pack(fill="both", expand=True, pady=2)

        add_btn = ttk.Button(frame, text="Add Selected", command=lambda: self.add_selected(listbox))
        add_btn.pack(side="left", padx=2)
        rem_btn = ttk.Button(frame, text="Remove", command=lambda: self.remove_selected(listbox))
        rem_btn.pack(side="left", padx=2)

        self.splits.append({"branch": branch_var, "listbox": listbox})

    def add_selected(self, listbox):
        """Move checked files from the main list to the selected split listbox."""
        moved_files = []
        for file, var in list(self.file_vars.items()):
            if var.get():
                listbox.insert("end", file)
                moved_files.append(file)
                var.set(False)

        # Remove added files from main list UI
        for file in moved_files:
            # Find and remove corresponding checkbox
            for child in self.file_checkbox_frame.winfo_children():
                if isinstance(child, ttk.Checkbutton) and child.cget("text") == file:
                    child.destroy()
                    break

            del self.file_vars[file]  # Remove from tracking

    def remove_selected(self, listbox):
        """Remove selected files from a split and return them to the main list."""
        selected = listbox.curselection()
        for i in reversed(selected):
            fname = listbox.get(i)
            listbox.delete(i)

            # Recreate the checkbox in main list
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.file_checkbox_frame, text=fname, variable=var)
            cb.pack(anchor="w")
            self.file_vars[fname] = var

    def apply_splits(self):
        repo = self.repo
        base = "master"

        for split in self.splits:
            branch_name = split["branch"].get()
            files = split["listbox"].get(0, "end")
            if not files:
                continue

            print(f"Would create branch '{branch_name}' with files:")
            for f in files:
                print("  ", f)

        messagebox.showinfo("Done", "Splits processed (dry-run).")

# Run UI
if __name__ == "__main__":
    root = tk.Tk()
    GitSplitUI(root)
    root.mainloop()
