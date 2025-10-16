import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta
import threading
import sys

try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame library not found. Sound notifications will use system beep. Install with 'pip install pygame'.")

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("Warning: plyer library not found. Desktop notifications will be disabled. Install with 'pip install plyer'.")

class ToDoApp(tk.Tk):
    """
    A Python To-Do List Manager with a Reminder System using Tkinter.
    """
    def __init__(self):
        super().__init__()
        self.title("To-Do List Manager")
        self.geometry("800x600")
        
        self.task_file = "tasks.json"
        self.tasks = self.load_tasks()

        self.create_widgets()
        self.refresh_task_list()
        self.check_reminders()
        self.update_clock()

    def create_widgets(self):
        """Initializes and places all GUI widgets."""
        
        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header Section ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.clock_label = ttk.Label(header_frame, text="", font=("Arial", 12))
        self.clock_label.pack(side=tk.RIGHT)
        
        ttk.Label(header_frame, text="To-Do List", font=("Helvetica", 24, "bold")).pack(side=tk.LEFT)
        
        # --- Task Input Section ---
        input_frame = ttk.LabelFrame(main_frame, text="Add New Task", padding="10")
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="Task:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.task_entry = ttk.Entry(input_frame, width=40)
        self.task_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=5, pady=5)
        
        ttk.Label(input_frame, text="Deadline (DD/MM HH:MM):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.deadline_entry = ttk.Entry(input_frame, width=20)
        self.deadline_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(input_frame, text="Remind before:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        # Create a frame for hours and minutes selection
        reminder_frame = ttk.Frame(input_frame)
        reminder_frame.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Hours dropdown
        ttk.Label(reminder_frame, text="Hours:").pack(side=tk.LEFT, padx=(0, 5))
        reminder_hours_options = [str(i) for i in range(0, 24)]
        self.reminder_hours = tk.StringVar(self)
        self.reminder_hours.set("1")
        hours_menu = ttk.OptionMenu(reminder_frame, self.reminder_hours, *reminder_hours_options)
        hours_menu.pack(side=tk.LEFT, padx=(0, 10))
        
        # Minutes dropdown
        ttk.Label(reminder_frame, text="Minutes:").pack(side=tk.LEFT, padx=(0, 5))
        reminder_minutes_options = [str(i) for i in range(0, 60, 5)]  # 5-minute intervals
        self.reminder_minutes = tk.StringVar(self)
        self.reminder_minutes.set("0")
        minutes_menu = ttk.OptionMenu(reminder_frame, self.reminder_minutes, *reminder_minutes_options)
        minutes_menu.pack(side=tk.LEFT)
        
        self.add_button = ttk.Button(input_frame, text="Add Task", command=self.add_task)
        self.add_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        input_frame.columnconfigure(1, weight=1)

        # --- Task List Display ---
        task_list_frame = ttk.Frame(main_frame)
        task_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure Treeview and its columns
        columns = ("task", "deadline", "reminder_time", "status")
        self.task_tree = ttk.Treeview(task_list_frame, columns=columns, show="headings", selectmode="browse")
        
        self.task_tree.heading("task", text="Task")
        self.task_tree.heading("deadline", text="Deadline")
        self.task_tree.heading("reminder_time", text="Reminder Time")
        self.task_tree.heading("status", text="Status")
        
        self.task_tree.column("task", width=250, anchor="w")
        self.task_tree.column("deadline", width=150, anchor="center")
        self.task_tree.column("reminder_time", width=150, anchor="center")
        self.task_tree.column("status", width=100, anchor="center")
        
        # Configure a tag for completed tasks (strikethrough)
        self.task_tree.tag_configure("completed", font=("Helvetica", 10, "overstrike"))
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(task_list_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscroll=scrollbar.set)
        
        self.task_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Action Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT, padx=2, expand=True)
        ttk.Button(button_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=2, expand=True)
        ttk.Button(button_frame, text="Mark Completed", command=self.mark_completed).pack(side=tk.LEFT, padx=2, expand=True)
        ttk.Button(button_frame, text="Reset Reminder", command=self.reset_reminder).pack(side=tk.LEFT, padx=2, expand=True)
        ttk.Button(button_frame, text="Sort by Deadline", command=self.sort_tasks).pack(side=tk.LEFT, padx=2, expand=True)

    def add_task(self):
        """Adds a new task from user input."""
        task_text = self.task_entry.get().strip()
        deadline_text = self.deadline_entry.get().strip()
        
        if not task_text:
            messagebox.showwarning("Input Error", "Task description cannot be empty.")
            return

        try:
            # Parse DD/MM HH:MM format and assume current year
            current_year = datetime.now().year
            deadline_with_year = f"{current_year} {deadline_text}"
            deadline = datetime.strptime(deadline_with_year, "%Y %d/%m %H:%M")
            reminder_hours = int(self.reminder_hours.get())
            reminder_minutes = int(self.reminder_minutes.get())
            reminder_time = deadline - timedelta(hours=reminder_hours, minutes=reminder_minutes)
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid deadline format. Please use DD/MM HH:MM.")
            return

        # Generate unique ID based on current timestamp
        import time
        task_id = str(int(time.time() * 1000))  # millisecond timestamp
        
        new_task = {
            "id": task_id,
            "task": task_text,
            "deadline": deadline.isoformat(),
            "reminder_time": reminder_time.isoformat(),
            "completed": False,
            "reminded": False
        }
        self.tasks.append(new_task)
        self.save_tasks()
        self.refresh_task_list()
        
        # Clear entry fields
        self.task_entry.delete(0, tk.END)
        self.deadline_entry.delete(0, tk.END)
        messagebox.showinfo("Task Added", "Task successfully added!")

    def edit_task(self):
        """Allows the user to edit the selected task."""
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select a task to edit.")
            return

        # Get the index of the selected item
        selected_item = selected_items[0]
        try:
            all_items = self.task_tree.get_children()
            selected_index = all_items.index(selected_item)
        except ValueError:
            messagebox.showerror("Error", "Could not find the selected task.")
            return
        
        if selected_index >= len(self.tasks):
            messagebox.showerror("Error", "Selected task index is out of range.")
            return
            
        selected_task = self.tasks[selected_index]
        original_task_text = selected_task["task"]
        
        edit_window = tk.Toplevel(self)
        edit_window.title("Edit Task")
        edit_window.geometry("400x200")
        
        ttk.Label(edit_window, text="New Task:").pack(pady=5)
        new_task_entry = ttk.Entry(edit_window, width=50)
        new_task_entry.insert(0, original_task_text)
        new_task_entry.pack(pady=5)
        
        def save_edit():
            new_text = new_task_entry.get().strip()
            if new_text:
                selected_task["task"] = new_text
                self.save_tasks()
                self.refresh_task_list()
                edit_window.destroy()
                messagebox.showinfo("Success", "Task updated successfully!")
            else:
                messagebox.showwarning("Input Error", "Task cannot be empty.", parent=edit_window)
        
        ttk.Button(edit_window, text="Save", command=save_edit).pack(pady=10)

    def delete_task(self):
        """Deletes the selected task from the list."""
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select a task to delete.")
            return
        
        # Get the index of the selected item
        selected_item = selected_items[0]
        try:
            all_items = self.task_tree.get_children()
            selected_index = all_items.index(selected_item)
        except ValueError:
            messagebox.showerror("Error", "Could not find the selected task.")
            return
        
        if selected_index >= len(self.tasks):
            messagebox.showerror("Error", "Selected task index is out of range.")
            return
            
        task_text = self.tasks[selected_index]["task"]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{task_text}'?"):
            del self.tasks[selected_index]
            self.save_tasks()
            self.refresh_task_list()
            messagebox.showinfo("Success", "Task deleted successfully!")

    def mark_completed(self):
        """Toggles the completion status of the selected task."""
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select a task to mark as completed.")
            return

        # Get the index of the selected item
        selected_item = selected_items[0]
        try:
            all_items = self.task_tree.get_children()
            selected_index = all_items.index(selected_item)
        except ValueError:
            messagebox.showerror("Error", "Could not find the selected task.")
            return
        
        if selected_index >= len(self.tasks):
            messagebox.showerror("Error", "Selected task index is out of range.")
            return
            
        selected_task = self.tasks[selected_index]
        selected_task["completed"] = not selected_task["completed"]
        self.save_tasks()
        self.refresh_task_list()
        status = "completed" if selected_task["completed"] else "pending"
        messagebox.showinfo("Success", f"Task marked as {status}!")

    def reset_reminder(self):
        """Resets the reminder status for the selected task."""
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Error", "Please select a task to reset reminder.")
            return

        # Get the index of the selected item
        selected_item = selected_items[0]
        try:
            all_items = self.task_tree.get_children()
            selected_index = all_items.index(selected_item)
        except ValueError:
            messagebox.showerror("Error", "Could not find the selected task.")
            return
        
        if selected_index >= len(self.tasks):
            messagebox.showerror("Error", "Selected task index is out of range.")
            return
            
        selected_task = self.tasks[selected_index]
        
        if selected_task.get("reminded", False):
            selected_task["reminded"] = False
            self.save_tasks()
            self.refresh_task_list()
            messagebox.showinfo("Reminder Reset", "Reminder status has been reset. You will be reminded again when the time comes.")
        else:
            messagebox.showinfo("No Action Needed", "This task hasn't been reminded yet.")

    def sort_tasks(self):
        """Sorts tasks by their deadline."""
        self.tasks.sort(key=lambda t: datetime.fromisoformat(t["deadline"]))
        self.refresh_task_list()
        messagebox.showinfo("Tasks Sorted", "Tasks have been sorted by their deadline.")

    def refresh_task_list(self):
        """Clears and re-populates the Treeview with current task data."""
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
            
        for task in self.tasks:
            # Determine status text
            if task["completed"]:
                status = "Completed"
            elif task.get("reminded", False):
                status = "Reminded"
            else:
                status = "Pending"
                
            task_info = (
                task["task"],
                datetime.fromisoformat(task["deadline"]).strftime("%d/%m %H:%M"),
                datetime.fromisoformat(task["reminder_time"]).strftime("%d/%m %H:%M"),
                status
            )
            
            # Apply strikethrough tag if completed
            if task["completed"]:
                self.task_tree.insert("", "end", values=task_info, tags=("completed",))
            else:
                self.task_tree.insert("", "end", values=task_info)

    def save_tasks(self):
        """Saves the current task list to a JSON file."""
        with open(self.task_file, "w") as f:
            json.dump(self.tasks, f, indent=4)

    def load_tasks(self):
        """Loads tasks from a JSON file, or returns an empty list if not found."""
        if os.path.exists(self.task_file):
            with open(self.task_file, "r") as f:
                tasks = json.load(f)
                # Ensure all tasks have required fields for backward compatibility
                import time
                for i, task in enumerate(tasks):
                    if "reminded" not in task:
                        task["reminded"] = False
                    if "id" not in task:
                        # Generate unique ID for existing tasks
                        task["id"] = f"legacy_{i}_{int(time.time() * 1000)}"
                return tasks
        return []

    def check_reminders(self):
        """Checks for upcoming reminders and triggers notifications."""
        now = datetime.now()
        
        for task in self.tasks:
            if not task["completed"] and not task.get("reminded", False):
                try:
                    reminder_time = datetime.fromisoformat(task["reminder_time"])
                    if now >= reminder_time:
                        self.trigger_reminder(task)
                        
                        # Mark task as reminded to prevent repeated reminders
                        # Task remains incomplete until user manually marks it done
                        task["reminded"] = True
                except ValueError:
                    # Skip tasks with invalid datetime format
                    continue
        
        self.save_tasks()
        self.refresh_task_list()
        
        # Schedule the next check in 1 second
        self.after(1000, self.check_reminders)

    def trigger_reminder(self, task):
        """Triggers the reminder notifications."""
        
        task_name = task["task"]
        deadline = datetime.fromisoformat(task["deadline"]).strftime("%d/%m %H:%M")
        
        # --- Alarm Sound (in a new thread to prevent UI freeze) ---
        threading.Thread(target=self.play_alarm_sound).start()
        
        # --- In-app Popup Message ---
        messagebox.showinfo("REMINDER", f"Task: {task_name}\n\nDeadline: {deadline}")
        
        # --- Desktop Notification (if plyer is available) ---
        if PLYER_AVAILABLE:
            notification_title = "To-Do Reminder"
            notification_message = f"Reminder for '{task_name}'! Deadline is at {deadline}."
            notification.notify(
                title=notification_title,
                message=notification_message,
                timeout=10
            )

    def play_alarm_sound(self):
        """Plays a sound file using available sound libraries."""
        try:
            if PYGAME_AVAILABLE:
                # Try to play with pygame first
                if os.path.exists("reminder.wav"):
                    pygame.mixer.music.load("reminder.wav")
                    pygame.mixer.music.play()
                else:
                    # Play a default system sound with pygame
                    print("reminder.wav not found, using system beep")
                    if WINSOUND_AVAILABLE:
                        winsound.Beep(1000, 500)  # 1000 Hz for 500ms
            elif WINSOUND_AVAILABLE:
                # Fallback to Windows system sound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                # Last resort: print sound
                print("\a")  # Terminal bell sound
                print("🔔 REMINDER ALERT! 🔔")
        except Exception as e:
            print(f"Could not play alarm sound. Error: {e}")
            print("🔔 REMINDER ALERT! 🔔")

    def update_clock(self):
        """Updates the current date and time displayed in the header."""
        now = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)

    def get_selected_task(self):
        """Helper method to get the selected task from the treeview."""
        selected_items = self.task_tree.selection()
        if not selected_items:
            return None
        
        # Get the first selected item
        selected_item = selected_items[0]
        
        # Get the index of the selected item in the treeview
        try:
            all_items = self.task_tree.get_children()
            selected_index = all_items.index(selected_item)
            
            # Return the corresponding task from our task list
            if 0 <= selected_index < len(self.tasks):
                return self.tasks[selected_index]
        except (ValueError, IndexError):
            pass
            
        return None

if __name__ == "__main__":
    app = ToDoApp()
    app.mainloop()