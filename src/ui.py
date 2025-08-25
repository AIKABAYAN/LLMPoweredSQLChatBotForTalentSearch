import uuid
import time
import datetime as dt
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

from src.config import logger
from src.intent_parser import call_ollama_intent
from src.query_executor import run_all_queries
from src.formatter import format_employee_summary, format_bucketed_sentences
from src.sql_builder import build_clauses, ROLE_SQL, PROJECT_SQL, EDU_SQL, TIMESHEET_SQL
from src.logger_helper import append_sql_log

# ReportLab untuk export PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# =============================================
# UI Application
# =============================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("Talent Search Chatbot v15 (Export PDF)")  # PRD v15
        root.geometry("1180x760")

        self.employee_summary_var = tk.BooleanVar(value=True)
        self.start_date_var = tk.StringVar(value="")
        self.end_date_var = tk.StringVar(value="")

        self.last_raw = None
        self.last_employees = []
        self.session_id = None
        self.last_intent = None

        self._build_ui()
        self.entry.insert(0, "recommend me Technical Leader  java  python core banking, experience > 5 years")

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

        # Chat tab
        chat = ttk.Frame(nb)
        nb.add(chat, text="Chat")

        top = ttk.Frame(chat)
        top.pack(fill="x", padx=10, pady=6)
        ttk.Label(top, text="Timesheet Start (YYYY-MM-DD)").pack(side=tk.LEFT)
        ttk.Entry(top, width=12, textvariable=self.start_date_var).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(top, text="End").pack(side=tk.LEFT)
        ttk.Entry(top, width=12, textvariable=self.end_date_var).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Checkbutton(top, text="Employee Summary", variable=self.employee_summary_var).pack(side=tk.LEFT)

        self.chat_box = scrolledtext.ScrolledText(chat, wrap=tk.WORD, width=120, height=28)
        self.chat_box.pack(padx=10, pady=6, fill="both", expand=True)

        bottom = ttk.Frame(chat)
        bottom.pack(fill="x", padx=10, pady=8)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Button(bottom, text="Send", command=self.on_send).pack(side=tk.LEFT, padx=8)

        # SQL Logs tab
        logs = ttk.Frame(nb)
        nb.add(logs, text="SQL Logs")
        self.sql_log_box = scrolledtext.ScrolledText(logs, wrap=tk.WORD)
        self.sql_log_box.pack(fill="both", expand=True, padx=10, pady=10)

        # Results tab
        results = ttk.Frame(nb)
        nb.add(results, text="Results")

        # Table + details splitter
        upper = ttk.Frame(results)
        upper.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        self.tree = ttk.Treeview(upper, columns=("employee_id", "name", "score"), show="headings", height=12)
        self.tree.heading("employee_id", text="Employee ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("score", text="Score")
        self.tree.column("employee_id", width=120, anchor=tk.W)
        self.tree.column("name", width=420, anchor=tk.W)
        self.tree.column("score", width=80, anchor=tk.E)
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)

        vsb = ttk.Scrollbar(upper, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.LEFT, fill="y")

        right = ttk.Frame(upper)
        right.pack(side=tk.LEFT, fill="both", expand=True, padx=(10, 0))

        ttk.Label(right, text="Scoring Breakdown").pack(anchor="w")
        self.breakdown_box = scrolledtext.ScrolledText(right, wrap=tk.WORD, height=10)
        self.breakdown_box.pack(fill="both", expand=True)

        ttk.Label(right, text="Employee Summary (preview)").pack(anchor="w", pady=(8, 0))
        self.summary_box = scrolledtext.ScrolledText(right, wrap=tk.WORD, height=12)
        self.summary_box.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Buttons bar
        btnbar = ttk.Frame(results)
        btnbar.pack(fill="x", padx=10, pady=6)
        ttk.Button(btnbar, text="Export CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btnbar, text="Export PDF", command=self.export_pdf).pack(side=tk.RIGHT)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = str(self.tree.item(sel[0], "values")[0])  # employee_id
        emp = next((e for e in self.last_employees if str(e.get("employee_id")) == idx), None)

        self.breakdown_box.delete("1.0", tk.END)
        self.summary_box.delete("1.0", tk.END)

        if not emp:
            return

        # Breakdown
        br = emp.get("scoring_breakdown", []) or []
        if br:
            self.breakdown_box.insert(tk.END, "\n".join(f"- {x}" for x in br))
        else:
            self.breakdown_box.insert(tk.END, "(no breakdown)")

        # Summary preview
        try:
            self.summary_box.insert(tk.END, format_employee_summary(emp, self.last_intent))
        except Exception as e:
            self.summary_box.insert(tk.END, f"(cannot render summary: {e})")

    def on_send(self):
        user_query = self.entry.get().strip()
        if not user_query:
            return
        self.entry.delete(0, tk.END)

        self.session_id = str(uuid.uuid4())[:8]
        sid = self.session_id
        logger.info(f"[{sid}] User query: {user_query}")
        self.chat_box.insert(tk.END, f"You: {user_query}\n")

        # ===== Parse Intent =====
        t0 = time.perf_counter()
        intent, prompt = call_ollama_intent(user_query)
        self.last_intent = intent

        start = self.start_date_var.get().strip()
        end = self.end_date_var.get().strip()
        if start or end:
            intent.setdefault("timesheet", {})
            if start:
                intent["timesheet"]["start_date"] = start
            if end:
                intent["timesheet"]["end_date"] = end
        t1 = time.perf_counter()

        # ===== Run Queries =====
        employees, raw, sql_time = run_all_queries(intent, sid)
        t2 = time.perf_counter()

        self.last_raw = raw
        self.last_employees = employees

        # ===== Primary/Backup =====
        lim = intent.get("limit", {}) or {}
        n_primary = int(lim.get("primary", 3))
        n_backup = int(lim.get("backup", 2))
        primary = employees[:n_primary]
        backup = employees[n_primary:n_primary + n_backup]

        primary_tuples = [(e, e.get("score", 0)) for e in primary]
        backup_tuples = [(e, e.get("score", 0)) for e in backup]

        parse_time = t1 - t0
        merge_time = t2 - t1
        total_time = t2 - t0

        logger.info(
            f"[{sid}] Done: {len(primary)} recommended, {len(backup)} backup | "
            f"Parse={parse_time:.2f}s SQL+Merge+Score={merge_time:.2f}s Total={total_time:.2f}s"
        )

        # ✅ Show different message if query was name-only
        if intent.get("name"):
            prompt_top = f"Searching for candidate: {intent['name']}"
        else:
            must = intent.get("skills", {}).get("must_have", [])
            nice = intent.get("skills", {}).get("nice_to_have", [])
            prompt_top = f"Prompt: role={intent.get('role','')}, Must Have={must}, Nice To Have={nice}"

        self.chat_box.insert(tk.END, prompt_top + "\n")
        self.chat_box.insert(
            tk.END,
            f"Processing Time: {total_time:.2f}s (LLM {parse_time:.2f}s, SQL+Merge+Score {merge_time:.2f}s)\n\n"
        )

        if self.employee_summary_var.get():
            self.chat_box.insert(tk.END, f"--- Recommended Talents ({len(primary)}) ---\n\n")
            for emp in primary:
                self.chat_box.insert(tk.END, format_employee_summary(emp, intent) + "\n")
            self.chat_box.insert(tk.END, f"--- Backup Talents ({len(backup)}) ---\n\n")
            for emp in backup:
                self.chat_box.insert(tk.END, format_employee_summary(emp, intent) + "\n")
        else:
            self.chat_box.insert(tk.END, f"--- Recommended Talents ({len(primary)}) ---\n")
            self.chat_box.insert(tk.END, format_bucketed_sentences(primary_tuples) + "\n\n")
            self.chat_box.insert(tk.END, f"--- Backup Talents ({len(backup)}) ---\n")
            self.chat_box.insert(tk.END, format_bucketed_sentences(backup_tuples) + "\n\n")

        self._populate_results_table(employees)

        # ===== SQL Logs =====
        clauses = build_clauses(intent)
        role_clause, skill_clause, role_params, name_clause = clauses["role"]
        proj_clause, proj_params, name_clause2 = clauses["project"]
        edu_clause, edu_params, name_clause3 = clauses["education"]
        ts_date_clause, ts_proj_clause, ts_params, name_clause4 = clauses["timesheet"]

        q_role = ROLE_SQL.format(role_clause=role_clause, skill_clause=skill_clause, name_clause=name_clause)
        q_proj = PROJECT_SQL.format(proj_clause=proj_clause, name_clause=name_clause2)
        q_edu = EDU_SQL.format(edu_clause=edu_clause, name_clause=name_clause3)
        q_ts = TIMESHEET_SQL.format(ts_date_clause=ts_date_clause, ts_proj_clause=ts_proj_clause, name_clause=name_clause4)

        log_blob = (
            f"[{dt.datetime.now().isoformat()}] {user_query}\n"
            f"{q_role}\nparams={role_params}\n"
            f"{q_proj}\nparams={proj_params}\n"
            f"{q_edu}\nparams={edu_params}\n"
            f"{q_ts}\nparams={ts_params}\n\n"
        )
        self.sql_log_box.insert(tk.END, log_blob)
        append_sql_log(f"User: {user_query}", [q_role, q_proj, q_edu, q_ts])

    def _populate_results_table(self, employees):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, emp in enumerate(employees):
            emp_id = emp.get("employee_id")
            name = emp.get("full_name", f"EMP-{emp_id}")
            score = emp.get("score", 0)
            self.tree.insert("", tk.END, text=str(idx), values=(emp_id, name, score))

        self.breakdown_box.delete("1.0", tk.END)
        self.summary_box.delete("1.0", tk.END)

    def export_csv(self):
        if not self.last_raw:
            messagebox.showwarning("Export", "No results to export yet.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"results_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not file_path:
            return
        try:
            import csv
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for name in ("roles", "projects", "education", "timesheet"):
                    rows = self.last_raw.get(name, [])
                    writer.writerow([name])
                    if not rows:
                        writer.writerow(["(empty)"])
                        writer.writerow([])
                        continue
                    cols = list(rows[0].keys())
                    writer.writerow(cols)
                    for r in rows:
                        writer.writerow([r.get(c) for c in cols])
                    writer.writerow([])
            logger.info(f"[{self.session_id}] CSV exported: {file_path}")
            messagebox.showinfo("Export", "CSV exported successfully.")
        except Exception as e:
            logger.exception("CSV export failed: %s", e)
            messagebox.showerror("Export failed", str(e))

    def export_pdf(self):
        if not self.last_employees:
            messagebox.showwarning("Export", "No results to export yet.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"results_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        )
        if not file_path:
            return
        try:
            styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elems = []

            elems.append(Paragraph("<b>Talent Search Report</b>", styles["Title"]))
            elems.append(Paragraph(f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
            elems.append(Spacer(1, 12))

            if self.last_intent:
                elems.append(Paragraph(f"<b>User Query Summary</b>", styles["Heading2"]))

                if self.last_intent.get("name"):
                    elems.append(Paragraph(f"Candidate Search for: {self.last_intent['name']}", styles["Normal"]))
                else:
                    role = self.last_intent.get("role", "")
                    must = self.last_intent.get("skills", {}).get("must_have", [])
                    nice = self.last_intent.get("skills", {}).get("nice_to_have", [])
                    elems.append(Paragraph(f"Role: {role}", styles["Normal"]))
                    elems.append(Paragraph(f"Must Have Skills: {', '.join(must)}", styles["Normal"]))
                    elems.append(Paragraph(f"Nice to Have Skills: {', '.join(nice)}", styles["Normal"]))

                elems.append(Spacer(1, 12))

            elems.append(Paragraph("<b>Candidates</b>", styles["Heading2"]))
            for i, emp in enumerate(self.last_employees, 1):
                summary = format_employee_summary(emp, self.last_intent).splitlines()
                elems.append(Paragraph(f"{i}. {summary[0]}", styles["Heading3"]))  # Name line
                for line in summary[1:]:
                    if not line.strip():
                        elems.append(Spacer(1, 6))
                    else:
                        elems.append(Paragraph(line, styles["Normal"]))
                elems.append(Spacer(1, 12))

            doc.build(elems)
            logger.info(f"[{self.session_id}] PDF exported: {file_path}")
            messagebox.showinfo("Export", "PDF exported successfully.")
        except Exception as e:
            logger.exception("PDF export failed: %s", e)
            messagebox.showerror("Export failed", str(e))
