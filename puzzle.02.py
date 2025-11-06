import tkinter as tk
from tkinter import messagebox
import heapq
import time
import threading
import queue
import random

# =======================================================================
# --- Part 1: A* Solver Logic (Unchanged) ---
# =======================================================================

class PuzzleNode:
    """A node in the A* search tree for the 8-puzzle."""
    
    def __init__(self, state, parent=None, move=None, g_cost=0):
        self.state = state
        self.parent = parent
        self.move = move
        self.g_cost = g_cost
        self.h_cost = 0
        self.f_cost = 0

    def __lt__(self, other):
        """Allows nodes to be compared based on their f_cost for the priority queue."""
        return self.f_cost < other.f_cost

def calculate_manhattan_distance(state, goal_state):
    """Calculates the Manhattan distance heuristic for a given state."""
    distance = 0
    goal_positions = {tile: i for i, tile in enumerate(goal_state)}

    for i, tile in enumerate(state):
        if tile == 0:  # Skip the blank tile
            continue
        
        current_row, current_col = divmod(i, 3)
        goal_pos = goal_positions[tile]
        goal_row, goal_col = divmod(goal_pos, 3)
        
        distance += abs(current_row - goal_row) + abs(current_col - goal_col)
        
    return distance

def get_neighbors(node, goal_state):
    """Generates all valid successor nodes (neighbors) from the current node."""
    neighbors = []
    state_list = list(node.state)
    blank_index = state_list.index(0)
    blank_row, blank_col = divmod(blank_index, 3)

    possible_moves = [
        (-1, 0, 'UP'), (1, 0, 'DOWN'),
        (0, -1, 'LEFT'), (0, 1, 'RIGHT')
    ]

    for dr, dc, move_name in possible_moves:
        new_row, new_col = blank_row + dr, blank_col + dc

        if 0 <= new_row < 3 and 0 <= new_col < 3:
            swap_index = new_row * 3 + new_col
            new_state_list = list(state_list)
            new_state_list[blank_index], new_state_list[swap_index] = \
                new_state_list[swap_index], new_state_list[blank_index]
            
            new_state_tuple = tuple(new_state_list)
            neighbor_node = PuzzleNode(new_state_tuple, 
                                       parent=node, 
                                       move=move_name, 
                                       g_cost=node.g_cost + 1)
            
            neighbor_node.h_cost = calculate_manhattan_distance(new_state_tuple, goal_state)
            neighbor_node.f_cost = neighbor_node.g_cost + neighbor_node.h_cost
            neighbors.append(neighbor_node)
            
    return neighbors

def reconstruct_path(node):
    """Traces back from the goal node to get the solution path."""
    path = []
    current = node
    while current:
        path.append(current.state) # We only need the states for animation
        current = current.parent
    return path[::-1]  # Reverse the path to show from start to goal

def solve_puzzle(initial_state, goal_state, result_queue):
    """
    Solves the 8-puzzle using A* and puts the result in a queue.
    This function is designed to be run in a separate thread.
    """
    # --- Solvability Check ---
    inversions = 0
    flat_state = [i for i in initial_state if i != 0]
    for i in range(len(flat_state)):
        for j in range(i + 1, len(flat_state)):
            if flat_state[i] > flat_state[j]:
                inversions += 1
    
    if inversions % 2 != 0:
        solution_info = {"unsolvable": True}
        result_queue.put(solution_info)
        return
    # --- End of Solvability Check ---

    start_time = time.time()
    start_node = PuzzleNode(initial_state, g_cost=0)
    start_node.h_cost = calculate_manhattan_distance(initial_state, goal_state)
    start_node.f_cost = start_node.g_cost + start_node.h_cost

    open_set = []
    unique_id = 0
    heapq.heappush(open_set, (start_node.f_cost, unique_id, start_node))
    closed_set = set()
    open_set_g_costs = {initial_state: 0}

    while open_set:
        current_f, _, current_node = heapq.heappop(open_set)
        
        if current_node.state == goal_state:
            end_time = time.time()
            path = reconstruct_path(current_node)
            solution_info = {
                "unsolvable": False,
                "path": path,
                "time": end_time - start_time,
                "moves": current_node.g_cost,
                "explored": len(closed_set)
            }
            result_queue.put(solution_info) # Put solution in the queue
            return

        closed_set.add(current_node.state)

        for neighbor in get_neighbors(current_node, goal_state):
            if neighbor.state in closed_set:
                continue
            
            new_g_cost = neighbor.g_cost
            if neighbor.state in open_set_g_costs and new_g_cost >= open_set_g_costs[neighbor.state]:
                continue
                
            open_set_g_costs[neighbor.state] = new_g_cost
            unique_id += 1
            heapq.heappush(open_set, (neighbor.f_cost, unique_id, neighbor))

    result_queue.put(None) # No solution found


# =======================================================================
# --- Part 2: Tkinter GUI Application ---
# =======================================================================

class PuzzleGUI(tk.Tk):
    def __init__(self, initial_state, goal_state):
        super().__init__()
        self.title("AI 8-Puzzle Solver")
        self.geometry("350x550") # <-- Made window taller for input
        
        self.initial_state = initial_state
        self.goal_state = goal_state
        self.current_state = initial_state
        self.solution_path = []
        self.animation_index = 0
        self.allow_user_moves = True
        
        # --- Configure Colors and Fonts ---
        self.tile_colors = {
            0: "#CDC0B4", 1: "#EEE4DA", 2: "#EDE0C8",
            3: "#F2B179", 4: "#F59563", 5: "#F67C5F",
            6: "#F65E3B", 7: "#EDCF72", 8: "#EDCC61",
        }
        self.tile_font = ("Arial", 30, "bold")
        self.button_font = ("Arial", 12, "bold")
        self.input_font = ("Arial", 10)

        # --- NEW: Create Input Frame (at the top) ---
        self.input_frame = tk.Frame(self)
        self.input_frame.pack(pady=10)
        
        self.input_label = tk.Label(self.input_frame, 
                                     text="Enter state (e.g., 1,2,3,7,4,5,0,8,6):",
                                     font=self.input_font)
        self.input_label.pack()
        
        self.input_entry = tk.Entry(self.input_frame, width=35, font=self.input_font)
        self.input_entry.pack(side="left", padx=(10, 5))
        
        self.set_button = tk.Button(self.input_frame, text="Set",
                                     font=self.button_font,
                                     command=self.set_board_from_input)
        self.set_button.pack(side="left")

        # --- Create Main Frames ---
        self.grid_frame = tk.Frame(self, bg="#92877d", bd=4)
        self.grid_frame.pack(pady=10, padx=20)
        
        self.control_frame = tk.Frame(self)
        self.control_frame.pack(fill="x", padx=20)

        # --- Create Widgets ---
        self.tile_labels = []
        for i in range(9):
            row, col = divmod(i, 3)
            label = tk.Label(self.grid_frame, text="", width=4, height=2,
                              font=self.tile_font, relief="raised", bd=2)
            label.grid(row=row, column=col, padx=3, pady=3)
            label.bind("<Button-1>", lambda event, index=i: self.on_tile_click(index))
            self.tile_labels.append(label)
            
        self.status_label = tk.Label(self.control_frame, text="Set up your puzzle or click 'Shuffle'",
                                     font=("Arial", 12, "italic"), pady=10)
        self.status_label.pack()
        
        self.button_frame = tk.Frame(self.control_frame)
        self.button_frame.pack()

        self.shuffle_button = tk.Button(self.button_frame, text="Shuffle",
                                      font=self.button_font, bg="#8f7a66",
                                      fg="white", command=self.shuffle_board)
        self.shuffle_button.pack(side="left", expand=True, padx=5)

        self.solve_button = tk.Button(self.button_frame, text="Solve",
                                      font=self.button_font, bg="#8f7a66",
                                      fg="white", command=self.start_solve_thread)
        self.solve_button.pack(side="left", expand=True, padx=5)
        
        self.reset_button = tk.Button(self.button_frame, text="Reset",
                                      font=self.button_font, bg="#8f7a66",
                                      fg="white", command=self.reset_board)
        self.reset_button.pack(side="left", expand=True, padx=5)

        # --- Initialize Board and Solver Queue ---
        self.update_board_display(self.current_state)
        self.input_entry.insert(0, ",".join(map(str, self.current_state))) # Pre-fill
        self.solver_queue = queue.Queue()


    def set_board_from_input(self):
        """NEW: Validates and sets the board from the text entry."""
        if not self.allow_user_moves: return # Don't set if solving

        input_str = self.input_entry.get().strip()
        
        # Clean the input string
        parts = input_str.replace(" ", "").split(',')
        
        try:
            # Try to convert all parts to integers
            nums = [int(p) for p in parts if p]
        except ValueError:
            messagebox.showerror("Invalid Input", 
                                 "Input must be numbers separated by commas.")
            return

        # Validation 1: Check for 9 numbers
        if len(nums) != 9:
            messagebox.showerror("Invalid Input", 
                                 f"Must have exactly 9 numbers. You entered {len(nums)}.")
            return

        # Validation 2: Check for all digits 0-8
        if sorted(nums) != list(range(9)):
            messagebox.showerror("Invalid Input", 
                                 "Must include all numbers from 0 to 8 exactly once.")
            return

        # If all checks pass:
        self.current_state = tuple(nums)
        self.initial_state = self.current_state
        self.update_board_display(self.current_state)
        self.status_label.config(text="New board set. Click 'Solve'.")
        self.reset_board() # Reset buttons to normal state


    def update_board_display(self, state_tuple):
        """Updates the 3x3 grid labels to match the given state."""
        self.current_state = state_tuple 
        for i, tile_num in enumerate(state_tuple):
            label = self.tile_labels[i]
            if tile_num == 0:
                label.config(text="", bg=self.tile_colors[0])
            else:
                label.config(text=str(tile_num), 
                             bg=self.tile_colors.get(tile_num, "#CCC"),
                             fg="#776E65")
        self.update_idletasks()


    def on_tile_click(self, clicked_index):
        """Handles a user click on a tile."""
        if not self.allow_user_moves:
            return

        state_list = list(self.current_state)
        blank_index = state_list.index(0)
        
        clicked_row, clicked_col = divmod(clicked_index, 3)
        blank_row, blank_col = divmod(blank_index, 3)
        is_adjacent = abs(clicked_row - blank_row) + abs(clicked_col - blank_col) == 1
        
        if is_adjacent:
            state_list[blank_index], state_list[clicked_index] = \
                state_list[clicked_index], state_list[blank_index]
            
            self.current_state = tuple(state_list)
            self.initial_state = self.current_state
            self.update_board_display(self.current_state)
            self.input_entry.delete(0, tk.END) # Update entry box
            self.input_entry.insert(0, ",".join(map(str, self.current_state)))
            self.status_label.config(text="Board set. Click 'Solve' to begin.")


    def shuffle_board(self):
        """Generates a new, random, solvable puzzle."""
        self.allow_user_moves = True
        self.solve_button.config(state="normal")
        
        state = list(self.goal_state)
        for _ in range(100):
            blank_index = state.index(0)
            blank_row, blank_col = divmod(blank_index, 3)
            
            valid_moves = []
            if blank_row > 0: valid_moves.append(blank_index - 3) # Up
            if blank_row < 2: valid_moves.append(blank_index + 3) # Down
            if blank_col > 0: valid_moves.append(blank_index - 1) # Left
            if blank_col < 2: valid_moves.append(blank_index + 1) # Right
                
            swap_index = random.choice(valid_moves)
            state[blank_index], state[swap_index] = state[swap_index], state[blank_index]
        
        self.current_state = tuple(state)
        self.initial_state = self.current_state
        self.update_board_display(self.current_state)
        self.input_entry.delete(0, tk.END) # Update entry box
        self.input_entry.insert(0, ",".join(map(str, self.current_state)))
        self.status_label.config(text="New puzzle generated. Click 'Solve'!")


    def reset_board(self):
        """Resets the board to the last initial state."""
        self.current_state = self.initial_state
        self.solution_path = []
        self.animation_index = 0
        self.allow_user_moves = True
        self.update_board_display(self.current_state)
        self.input_entry.delete(0, tk.END) # Update entry box
        self.input_entry.insert(0, ",".join(map(str, self.current_state)))
        self.status_label.config(text="Board reset. Set up or click 'Solve'.")
        # Re-enable buttons
        self.solve_button.config(state="normal")
        self.shuffle_button.config(state="normal")
        self.set_button.config(state="normal") # Enable set button


    def start_solve_thread(self):
        """
        Starts the A* solver in a separate thread to prevent the GUI
        from freezing.
        """
        self.allow_user_moves = False 
        self.solve_button.config(state="disabled")
        self.reset_button.config(state="disabled")
        self.shuffle_button.config(state="disabled")
        self.set_button.config(state="disabled") # Disable set button
        self.status_label.config(text="Solving... This may take a moment.")
        
        self.solver_thread = threading.Thread(
            target=solve_puzzle,
            args=(self.current_state, self.goal_state, self.solver_queue)
        )
        self.solver_thread.start()
        self.after(100, self.check_solution_queue)


    def check_solution_queue(self):
        """
        Checks the queue for the solution from the solver thread.
        If found, starts the animation. If not, checks again.
        """
        try:
            solution_info = self.solver_queue.get_nowait()
            
            if solution_info and solution_info.get("unsolvable", False):
                messagebox.showerror("No Solution", "This puzzle configuration is unsolvable.")
                self.reset_board()
            
            elif solution_info:
                self.solution_path = solution_info["path"]
                self.animation_index = 0
                self.status_label.config(text=f"Solved in {solution_info['moves']} moves! Animating...")
                self.animate_solution()
            
            else:
                 messagebox.showerror("No Solution", "An unknown error occurred.")
                 self.reset_board()

        except queue.Empty:
            self.after(100, self.check_solution_queue)


    def animate_solution(self):
        """Animates the solution path step by step."""
        self.allow_user_moves = False 
        
        if self.animation_index < len(self.solution_path):
            state = self.solution_path[self.animation_index]
            self.update_board_display(state)
            self.animation_index += 1
            self.after(400, self.animate_solution) # 400ms delay
        else:
            self.status_label.config(text="Animation complete!")
            self.reset_button.config(state="normal")
            self.shuffle_button.config(state="normal")
            self.set_button.config(state="normal") # Re-enable set
            self.allow_user_moves = True


# =======================================================================
# --- Part 3: Main Execution ---
# =======================================================================

if __name__ == "__main__":
    
    # 0 represents the blank space
    
    # --- THIS IS A SOLVABLE PUZZLE ---
    INITIAL_STATE = (1, 2, 3,
                     7, 4, 5,
                     0, 8, 6)

    # The classic goal state (0 inversions)
    GOAL_STATE = (1, 2, 3,
                  4, 5, 6,
                  7, 8, 0)

    app = PuzzleGUI(INITIAL_STATE, GOAL_STATE)
    app.mainloop()