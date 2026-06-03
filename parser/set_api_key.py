"""
Tiny GUI to enter / update the ANTHROPIC_API_KEY in the project .env file.
Run:  python set_api_key.py
"""
import os
import re
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
KEY = "ANTHROPIC_API_KEY"


def write_key(value: str):
    value = value.strip()
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    found = False
    for i, ln in enumerate(lines):
        if re.match(rf"^\s*{KEY}\s*=", ln):
            lines[i] = f"{KEY}={value}"
            found = True
            break
    if not found:
        lines.append(f"{KEY}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def on_save():
    val = entry.get().strip()
    if not val:
        messagebox.showwarning("缺少金鑰", "請貼上 API Key")
        return
    if not val.startswith("sk-"):
        if not messagebox.askyesno("確認", "金鑰看起來不像 sk- 開頭，仍要儲存嗎？"):
            return
    try:
        write_key(val)
    except Exception as e:
        messagebox.showerror("寫入失敗", str(e))
        return
    masked = val[:7] + "…" + val[-4:] if len(val) > 12 else "(已儲存)"
    messagebox.showinfo("完成", f"已寫入 .env\n{KEY}={masked}\n\n{ENV_PATH}")
    root.destroy()


def toggle_show():
    entry.config(show="" if show_var.get() else "*")


root = tk.Tk()
root.title("Innodisk Parser — API Key")
root.geometry("520x190")
root.resizable(False, False)
root.attributes("-topmost", True)

tk.Label(root, text="貼上你的 ANTHROPIC_API_KEY：", font=("Segoe UI", 11)).pack(
    anchor="w", padx=16, pady=(16, 4)
)

entry = tk.Entry(root, width=58, show="*", font=("Consolas", 10))
entry.pack(padx=16)
entry.focus_set()

show_var = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="顯示金鑰", variable=show_var,
               command=toggle_show).pack(anchor="w", padx=14, pady=(4, 0))

tk.Label(root, text=f"將寫入：{ENV_PATH}", fg="#666",
         font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(2, 0))

btns = tk.Frame(root)
btns.pack(pady=12)
tk.Button(btns, text="儲存", width=12, command=on_save,
          default="active").pack(side="left", padx=6)
tk.Button(btns, text="取消", width=12, command=root.destroy).pack(side="left", padx=6)

root.bind("<Return>", lambda e: on_save())
root.bind("<Escape>", lambda e: root.destroy())
root.mainloop()
