import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.colors as mcolors
import random
from scipy.ndimage import gaussian_filter
import tkinter as tk
from threading import Thread, Event

# Grid dimensions
rows, cols = 100, 100

# Environmental variables
humidity = 0.8
precipitation_strength = 0.6
precipitation_chance = 0.7
wind_strength = 0.2

# Simulation state
stop_simulation_event = Event()

# Variables to store the initial state for restart
initial_forest = None
initial_moisture_map = None
initial_burn_timers = None

def initialize_forest(rows, cols):
    forest = np.random.choice([1, 6], size=(rows, cols), p=[0.6, 0.4])
    moisture_map = np.random.rand(rows, cols)
    burn_timers = np.zeros((rows, cols), dtype=int)
    return forest, moisture_map, burn_timers

def add_rock_clusters(forest, num_clusters, max_cluster_size):
    for _ in range(num_clusters):
        cluster_row = random.randint(0, rows - 1)
        cluster_col = random.randint(0, cols - 1)
        cluster_size = random.randint(1, max_cluster_size)
        for i in range(cluster_size):
            for j in range(cluster_size):
                ni, nj = cluster_row + i, cluster_col + j
                if 0 <= ni < rows and 0 <= nj < cols:
                    forest[ni, nj] = 4
    return forest

def add_water_clusters(forest, probability, sigma, threshold):
    water_layer = np.random.rand(rows, cols) < probability
    water_layer = gaussian_filter(water_layer.astype(float), sigma=sigma) > threshold
    forest[water_layer] = 3
    return forest

def ignite_random_fire(forest, burn_timers):
    while True:
        random_row = random.randint(0, rows - 1)
        random_col = random.randint(0, cols - 1)
        if forest[random_row, random_col] in [1, 6]:
            forest[random_row, random_col] = 2
            burn_timers[random_row, random_col] = 10 if forest[random_row, random_col] == 1 else 3
            break
    return forest, burn_timers

def spread_fire(grid, moisture_map, burn_timers, drying_effect, rain_active):
    global humidity, precipitation_strength, wind_strength
    new_grid = grid.copy()
    new_moisture = moisture_map.copy()
    new_burn_timers = burn_timers.copy()

    for i in range(rows):
        for j in range(cols):
            if grid[i, j] == 2:  # Burning
                if rain_active and precipitation_strength > 0.6:
                    new_grid[i, j] = 5  # Burnt
                    continue

                new_burn_timers[i, j] -= 1
                if new_burn_timers[i, j] <= 0:
                    new_grid[i, j] = 5  # Burnt
                    continue

                for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    ni, nj = i + dy, j + dx
                    if 0 <= ni < rows and 0 <= nj < cols and grid[ni, nj] in [1, 6]:
                        reduction_factor = ((humidity + precipitation_strength) * 10) * 5
                        increase_factor = ((wind_strength + drying_effect) * 10) * 3
                        ignition_chance = 0.65 - (reduction_factor / 100) + (increase_factor / 100)
                        ignition_chance = max(0, min(1, ignition_chance))

                        if random.random() < ignition_chance:
                            new_grid[ni, nj] = 2
                            new_burn_timers[ni, nj] = 8 if grid[ni, nj] == 1 else 8

    new_moisture = np.clip(new_moisture - drying_effect * wind_strength, 0, 1)
    return new_grid, new_moisture, new_burn_timers

def run_simulation(forest, moisture_map, burn_timers, canvas, ax, drying_effect, result_label):
    global stop_simulation_event
    stop_simulation_event.clear()

    cmap = mcolors.ListedColormap(['#654321', 'green', 'red', 'blue', 'grey', '#3d251e', '#5fa15f'])
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    total_cells = rows * cols
    steps_taken = 0

    while not stop_simulation_event.is_set():
        rain_active = random.random() < precipitation_chance

        ax.clear()
        ax.imshow(forest, cmap=cmap, norm=norm)
        ax.set_title(f"Step: {steps_taken} | Rain: {'Yes' if rain_active else 'No'}")
        canvas.draw()

        steps_taken += 1

        if np.all(forest != 2):  # No burning cells
            print("Fire has stopped spreading.")
            break

        forest, moisture_map, burn_timers = spread_fire(forest, moisture_map, burn_timers, drying_effect, rain_active)

    if stop_simulation_event.is_set():
        print("Simulation was stopped manually.")

    # Simulation ended, calculate and update results
    burned_cells = np.sum(forest == 5)
    burned_percentage = (burned_cells / total_cells) * 100
    result_text = (f"Simulation Results:\n"
                   f"Total burned m²: {burned_cells}\n"
                   f"% burned: {burned_percentage:.2f}%\n"
                   f"Total steps taken: {steps_taken}")
    result_label.config(text=result_text)  # Update results in the secondary window

def main():
    global initial_forest, initial_moisture_map, initial_burn_timers, results_window, results_label
    global humidity, precipitation_strength, precipitation_chance, wind_strength
    global humidity_input, precipitation_strength_input, precipitation_chance_input, wind_strength_input

    root = tk.Tk()
    root.title("Fire Simulation")

    # Create the secondary results window
    results_window = tk.Toplevel(root)
    results_window.title("Simulation Results")
    results_window.geometry("400x350")

    # Add result labels to the secondary window
    results_label = tk.Label(results_window, text=("Simulation Results:\n"
                                                   "Total burned m²: \n"
                                                   "% burned: \n"
                                                   "Total steps taken: "), 
                             bg="white", fg="black", font=("Helvetica", 10), justify="left")
    results_label.pack(pady=10)

    # Add inputs for environmental variables
    tk.Label(results_window, text="Humidity (0-1):").pack(pady=2)
    humidity_input = tk.Entry(results_window)
    humidity_input.insert(0, str(humidity))
    humidity_input.pack(pady=2)

    tk.Label(results_window, text="Precipitation Strength (0-1):").pack(pady=2)
    precipitation_strength_input = tk.Entry(results_window)
    precipitation_strength_input.insert(0, str(precipitation_strength))
    precipitation_strength_input.pack(pady=2)

    tk.Label(results_window, text="Precipitation Chance (0-1):").pack(pady=2)
    precipitation_chance_input = tk.Entry(results_window)
    precipitation_chance_input.insert(0, str(precipitation_chance))
    precipitation_chance_input.pack(pady=2)

    tk.Label(results_window, text="Wind Strength (0-1):").pack(pady=2)
    wind_strength_input = tk.Entry(results_window)
    wind_strength_input.insert(0, str(wind_strength))
    wind_strength_input.pack(pady=2)

    def apply_changes():
        """Apply user-defined changes to the environmental variables."""
        global humidity, precipitation_strength, precipitation_chance, wind_strength
        try:
            humidity = float(humidity_input.get())
            precipitation_strength = float(precipitation_strength_input.get())
            precipitation_chance = float(precipitation_chance_input.get())
            wind_strength = float(wind_strength_input.get())
            print(f"Updated Variables:\n"
                  f"Humidity: {humidity}\n"
                  f"Precipitation Strength: {precipitation_strength}\n"
                  f"Precipitation Chance: {precipitation_chance}\n"
                  f"Wind Strength: {wind_strength}")
        except ValueError:
            print("Error: Please enter valid numbers between 0 and 1.")

    # Add a button to apply changes
    apply_button = tk.Button(results_window, text="Apply Changes", command=apply_changes, bg="blue", fg="white")
    apply_button.pack(pady=10)

    fig, ax = plt.subplots(figsize=(8, 8))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Define cmap and norm globally for the simulation
    cmap = mcolors.ListedColormap(['#654321', 'green', 'red', 'blue', 'grey', '#3d251e', '#5fa15f'])
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    def generate_landscape():
        nonlocal forest, moisture_map, burn_timers
        forest, moisture_map, burn_timers = initialize_forest(rows, cols)
        forest = add_rock_clusters(forest, num_clusters=50, max_cluster_size=5)
        forest = add_water_clusters(forest, probability=0.15, sigma=3, threshold=0.2)
        ax.clear()
        ax.imshow(forest, cmap=cmap, norm=norm)  # Use cmap and norm here
        ax.set_title("Generated Landscape")
        canvas.draw()

    def start_simulation():
        nonlocal forest, burn_timers
        global initial_forest, initial_moisture_map, initial_burn_timers

        # Save the initial healthy state
        initial_forest = forest.copy()
        initial_moisture_map = moisture_map.copy()
        initial_burn_timers = burn_timers.copy()

        forest, burn_timers = ignite_random_fire(forest, burn_timers)
        simulation_thread = Thread(target=run_simulation, args=(forest, moisture_map, burn_timers, canvas, ax, drying_effect, results_label), daemon=True)
        simulation_thread.start()

    def restart_simulation():
        global stop_simulation_event
        stop_simulation_event.set()  # Stop any running simulation
        if initial_forest is not None:
            # Restore the initial landscape
            nonlocal forest, moisture_map, burn_timers
            forest = initial_forest.copy()
            moisture_map = initial_moisture_map.copy()
            burn_timers = initial_burn_timers.copy()
            ax.clear()
            ax.imshow(forest, cmap=cmap, norm=norm)  # Use cmap and norm here
            ax.set_title("Restored Landscape")
            canvas.draw()

    drying_effect = wind_strength

    forest, moisture_map, burn_timers = initialize_forest(rows, cols)
    generate_landscape()

    btn_generate = tk.Button(root, text="Generate Landscape", command=generate_landscape, bg="blue", fg="white")
    btn_generate.pack(side=tk.LEFT, padx=5, pady=5)

    btn_start = tk.Button(root, text="Start Simulation", command=start_simulation, bg="green", fg="white")
    btn_start.pack(side=tk.RIGHT, padx=5, pady=5)

    btn_restart = tk.Button(root, text="Restart Simulation", command=restart_simulation, bg="orange", fg="white")
    btn_restart.pack(side=tk.BOTTOM, padx=5, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
