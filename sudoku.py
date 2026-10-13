import tkinter as tk
from tkinter import messagebox
import random

SIZE = 9


def build_peers():
    peers = {}
    for r in range(SIZE):
        for c in range(SIZE):
            s = set()
            for i in range(SIZE):
                s.add((r, i))
                s.add((i, c))
            br, bc = (r // 3) * 3, (c // 3) * 3
            for i in range(br, br + 3):
                for j in range(bc, bc + 3):
                    s.add((i, j))
            s.discard((r, c))
            peers[(r, c)] = s
    return peers


PEERS = build_peers()


class SudokuCSP:
    def __init__(self, grid, randomize=False):
        self.grid = [row[:] for row in grid]
        self.randomize = randomize
        self.nodes = 0
        self.backtracks = 0

    def _givens_consistent(self):
        for r in range(SIZE):
            for c in range(SIZE):
                v = self.grid[r][c]
                if v:
                    for pr, pc in PEERS[(r, c)]:
                        if self.grid[pr][pc] == v:
                            return False
        return True

    def _initial_domains(self):
        domains = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] == 0:
                    domains[(r, c)] = set(range(1, 10))
        for r in range(SIZE):
            for c in range(SIZE):
                v = self.grid[r][c]
                if v:
                    for p in PEERS[(r, c)]:
                        if p in domains:
                            domains[p].discard(v)
        return domains

    def _select_variable(self, domains):
        min_size = min(len(d) for d in domains.values())
        candidates = [v for v, d in domains.items() if len(d) == min_size]
        if len(candidates) == 1:
            return candidates[0]
        return max(candidates,
                   key=lambda v: sum(1 for p in PEERS[v] if p in domains))

    def _order_values(self, var, domains):
        def conflicts(val):
            return sum(1 for p in PEERS[var] if p in domains and val in domains[p])

        values = list(domains[var])
        if self.randomize:
            random.shuffle(values)
        return sorted(values, key=conflicts)

    def _backtrack(self, domains, solutions, limit):
        if not domains:
            solutions.append([row[:] for row in self.grid])
            return len(solutions) >= limit

        self.nodes += 1
        var = self._select_variable(domains)
        r, c = var

        for val in self._order_values(var, domains):
            new_domains = {k: set(v) for k, v in domains.items() if k != var}
            ok = True
            for p in PEERS[var]:
                if p in new_domains:
                    new_domains[p].discard(val)
                    if not new_domains[p]:
                        ok = False
                        break

            if ok:
                self.grid[r][c] = val
                if self._backtrack(new_domains, solutions, limit):
                    return True
                self.grid[r][c] = 0

            self.backtracks += 1
        return False

    def solve(self, limit=1):
        self.nodes = 0
        self.backtracks = 0
        if not self._givens_consistent():
            return []
        solutions = []
        self._backtrack(self._initial_domains(), solutions, limit)
        return solutions


def generate_puzzle(holes=50):
    full = SudokuCSP([[0] * SIZE for _ in range(SIZE)], randomize=True).solve(1)[0]
    puzzle = [row[:] for row in full]

    cells = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    random.shuffle(cells)

    removed = 0
    for r, c in cells:
        if removed >= holes:
            break
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        if len(SudokuCSP(puzzle).solve(limit=2)) == 1:
            removed += 1
        else:
            puzzle[r][c] = backup
    return puzzle, full


class SudokuApp:
    def __init__(self, root):
        self.root = root
        root.title("Sudoku - CSP (MRV + Degree + LCV)")
        root.resizable(False, False)

        self.solution = None
        self.givens = set()
        self.entries = {}

        vcmd = (root.register(self._validate), "%P")

        board = tk.Frame(root, bg="black", padx=3, pady=3)
        board.pack(padx=10, pady=(10, 5))

        for br in range(3):
            for bc in range(3):
                block = tk.Frame(board, bg="black")
                block.grid(row=br, column=bc, padx=2, pady=2)
                for i in range(3):
                    for j in range(3):
                        r, c = br * 3 + i, bc * 3 + j
                        e = tk.Entry(block, width=2, font=("Arial", 20, "bold"),
                                     justify="center", bd=0, relief="flat",
                                     validate="key", validatecommand=vcmd)
                        e.grid(row=i, column=j, padx=1, pady=1, ipady=6)
                        self.entries[(r, c)] = e

        btns = tk.Frame(root)
        btns.pack(pady=5)
        tk.Button(btns, text="Шинэ тоглоом", width=14,
                  command=self.new_game).grid(row=0, column=0, padx=4)
        tk.Button(btns, text="Шалгах", width=12,
                  command=self.check).grid(row=0, column=1, padx=4)
        tk.Button(btns, text="CSP-ээр бодох", width=14,
                  command=self.solve_csp).grid(row=0, column=2, padx=4)

        self.status = tk.Label(root, text="", font=("Arial", 11))
        self.status.pack(pady=(5, 10))

        self.new_game()

    def _validate(self, P):
        return P == "" or (len(P) == 1 and P in "123456789")

    def new_game(self):
        puzzle, self.solution = generate_puzzle(holes=50)
        self.givens = set()
        for (r, c), e in self.entries.items():
            v = puzzle[r][c]
            e.config(state="normal")
            e.delete(0, "end")
            if v:
                e.insert(0, str(v))
                e.config(state="readonly", readonlybackground="#dcdcdc", fg="black")
                self.givens.add((r, c))
            else:
                e.config(bg="white", fg="#1a4fd6")
        self.status.config(text="Шинэ тоглоом эхэллээ.")

    def read_grid(self):
        grid = [[0] * SIZE for _ in range(SIZE)]
        for (r, c), e in self.entries.items():
            t = e.get().strip()
            if t.isdigit():
                grid[r][c] = int(t)
        return grid

    def check(self):
        wrong = False
        complete = True
        for (r, c), e in self.entries.items():
            if (r, c) in self.givens:
                continue
            t = e.get().strip()
            if not t:
                complete = False
                e.config(bg="white")
                continue
            if int(t) != self.solution[r][c]:
                wrong = True
                e.config(bg="#ffb3b3")
            else:
                e.config(bg="white")

        if wrong:
            self.status.config(text="Буруу утгууд улаанаар тэмдэглэгдлээ.")
        elif complete:
            messagebox.showinfo("Баяр хүргэе!", "Sudoku-г амжилттай бодлоо!")
            self.status.config(text="Гайхалтай! Тоглоом дууслаа.")
        else:
            self.status.config(text="Сайн явж байна, үргэлжлүүлээрэй.")

    def solve_csp(self):
        grid = self.read_grid()
        solver = SudokuCSP(grid)
        sols = solver.solve(limit=1)
        if not sols:
            messagebox.showwarning("Шийдэлгүй",
                                   "Одоогийн самбар зөрчилтэй эсвэл шийдэлгүй байна.")
            return

        sol = sols[0]
        for (r, c), e in self.entries.items():
            if grid[r][c] == 0:
                e.config(state="normal")
                e.delete(0, "end")
                e.insert(0, str(sol[r][c]))
                e.config(fg="#2e7d32", bg="white")
        self.status.config(
            text=f"CSP (MRV+Degree+LCV): {solver.nodes} төлөв, "
                 f"{solver.backtracks} буцалт")


if __name__ == "__main__":
    root = tk.Tk()
    SudokuApp(root)
    root.mainloop()