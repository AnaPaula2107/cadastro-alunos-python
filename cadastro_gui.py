# cadastro_gui.py
# Interface gráfica (Tkinter/ttk) para cadastro de alunos com persistência em JSON.
# Recursos:
# - Listagem em Treeview com ordenação por coluna
# - Busca em tempo real por nome
# - Adicionar, editar, remover com validação
# - Mensagens amigáveis e confirmação de exclusão
# - Persistência em alunos.json (compatível com o código original)

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ARQUIVO = Path("alunos.json")


# ---------------------- Persistência ---------------------- #
class StudentManager:
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo
        self.alunos = self._carregar()

    def _carregar(self):
        if self.arquivo.exists():
            try:
                with self.arquivo.open("r", encoding="utf-8") as f:
                    dados = json.load(f)
                    if isinstance(dados, list):
                        # normaliza estrutura e tipos
                        alunos = []
                        for a in dados:
                            if not isinstance(a, dict):
                                continue
                            nome = str(a.get("nome", "")).strip()
                            curso = str(a.get("curso", "")).strip()
                            idade_raw = a.get("idade", "")
                            try:
                                idade = int(idade_raw)
                            except (ValueError, TypeError):
                                # se veio como string ou inválido, ignora até editar
                                idade = None
                            alunos.append({"nome": nome, "idade": idade, "curso": curso})
                        return alunos
                    else:
                        print("Formato JSON inválido (esperado: lista).")
            except json.JSONDecodeError:
                print("Erro ao decodificar o JSON.")
        return []

    def salvar(self):
        # salva idades como inteiros (se houver), mantendo estrutura simples
        with self.arquivo.open("w", encoding="utf-8") as f:
            json.dump(self.alunos, f, ensure_ascii=False, indent=2)

    def adicionar(self, aluno: dict):
        self.alunos.append(aluno)
        self.salvar()

    def atualizar(self, idx: int, aluno: dict):
        if 0 <= idx < len(self.alunos):
            self.alunos[idx] = aluno
            self.salvar()

    def remover(self, idx: int):
        if 0 <= idx < len(self.alunos):
            self.alunos.pop(idx)
            self.salvar()


# ---------------------- Interface ---------------------- #
class CadastroGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cadastro de Alunos (JSON)")
        self.geometry("900x560")
        self._center_on_screen(900, 560)

        # Estilo
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass  # usa padrão se "clam" não estiver disponível
        self.style.configure("TButton", padding=6)
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10))
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("Treeview", rowheight=26)

        # Persistência
        self.manager = StudentManager(ARQUIVO)

        # Variáveis de formulário e busca
        self.nome_var = tk.StringVar()
        self.idade_var = tk.StringVar()
        self.curso_var = tk.StringVar()
        self.search_var = tk.StringVar()

        # Controle de ordenação (coluna, asc=True/False)
        self.sort_state = ("nome", True)

        # Layout
        self._build_header()
        self._build_form()
        self._build_actions()
        self._build_search()
        self._build_list()
        self._build_statusbar()

        self._refresh_tree()

        # Atalhos
        self.bind("<Escape>", lambda e: self._limpar_formulario())
        self.bind("<Control-n>", lambda e: self._limpar_formulario())
        self.bind("<Control-s>", lambda e: self._adicionar_ou_atualizar())

    # ---------------------- Construção de UI ---------------------- #
    def _build_header(self):
        header = ttk.Frame(self, padding=(12, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Sistema de Cadastro de Alunos", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Adicione, edite, busque e remova alunos com persistência em JSON.",
                  style="SubHeader.TLabel", foreground="#555").pack(anchor="w", pady=(2, 0))

    def _build_form(self):
        frm = ttk.LabelFrame(self, text="Cadastro / Edição", padding=12)
        frm.pack(fill="x", padx=12, pady=(4, 6))

        # Nome
        ttk.Label(frm, text="Nome *").grid(row=0, column=0, sticky="w")
        self.nome_entry = ttk.Entry(frm, textvariable=self.nome_var, width=40)
        self.nome_entry.grid(row=1, column=0, sticky="we", padx=(0, 12))

        # Idade
        ttk.Label(frm, text="Idade * (9 a 80)").grid(row=0, column=1, sticky="w")
        self.idade_entry = ttk.Entry(frm, textvariable=self.idade_var, width=12)
        self.idade_entry.grid(row=1, column=1, sticky="w", padx=(0, 12))

        # Curso
        ttk.Label(frm, text="Curso").grid(row=0, column=2, sticky="w")
        self.curso_entry = ttk.Entry(frm, textvariable=self.curso_var, width=28)
        self.curso_entry.grid(row=1, column=2, sticky="we")

        frm.columnconfigure(0, weight=3)
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(2, weight=2)

    def _build_actions(self):
        act = ttk.Frame(self, padding=(12, 0))
        act.pack(fill="x")

        self.btn_add = ttk.Button(act, text="Adicionar (Ctrl+S)", command=self._adicionar_ou_atualizar)
        self.btn_add.pack(side="left")

        self.btn_clear = ttk.Button(act, text="Limpar (Esc)", command=self._limpar_formulario)
        self.btn_clear.pack(side="left", padx=(8, 0))

        self.btn_delete = ttk.Button(act, text="Remover Selecionado", command=self._remover_selecionado, state="disabled")
        self.btn_delete.pack(side="left", padx=(8, 0))

    def _build_search(self):
        sfrm = ttk.LabelFrame(self, text="Busca", padding=12)
        sfrm.pack(fill="x", padx=12, pady=(8, 6))

        ttk.Label(sfrm, text="Filtrar por nome:").pack(side="left")
        ent = ttk.Entry(sfrm, textvariable=self.search_var, width=40)
        ent.pack(side="left", padx=(8, 0), fill="x", expand=True)
        ttk.Button(sfrm, text="Limpar Filtro", command=lambda: self.search_var.set("")).pack(side="left", padx=(8, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_tree())

    def _build_list(self):
        lfrm = ttk.LabelFrame(self, text="Alunos", padding=(8, 6))
        lfrm.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        columns = ("nome", "idade", "curso")
        self.tree = ttk.Treeview(lfrm, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("nome", text="Nome", command=lambda: self._ordenar_por("nome"))
        self.tree.heading("idade", text="Idade", command=lambda: self._ordenar_por("idade"))
        self.tree.heading("curso", text="Curso", command=lambda: self._ordenar_por("curso"))

        self.tree.column("nome", width=280, anchor="w")
        self.tree.column("idade", width=80, anchor="center")
        self.tree.column("curso", width=200, anchor="w")

        vsb = ttk.Scrollbar(lfrm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(lfrm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        lfrm.rowconfigure(0, weight=1)
        lfrm.columnconfigure(0, weight=1)

        # Eventos
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # Menu de contexto
        self.ctx_menu = tk.Menu(self, tearoff=False)
        self.ctx_menu.add_command(label="Editar", command=self._carregar_selecao_no_form)
        self.ctx_menu.add_command(label="Remover", command=self._remover_selecionado)
        self.tree.bind("<Button-3>", self._abrir_context_menu)

    def _build_statusbar(self):
        self.status = ttk.Label(self, text="", anchor="w", padding=(12, 6))
        self.status.pack(fill="x")

    # ---------------------- Utilitários ---------------------- #
    def _center_on_screen(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _ordenar_por(self, coluna):
        col_atual, asc = self.sort_state
        if col_atual == coluna:
            asc = not asc
        else:
            asc = True
        self.sort_state = (coluna, asc)
        self._refresh_tree()

    def _filtrar(self, alunos):
        termo = self.search_var.get().strip().lower()
        if not termo:
            return list(enumerate(alunos))
        encontrados = []
        for idx, a in enumerate(alunos):
            if termo in a.get("nome", "").lower():
                encontrados.append((idx, a))
        return encontrados

    def _ordenar(self, pares):
        # pares: [(idx_original, aluno_dict), ...]
        coluna, asc = self.sort_state
        def key_func(item):
            _, a = item
            v = a.get(coluna)
            # normaliza valores para comparação
            if v is None:
                return "" if coluna != "idade" else -1
            if coluna == "idade":
                try:
                    return int(v)
                except (ValueError, TypeError):
                    return -1
            return str(v).lower()
        return sorted(pares, key=key_func, reverse=not asc)

    def _refresh_tree(self):
        # Limpa
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Filtra e ordena (mantendo referência ao índice original)
        pares = self._filtrar(self.manager.alunos)
        pares = self._ordenar(pares)

        # Popula. Usamos iid = índice original para mapear operações (editar/excluir).
        for idx_original, a in pares:
            nome = a.get("nome", "")
            idade = a.get("idade", "")
            curso = a.get("curso", "")
            self.tree.insert("", "end", iid=str(idx_original), values=(nome, idade if idade is not None else "", curso))

        total = len(self.manager.alunos)
        filtrados = len(pares)
        msg = f"Total: {total} aluno(s)"
        if filtrados != total:
            msg += f" | Exibindo: {filtrados}"
        col, asc = self.sort_state
        seta = "▲" if asc else "▼"
        msg += f" | Ordenado por: {col} {seta}"
        self.status.config(text=msg)

        # Estado dos botões
        self._atualizar_estado_botoes()

    def _atualizar_estado_botoes(self):
        sel = self.tree.selection()
        self.btn_delete.config(state=("normal" if sel else "disabled"))
        # texto do botão principal muda conforme há seleção:
        self.btn_add.config(text="Atualizar (Ctrl+S)" if sel else "Adicionar (Ctrl+S)")

    def _abrir_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _on_select(self, _event):
        self._atualizar_estado_botoes()

    def _on_double_click(self, _event):
        self._carregar_selecao_no_form()

    def _carregar_selecao_no_form(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        aluno = self.manager.alunos[idx]
        self.nome_var.set(aluno.get("nome", ""))
        self.curso_var.set(aluno.get("curso", ""))
        idade = aluno.get("idade", "")
        self.idade_var.set("" if idade is None else str(idade))
        self.nome_entry.focus_set()

    def _limpar_formulario(self):
        self.nome_var.set("")
        self.idade_var.set("")
        self.curso_var.set("")
        self.tree.selection_remove(*self.tree.selection())
        self._atualizar_estado_botoes()
        self.nome_entry.focus_set()

    # ---------------------- Ações ---------------------- #
    def _validar_campos(self):
        nome = self.nome_var.get().strip()
        if not nome:
            messagebox.showwarning("Validação", "O campo Nome é obrigatório.")
            return None
        idade_txt = self.idade_var.get().strip()
        if not idade_txt.isdigit():
            messagebox.showwarning("Validação", "Idade deve ser um número inteiro entre 9 e 80.")
            return None
        idade = int(idade_txt)
        if idade < 9 or idade > 80:
            messagebox.showwarning("Validação", "Idade não permitida. Válido de 9 a 80 anos.")
            return None
        curso = self.curso_var.get().strip()
        return {"nome": nome, "idade": idade, "curso": curso}

    def _adicionar_ou_atualizar(self):
        dados = self._validar_campos()
        if not dados:
            return

        sel = self.tree.selection()
        if sel:
            # Atualiza registro selecionado
            idx = int(sel[0])
            self.manager.atualizar(idx, dados)
            messagebox.showinfo("Sucesso", "Dados do aluno atualizados com sucesso!")
        else:
            # Adiciona novo
            self.manager.adicionar(dados)
            messagebox.showinfo("Sucesso", "Aluno cadastrado com sucesso!")

        self._refresh_tree()
        self._limpar_formulario()

    def _remover_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        aluno = self.manager.alunos[idx]
        nome = aluno.get("nome", "Aluno")

        if messagebox.askyesno("Confirmar remoção", f"Deseja remover '{nome}'?"):
            self.manager.remover(idx)
            self._refresh_tree()
            self._limpar_formulario()
            messagebox.showinfo("Removido", f"Aluno '{nome}' removido com sucesso.")

# ---------------------- Execução ---------------------- #
if __name__ == "__main__":
    app = CadastroGUI()
    app.mainloop()