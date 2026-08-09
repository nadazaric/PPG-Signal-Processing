import csv
from pathlib import Path
from static import ui as static_processing_ui

import dearpygui.dearpygui as dpg


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SIGNAL_COLUMNS = ("green", "red", "infrared")
FILTERED_COLUMNS = ("green_minus_red", "green_minus_infrared", "green_minus_red_infrared_mean")
FS_HZ = 100.0
STARTUP_OUTLIER_SECONDS = 0.6

APP_TITLE = "PPG Visualizer"
APP_WIDTH = 1200
APP_HEIGHT = 820


state = {
    "files": [],
    "current_file": None,
    "x": [],
    "signals": {name: [] for name in SIGNAL_COLUMNS},
    "filtered_signals": {name: [] for name in FILTERED_COLUMNS},
    "window_size": 1000,
    "start_index": 0,
}


def find_csv_files():
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.csv"))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_ppg_csv(path):
    x_values = []
    signals = {name: [] for name in SIGNAL_COLUMNS}

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = [name for name in ("sample_index", *SIGNAL_COLUMNS) if name not in (reader.fieldnames or [])]
        if missing_columns:
            raise ValueError(f"CSV nema potrebne kolone: {', '.join(missing_columns)}")

        for row_number, row in enumerate(reader):
            sample_index = to_float(row.get("sample_index", row_number))
            x_values.append(sample_index / FS_HZ)
            for signal_name in SIGNAL_COLUMNS:
                signals[signal_name].append(to_float(row.get(signal_name)))

    return x_values, signals


def startup_outlier_samples(sample_count):
    return min(int(round(STARTUP_OUTLIER_SECONDS * FS_HZ)), sample_count)


def remove_startup_outliers_and_center(values):
    outlier_count = startup_outlier_samples(len(values))
    useful_values = values[outlier_count:]
    mean_value = sum(useful_values) / len(useful_values) if useful_values else 0.0

    return [
        0.0 if index < outlier_count else value - mean_value
        for index, value in enumerate(values)
    ]


def preprocess_signals(signals):
    return {
        signal_name: remove_startup_outliers_and_center(values)
        for signal_name, values in signals.items()
    }


def calculate_filtered_signals(signals):
    green = signals["green"]
    red = signals["red"]
    infrared = signals["infrared"]

    return {
        "green_minus_red": [g - r for g, r in zip(green, red)],
        "green_minus_infrared": [g - ir for g, ir in zip(green, infrared)],
        "green_minus_red_infrared_mean": [
            g - ((r + ir) / 2.0) for g, r, ir in zip(green, red, infrared)
        ],
    }


def visible_range():
    sample_count = len(state["x"])
    if sample_count == 0:
        return 0, 0

    window_size = max(10, min(int(state["window_size"]), sample_count))
    start = max(0, min(int(state["start_index"]), sample_count - window_size))
    end = min(sample_count, start + window_size)
    state["start_index"] = start
    state["window_size"] = window_size
    return start, end


def update_scroll_controls():
    sample_count = len(state["x"])
    max_window = max(10, sample_count)
    window_size = max(10, min(int(state["window_size"]), max_window))
    max_start = max(0, sample_count - window_size)

    dpg.configure_item("window_size_slider", max_value=max_window)
    dpg.set_value("window_size_slider", window_size)
    dpg.configure_item("start_index_slider", max_value=max_start)
    dpg.set_value("start_index_slider", min(int(state["start_index"]), max_start))


def update_plots():
    start, end = visible_range()
    x_visible = state["x"][start:end]

    static_processing_ui.set_visible_range(start, end)

    if not x_visible:
        for signal_name in SIGNAL_COLUMNS:
            dpg.set_value(f"{signal_name}_series", [[], []])
        for signal_name in FILTERED_COLUMNS:
            dpg.set_value(f"{signal_name}_series", [[], []])
        dpg.set_value("status_text", "Nema ucitanih podataka.")
        return

    all_plot_sources = [
        (signal_name, state["signals"][signal_name]) for signal_name in SIGNAL_COLUMNS
    ] + [
        (signal_name, state["filtered_signals"][signal_name]) for signal_name in FILTERED_COLUMNS
    ]

    for signal_name, signal_values in all_plot_sources:
        y_visible = signal_values[start:end]
        dpg.set_value(f"{signal_name}_series", [x_visible, y_visible])
        dpg.set_axis_limits(f"{signal_name}_x_axis", x_visible[0], x_visible[-1])

        y_min = min(y_visible)
        y_max = max(y_visible)
        padding = max((y_max - y_min) * 0.08, 1.0)
        dpg.set_axis_limits(f"{signal_name}_y_axis", y_min - padding, y_max + padding)

    filename = state["current_file"].name if state["current_file"] else "-"
    start_time = state["x"][start]
    end_time = state["x"][end - 1]
    dpg.set_value(
        "status_text",
        f"Fajl: {filename} | Fs: {FS_HZ:g} Hz | Uzorci: {len(state['x'])} | "
        f"Ignorisan pocetak: {STARTUP_OUTLIER_SECONDS:g} s | "
        f"Prikaz: {start_time:.2f}-{end_time:.2f} s",
    )
    update_scroll_controls()


def load_selected_file(sender=None, app_data=None, user_data=None):
    selected_name = dpg.get_value("file_combo")
    if not selected_name:
        return

    path = DATA_DIR / selected_name
    try:
        x_values, signals = load_ppg_csv(path)
        static_processing_ui.set_data(
            x_values,
            signals,
        )
    except Exception as exc:
        dpg.set_value("status_text", f"Greska pri ucitavanju: {exc}")
        return

    state["current_file"] = path
    state["x"] = x_values
    state["signals"] = preprocess_signals(signals)
    state["filtered_signals"] = preprocess_signals(calculate_filtered_signals(signals))
    state["start_index"] = 0
    state["window_size"] = min(1000, max(len(x_values), 10))
    update_plots()


def refresh_file_list(load_first=False):
    state["files"] = find_csv_files()
    file_names = [path.name for path in state["files"]]
    dpg.configure_item("file_combo", items=file_names)

    if not file_names:
        dpg.set_value("status_text", f"Nema CSV fajlova u folderu: {DATA_DIR}")
        return

    if load_first or dpg.get_value("file_combo") not in file_names:
        dpg.set_value("file_combo", file_names[0])
        load_selected_file()


def on_start_changed(sender, app_data):
    state["start_index"] = int(app_data)
    update_plots()


def on_window_size_changed(sender, app_data):
    state["window_size"] = int(app_data)
    update_plots()


def shift_view(delta):
    state["start_index"] = int(state["start_index"]) + int(delta)
    update_plots()


def on_mouse_wheel(sender, app_data):
    if not state["x"]:
        return

    wheel_delta = int(app_data)
    step = max(1, int(state["window_size"] * 0.08))
    shift_view(-wheel_delta * step)


def create_signal_plot(signal_name, label, color):
    with dpg.plot(label=label, height=235, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Vreme [s]", tag=f"{signal_name}_x_axis")
        dpg.add_plot_axis(dpg.mvYAxis, label=label, tag=f"{signal_name}_y_axis")
        dpg.add_line_series([], [], label=label, parent=f"{signal_name}_y_axis", tag=f"{signal_name}_series")
        dpg.bind_item_theme(f"{signal_name}_series", color)


def create_line_theme(color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 1.8, category=dpg.mvThemeCat_Plots)
    return theme


def build_ui():
    dpg.create_context()

    green_theme = create_line_theme((34, 197, 94, 255))
    red_theme = create_line_theme((239, 68, 68, 255))
    infrared_theme = create_line_theme((99, 102, 241, 255))
    filtered_red_theme = create_line_theme((245, 158, 11, 255))
    filtered_infrared_theme = create_line_theme((14, 165, 233, 255))
    filtered_mean_theme = create_line_theme((236, 72, 153, 255))

    with dpg.window(tag="main_window", label=APP_TITLE, width=APP_WIDTH, height=APP_HEIGHT):
        with dpg.group(horizontal=True):
            dpg.add_text("CSV fajl:")
            dpg.add_combo([], width=300, tag="file_combo", callback=load_selected_file)
            dpg.add_button(label="Osvezi", callback=lambda: refresh_file_list(load_first=False))
            dpg.add_button(label="Ucitaj", callback=load_selected_file)

        dpg.add_spacer(height=6)
        dpg.add_text("", tag="status_text")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_button(label="<", width=38, callback=lambda: shift_view(-max(1, int(state["window_size"] * 0.25))))
            dpg.add_slider_int(
                label="Pocetak prikaza",
                tag="start_index_slider",
                min_value=0,
                max_value=1,
                width=-180,
                callback=on_start_changed,
            )
            dpg.add_button(label=">", width=38, callback=lambda: shift_view(max(1, int(state["window_size"] * 0.25))))

        dpg.add_slider_int(
            label="Broj uzoraka u prikazu",
            tag="window_size_slider",
            min_value=10,
            max_value=1000,
            default_value=1000,
            width=-1,
            callback=on_window_size_changed,
        )

        dpg.add_spacer(height=4)
        with dpg.tab_bar():
            with dpg.tab(label="Sirovi signali"):
                with dpg.child_window(height=-1, width=-1, border=True):
                    create_signal_plot("green", "Green", green_theme)
                    create_signal_plot("red", "Red", red_theme)
                    create_signal_plot("infrared", "Infrared", infrared_theme)

            with dpg.tab(label="Filtrirani signali"):
                with dpg.child_window(height=-1, width=-1, border=True):
                    create_signal_plot(
                        "green_minus_red",
                        "Green - Red",
                        filtered_red_theme,
                    )
                    create_signal_plot(
                        "green_minus_infrared",
                        "Green - Infrared",
                        filtered_infrared_theme,
                    )
                    create_signal_plot(
                        "green_minus_red_infrared_mean",
                        "Green - srednja vrednost Red i Infrared",
                        filtered_mean_theme,
                    )
            with dpg.tab(label="Staticka obrada"):
                static_processing_ui.create()

    with dpg.handler_registry():
        dpg.add_mouse_wheel_handler(callback=on_mouse_wheel)

    dpg.create_viewport(title=APP_TITLE, width=APP_WIDTH, height=APP_HEIGHT)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)
    refresh_file_list(load_first=True)


def main():
    build_ui()
    dpg.show_viewport()
    dpg.maximize_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
