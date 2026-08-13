import types
from pathlib import Path

import dearpygui.dearpygui as dpg

from realtime import config_ui
from realtime.processing import process_green_signal, detect_peaks


BASE_DIR = Path(__file__).resolve().parent.parent
REALTIME_CONFIGS_DIR = BASE_DIR / "realtime_configs"

CONFIG_COMBO_TAG = "realtime_config_combo"
CONFIG_STATUS_TAG = "realtime_config_status"
CONFIG_DETAILS_BUTTON_TAG = "realtime_config_details_button"
CONFIG_DETAILS_TEXT_TAG = "realtime_config_details_text"
SAVE_CONFIG_WINDOW_TAG = "realtime_save_config_window"
SAVE_CONFIG_NAME_INPUT_TAG = "realtime_save_config_name_input"
SAVE_CONFIG_STATUS_TAG = "realtime_save_config_status"

REALTIME_ORIGINAL_GREEN_SERIES_TAG = "realtime_original_green_series"
REALTIME_ORIGINAL_GREEN_X_AXIS_TAG = "realtime_original_green_x_axis"
REALTIME_ORIGINAL_GREEN_Y_AXIS_TAG = "realtime_original_green_y_axis"

REALTIME_PROCESSED_GREEN_SERIES_TAG = "realtime_processed_green_series"
REALTIME_PROCESSED_GREEN_X_AXIS_TAG = "realtime_processed_green_x_axis"
REALTIME_PROCESSED_GREEN_Y_AXIS_TAG = "realtime_processed_green_y_axis"

REALTIME_FINAL_PROCESSED_GREEN_SERIES_TAG = "realtime_final_processed_green_series"
REALTIME_FINAL_PROCESSED_GREEN_X_AXIS_TAG = "realtime_final_processed_green_x_axis"
REALTIME_FINAL_PROCESSED_GREEN_Y_AXIS_TAG = "realtime_final_processed_green_y_axis"
REALTIME_FINAL_PROCESSED_CONTAINER_TAG = "realtime_final_processed_container"
REALTIME_PROCESSED_PEAKS_SERIES_TAG = "realtime_processed_peaks_series"
REALTIME_FINAL_PROCESSED_PEAKS_SERIES_TAG = "realtime_final_processed_peaks_series"

REALTIME_STATUS_TAG = "realtime_status"

REALTIME_FRAME_INTERVAL = 3
REALTIME_SAMPLES_PER_TICK = 5
# REALTIME_WINDOW_SIZE = 500
REALTIME_WINDOW_SIZE = 200
# REALTIME_PLOT_HEIGHT = 250
REALTIME_PLOT_HEIGHT = 350
SAVE_CONFIG_WINDOW_WIDTH = 420
SAVE_CONFIG_WINDOW_HEIGHT = 145

state = {
    "x_values": [],
    "signals": {},
    "processed_x_values": [],
    "processed_green": [],
    "visible_original_x_values": [],
    "visible_original_green_values": [],
    "visible_processed_x_values": [],
    "visible_processed_green_values": [],
    "current_index": 0,
    "is_running": False,
    "config": None,
    "config_name": None,
    "visible_range_start": 0,
    "visible_range_end": 0,
    "show_final_processed_plot": False,
    "peak_x_values": [],
    "peak_green_values": [],
}


def create_line_theme(color, line_weight):
    with dpg.theme() as line_theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, line_weight, category=dpg.mvThemeCat_Plots)

    return line_theme


def find_realtime_configs():
    if not REALTIME_CONFIGS_DIR.exists():
        return []

    return sorted(
        path.stem
        for path in REALTIME_CONFIGS_DIR.glob("*.py")
        if path.name != "__init__.py"
    )


def load_realtime_config(config_name):
    config_path = REALTIME_CONFIGS_DIR / f"{config_name}.py"

    if not config_path.exists():
        raise FileNotFoundError(f"Konfiguracija ne postoji: {config_path}")

    config_module = types.ModuleType(f"realtime_config_{config_name}")
    config_content = config_path.read_text(encoding="utf-8")
    exec(compile(config_content, str(config_path), "exec"), config_module.__dict__)

    return config_module


def normalize_config_name(config_name):
    normalized_name = str(config_name).strip()

    if normalized_name.endswith(".py"):
        normalized_name = normalized_name[:-3]

    normalized_name = normalized_name.replace(" ", "_").replace("-", "_")

    if not normalized_name:
        raise ValueError("Unesi ime konfiguracije.")

    if not all(character.isalnum() or character == "_" for character in normalized_name):
        raise ValueError("Ime konfiguracije smije sadrzati samo slova, brojeve i donju crtu.")

    return normalized_name


def save_realtime_config(config_name, config):
    normalized_name = normalize_config_name(config_name)
    REALTIME_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = REALTIME_CONFIGS_DIR / f"{normalized_name}.py"

    if config_path.exists():
        raise ValueError("Konfiguracija sa tim imenom vec postoji.")

    config_content = "\n".join(
        [
            f"STARTUP_TRIM_SECONDS = {float(config.STARTUP_TRIM_SECONDS)}",
            f"INVERT_PROCESSED_SIGNAL = {bool(config.INVERT_PROCESSED_SIGNAL)}",
            "",
            f"CHANNEL_SUBTRACTION = {repr(getattr(config, 'CHANNEL_SUBTRACTION', 'none'))}",
            "",
            f"DC_REMOVAL_ENABLED = {bool(config.DC_REMOVAL_ENABLED)}",
            '# "causal" or "centered"',
            f"DC_REMOVAL_WINDOW_TYPE = {repr(config.DC_REMOVAL_WINDOW_TYPE)}",
            f"DC_REMOVAL_WINDOW_SECONDS = {float(config.DC_REMOVAL_WINDOW_SECONDS)}",
            "",
            f"HIGH_PASS_FILTER_ENABLED = {bool(config.HIGH_PASS_FILTER_ENABLED)}",
            f"HIGH_PASS_CUTOFF_HZ = {float(config.HIGH_PASS_CUTOFF_HZ)}",
            f"HIGH_PASS_FILTER_PASSES = {int(config.HIGH_PASS_FILTER_PASSES)}",
            "",
            f"LOW_PASS_FILTER_ENABLED = {bool(config.LOW_PASS_FILTER_ENABLED)}",
            f"LOW_PASS_CUTOFF_HZ = {float(config.LOW_PASS_CUTOFF_HZ)}",
            f"LOW_PASS_FILTER_PASSES = {int(config.LOW_PASS_FILTER_PASSES)}",
            "",
            f"PEAK_DETECTION_ENABLED = {bool(getattr(config, 'PEAK_DETECTION_ENABLED', False))}",
            f"PEAK_MIN_DISTANCE_SECONDS = {float(getattr(config, 'PEAK_MIN_DISTANCE_SECONDS', 0.4))}",
            f"PEAK_MIN_HEIGHT = {float(getattr(config, 'PEAK_MIN_HEIGHT', 0.0))}",
        ]
    )
    config_path.write_text(config_content + "\n", encoding="utf-8")

    return normalized_name


def config_value(config, name, default="-"):
    return getattr(config, name, default)


def next_config_name(base_name):
    normalized_base = normalize_config_name(base_name or "rt_config")
    candidate = f"{normalized_base}_copy"
    index = 2

    while (REALTIME_CONFIGS_DIR / f"{candidate}.py").exists():
        candidate = f"{normalized_base}_copy_{index}"
        index += 1

    return candidate


def center_save_config_window():
    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()
    window_x = max(0, (viewport_width - SAVE_CONFIG_WINDOW_WIDTH) // 2)
    window_y = max(0, (viewport_height - SAVE_CONFIG_WINDOW_HEIGHT) // 2)
    dpg.set_item_pos(SAVE_CONFIG_WINDOW_TAG, [window_x, window_y])


def open_save_config_form(sender=None, app_data=None, user_data=None):
    if state["config"] is None:
        dpg.set_value(CONFIG_STATUS_TAG, "Prvo izaberi konfiguraciju.")
        return

    dpg.set_value(
        SAVE_CONFIG_NAME_INPUT_TAG,
        next_config_name(state["config_name"]),
    )
    dpg.set_value(SAVE_CONFIG_STATUS_TAG, "")
    dpg.configure_item(SAVE_CONFIG_WINDOW_TAG, show=True)
    center_save_config_window()
    dpg.focus_item(SAVE_CONFIG_NAME_INPUT_TAG)


def close_save_config_form(sender=None, app_data=None, user_data=None):
    dpg.configure_item(SAVE_CONFIG_WINDOW_TAG, show=False)


def save_current_config_as_new(sender=None, app_data=None, user_data=None):
    config = state["config"]

    if config is None:
        dpg.set_value(SAVE_CONFIG_STATUS_TAG, "Nijedna konfiguracija nije izabrana.")
        return

    try:
        saved_config_name = save_realtime_config(
            dpg.get_value(SAVE_CONFIG_NAME_INPUT_TAG),
            config,
        )
        config_names = find_realtime_configs()
        dpg.configure_item(CONFIG_COMBO_TAG, items=config_names)
        dpg.set_value(CONFIG_COMBO_TAG, saved_config_name)
        dpg.configure_item(SAVE_CONFIG_WINDOW_TAG, show=False)
        select_realtime_config()
        dpg.set_value(CONFIG_STATUS_TAG, f"Sacuvana nova konfiguracija: {saved_config_name}")

    except Exception as error:
        dpg.set_value(SAVE_CONFIG_STATUS_TAG, str(error))


def update_config_status():
    config = state["config"]
    config_name = state["config_name"]

    if config is None or config_name is None:
        dpg.set_value(CONFIG_STATUS_TAG, "")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        return

    details = (
        f"Uklanjanje pocetka: "
        f"{config_value(config, 'STARTUP_TRIM_SECONDS', 0.0)} s\n"
        f"Invertovanje signala: "
        f"{config_value(config, 'INVERT_PROCESSED_SIGNAL', False)}\n"
        f"\n"
        f"Kombinovanje kanala:\n"
        f"  Oduzimanje kanala: {config_value(config, 'CHANNEL_SUBTRACTION', 'none')}\n"
        f"\n"
        f"Uklanjanje DC komponente:\n"
        f"  Omoguceno: {config_value(config, 'DC_REMOVAL_ENABLED', False)}\n"
        f"  Tip prozora: {config_value(config, 'DC_REMOVAL_WINDOW_TYPE', 'causal')}\n"
        f"  Trajanje prozora: {config_value(config, 'DC_REMOVAL_WINDOW_SECONDS', 2.0)} s\n"
        f"\n"
        f"Filtriranje signala:\n"
        f"  Visokopropusni filter: "
        f"{config_value(config, 'HIGH_PASS_FILTER_ENABLED', False)}\n"
        f"  High-pass granica: "
        f"{config_value(config, 'HIGH_PASS_CUTOFF_HZ', 0.5)} Hz\n"
        f"  High-pass broj prolaza: "
        f"{config_value(config, 'HIGH_PASS_FILTER_PASSES', 1)}\n"
        f"  Niskopropusni filter: "
        f"{config_value(config, 'LOW_PASS_FILTER_ENABLED', False)}\n"
        f"  Low-pass granica: "
        f"{config_value(config, 'LOW_PASS_CUTOFF_HZ', 5.0)} Hz\n"
        f"  Low-pass broj prolaza: "
        f"{config_value(config, 'LOW_PASS_FILTER_PASSES', 1)}\n"
        f"\n"
        f"Detekcija vrhova:\n"
        f"  Omoguceno: {config_value(config, 'PEAK_DETECTION_ENABLED', False)}\n"
        f"  Minimalno rastojanje: {config_value(config, 'PEAK_MIN_DISTANCE_SECONDS', 0.4)} s\n"
        f"  Minimalna visina: {config_value(config, 'PEAK_MIN_HEIGHT', 0.0)}\n"
    )

    dpg.set_value(CONFIG_STATUS_TAG, "")
    dpg.set_value(CONFIG_DETAILS_TEXT_TAG, details)
    dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=True)


def set_data(x_values, signals):
    state["x_values"] = list(x_values)
    state["signals"] = {
        signal_name: list(signal_values)
        for signal_name, signal_values in signals.items()
    }
    reset_realtime()


def get_green_values():
    return state["signals"].get("green", [])


def get_arrived_data():
    sample_count = min(len(state["x_values"]), len(get_green_values()))
    current_index = min(state["current_index"], sample_count)
    arrived_x_values = state["x_values"][:current_index]
    arrived_signals = {
        signal_name: signal_values[:current_index]
        for signal_name, signal_values in state["signals"].items()
    }

    return arrived_x_values, arrived_signals


def update_processed_data():
    config = state["config"]
    arrived_x_values, arrived_signals = get_arrived_data()

    if config is None or not arrived_x_values or "green" not in arrived_signals:
        state["processed_x_values"] = []
        state["processed_green"] = []
        state["peak_x_values"] = []
        state["peak_green_values"] = []
        return

    processed_x_values, processed_green = process_green_signal(
        arrived_x_values,
        arrived_signals,
        config,
    )
    state["processed_x_values"] = processed_x_values
    state["processed_green"] = processed_green

    peak_x_values, peak_green_values = detect_peaks(
        processed_x_values,
        processed_green,
        config,
    )
    state["peak_x_values"] = peak_x_values
    state["peak_green_values"] = peak_green_values


def update_status():
    if not dpg.does_item_exist(REALTIME_STATUS_TAG):
        return

    sample_count = min(len(state["x_values"]), len(get_green_values()))

    if sample_count == 0:
        dpg.set_value(REALTIME_STATUS_TAG, "Nema ucitanih podataka.")
        return

    current_index = min(state["current_index"], sample_count)
    current_time = state["x_values"][current_index - 1] if current_index > 0 else 0.0
    status = "Pokrenuto" if state["is_running"] else "Pauzirano"

    dpg.set_value(
        REALTIME_STATUS_TAG,
        (
            f"{status} | "
            f"Prikazano: {current_index}/{sample_count} uzoraka | "
            f"Vrijeme: {current_time:.2f} s"
        ),
    )


def set_plot_data(series_tag, x_axis_tag, y_axis_tag, x_values, y_values):
    if not dpg.does_item_exist(series_tag):
        return

    dpg.set_value(series_tag, [x_values, y_values])

    if not x_values or not y_values:
        return

    x_min = x_values[0]
    x_max = x_values[-1]

    if x_min == x_max:
        x_max = x_min + 0.1

    y_min = min(y_values)
    y_max = max(y_values)
    padding = max((y_max - y_min) * 0.08, 1.0)

    dpg.set_axis_limits(x_axis_tag, x_min, x_max)
    dpg.set_axis_limits(y_axis_tag, y_min - padding, y_max + padding)


def update_original_plot(current_index):
    green_values = get_green_values()
    window_size = max(10, REALTIME_WINDOW_SIZE)
    start_index = max(0, current_index - window_size)

    visible_x_values = state["x_values"][start_index:current_index]
    visible_green_values = green_values[start_index:current_index]
    state["visible_original_x_values"] = visible_x_values
    state["visible_original_green_values"] = visible_green_values

    set_plot_data(
        REALTIME_ORIGINAL_GREEN_SERIES_TAG,
        REALTIME_ORIGINAL_GREEN_X_AXIS_TAG,
        REALTIME_ORIGINAL_GREEN_Y_AXIS_TAG,
        visible_x_values,
        visible_green_values,
    )


def update_processed_plot():
    processed_count = min(
        len(state["processed_x_values"]),
        len(state["processed_green"]),
    )
    window_size = max(10, REALTIME_WINDOW_SIZE)
    start_index = max(0, processed_count - window_size)

    visible_x_values = state["processed_x_values"][start_index:processed_count]
    visible_green_values = state["processed_green"][start_index:processed_count]
    state["visible_processed_x_values"] = visible_x_values
    state["visible_processed_green_values"] = visible_green_values

    set_plot_data(
        REALTIME_PROCESSED_GREEN_SERIES_TAG,
        REALTIME_PROCESSED_GREEN_X_AXIS_TAG,
        REALTIME_PROCESSED_GREEN_Y_AXIS_TAG,
        visible_x_values,
        visible_green_values,
    )

    if visible_x_values:
        visible_peak_x_values, visible_peak_green_values = filter_points_by_x_range(
            state["peak_x_values"],
            state["peak_green_values"],
            visible_x_values[0],
            visible_x_values[-1],
        )
    else:
        visible_peak_x_values = []
        visible_peak_green_values = []

    set_scatter_data(
        REALTIME_PROCESSED_PEAKS_SERIES_TAG,
        visible_peak_x_values,
        visible_peak_green_values,
    )


def update_plots():
    sample_count = min(len(state["x_values"]), len(get_green_values()))
    current_index = min(state["current_index"], sample_count)

    update_processed_data()
    update_original_plot(current_index)
    update_processed_plot()
    update_status()
    update_final_processed_plot()


def apply_runtime_config(
        startup_trim_seconds,
        channel_subtraction,
        dc_removal_enabled,
        dc_removal_window_type,
        dc_removal_window_seconds,
        invert_processed_signal,
        high_pass_filter_enabled,
        high_pass_cutoff_hz,
        low_pass_filter_enabled,
        low_pass_cutoff_hz,
        high_pass_filter_passes,
        low_pass_filter_passes,
        peak_detection_enabled,
        peak_min_distance_seconds,
        peak_min_height,
):
    config = state["config"]
    config_name = state["config_name"]

    if config is None or config_name is None:
        raise ValueError("Nijedna konfiguracija nije izabrana.")

    config.STARTUP_TRIM_SECONDS = startup_trim_seconds
    config.CHANNEL_SUBTRACTION = channel_subtraction
    config.DC_REMOVAL_ENABLED = dc_removal_enabled
    config.DC_REMOVAL_WINDOW_TYPE = dc_removal_window_type
    config.DC_REMOVAL_WINDOW_SECONDS = dc_removal_window_seconds
    config.INVERT_PROCESSED_SIGNAL = invert_processed_signal
    config.HIGH_PASS_FILTER_ENABLED = high_pass_filter_enabled
    config.HIGH_PASS_CUTOFF_HZ = high_pass_cutoff_hz
    config.LOW_PASS_FILTER_ENABLED = low_pass_filter_enabled
    config.LOW_PASS_CUTOFF_HZ = low_pass_cutoff_hz
    config.HIGH_PASS_FILTER_PASSES = high_pass_filter_passes
    config.LOW_PASS_FILTER_PASSES = low_pass_filter_passes
    config.PEAK_DETECTION_ENABLED = peak_detection_enabled
    config.PEAK_MIN_DISTANCE_SECONDS = peak_min_distance_seconds
    config.PEAK_MIN_HEIGHT = peak_min_height

    update_plots()
    update_config_status()


def open_config_form(sender=None, app_data=None, user_data=None):
    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if not selected_config or state["config"] is None:
        dpg.set_value(CONFIG_STATUS_TAG, "Prvo izaberi konfiguraciju.")
        return

    config_ui.open_config_form(selected_config, state["config"])


def select_realtime_config(sender=None, app_data=None, user_data=None):
    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if not selected_config:
        state["config"] = None
        state["config_name"] = None
        dpg.set_value(CONFIG_STATUS_TAG, "Nije izabrana konfiguracija.")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        update_plots()
        return

    try:
        state["config"] = load_realtime_config(selected_config)
        state["config_name"] = selected_config
        update_plots()
        update_config_status()

    except Exception as error:
        state["config"] = None
        state["config_name"] = None
        state["processed_x_values"] = []
        state["processed_green"] = []
        dpg.set_value(CONFIG_STATUS_TAG, f"Greska pri ucitavanju konfiguracije: {error}")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        update_plots()


def refresh_realtime_config_list(sender=None, app_data=None, user_data=None, select_first=False):
    config_names = find_realtime_configs()
    dpg.configure_item(CONFIG_COMBO_TAG, items=config_names)

    if not config_names:
        state["config"] = None
        state["config_name"] = None
        dpg.set_value(CONFIG_COMBO_TAG, "")
        dpg.set_value(CONFIG_STATUS_TAG, "Nema dostupnih konfiguracija.")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        update_plots()
        return

    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if select_first or selected_config not in config_names:
        dpg.set_value(CONFIG_COMBO_TAG, config_names[0])

    select_realtime_config()


def schedule_next_tick():
    if not state["is_running"]:
        return

    dpg.set_frame_callback(
        dpg.get_frame_count() + REALTIME_FRAME_INTERVAL,
        realtime_tick,
    )


def realtime_tick(sender=None, app_data=None, user_data=None):
    if not state["is_running"]:
        return

    sample_count = min(len(state["x_values"]), len(get_green_values()))

    if sample_count == 0:
        state["is_running"] = False
        update_plots()
        return

    samples_per_tick = max(1, REALTIME_SAMPLES_PER_TICK)
    state["current_index"] = min(
        state["current_index"] + samples_per_tick,
        sample_count,
    )

    if state["current_index"] >= sample_count:
        state["is_running"] = False
        state["show_final_processed_plot"] = True

    update_plots()
    schedule_next_tick()


def start_realtime(sender=None, app_data=None, user_data=None):
    sample_count = min(len(state["x_values"]), len(get_green_values()))

    if sample_count == 0:
        update_status()
        return

    if state["is_running"]:
        update_status()
        return

    if state["current_index"] >= sample_count:
        state["current_index"] = 0

    state["is_running"] = True
    update_plots()
    schedule_next_tick()
    hide_final_processed_plot()


def pause_realtime(sender=None, app_data=None, user_data=None):
    state["is_running"] = False
    update_status()


def reset_realtime(sender=None, app_data=None, user_data=None):
    state["is_running"] = False
    state["current_index"] = 0
    state["processed_x_values"] = []
    state["processed_green"] = []
    state["visible_original_x_values"] = []
    state["visible_original_green_values"] = []
    state["visible_processed_x_values"] = []
    state["visible_processed_green_values"] = []
    state["peak_x_values"] = []
    state["peak_green_values"] = []
    update_plots()

def create_signal_plot(
    label,
    series_label,
    series_tag,
    x_axis_tag,
    y_axis_tag,
    peak_series_tag=None,
    peak_series_label=None,
):
    with dpg.plot(label=label, width=-1, height=REALTIME_PLOT_HEIGHT):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Vrijeme [s]", tag=x_axis_tag)
        dpg.add_plot_axis(dpg.mvYAxis, label="Green", tag=y_axis_tag)
        dpg.add_line_series([], [], label=series_label, parent=y_axis_tag, tag=series_tag)
        if peak_series_tag is not None:
            dpg.add_scatter_series(
                [],
                [],
                label=peak_series_label,
                parent=y_axis_tag,
                tag=peak_series_tag,
            )


def create_save_config_window():
    with dpg.window(
        label="Sacuvaj novu realtime konfiguraciju",
        tag=SAVE_CONFIG_WINDOW_TAG,
        width=SAVE_CONFIG_WINDOW_WIDTH,
        height=SAVE_CONFIG_WINDOW_HEIGHT,
        modal=True,
        show=False,
        no_resize=True,
        no_collapse=True,
    ):
        dpg.add_text("Ime konfiguracije")
        dpg.add_input_text(tag=SAVE_CONFIG_NAME_INPUT_TAG, width=-1)
        dpg.add_spacer(height=6)
        dpg.add_text("", tag=SAVE_CONFIG_STATUS_TAG, color=(239, 68, 68, 255), wrap=380)
        dpg.add_spacer(height=6)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Sacuvaj", width=100, callback=save_current_config_as_new)
            dpg.add_button(label="Odustani", width=100, callback=close_save_config_form)


def create():
    original_green_theme = create_line_theme((34, 197, 94, 255), 2.0)
    processed_green_theme = create_line_theme((255, 215, 0, 255), 2.0)

    with dpg.child_window(width=-1, height=-1, border=True):
        with dpg.group(horizontal=True):
            dpg.add_text("Konfiguracija:")
            dpg.add_combo(
                [],
                width=300,
                tag=CONFIG_COMBO_TAG,
                callback=select_realtime_config,
            )
            dpg.add_button(label="Osvjezi", callback=refresh_realtime_config_list)
            dpg.add_button(label="Izmijeni", callback=open_config_form)
            dpg.add_button(label="Sacuvaj novu konfiguraciju", callback=open_save_config_form)
            dpg.add_button(label="Detalji", tag=CONFIG_DETAILS_BUTTON_TAG, show=False)

            with dpg.tooltip(parent=CONFIG_DETAILS_BUTTON_TAG):
                dpg.add_text("", tag=CONFIG_DETAILS_TEXT_TAG)

        dpg.add_spacer(height=6)
        dpg.add_text("", tag=CONFIG_STATUS_TAG)
        dpg.add_spacer(height=6)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Start", callback=start_realtime)
            dpg.add_button(label="Pauza", callback=pause_realtime)
            dpg.add_button(label="Reset", callback=reset_realtime)

        dpg.add_spacer(height=6)
        dpg.add_text("Nema ucitanih podataka.", tag=REALTIME_STATUS_TAG)
        dpg.add_spacer(height=8)

        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            width=-1,
        ):
            dpg.add_table_column(init_width_or_weight=1.0)
            dpg.add_table_column(init_width_or_weight=1.0)

            with dpg.table_row():
                create_signal_plot(
                    "Realtime Original Green signal",
                    "Original Green",
                    REALTIME_ORIGINAL_GREEN_SERIES_TAG,
                    REALTIME_ORIGINAL_GREEN_X_AXIS_TAG,
                    REALTIME_ORIGINAL_GREEN_Y_AXIS_TAG,
                )

                create_signal_plot(
                    "Realtime Processed Green signal",
                    "Processed Green",
                    REALTIME_PROCESSED_GREEN_SERIES_TAG,
                    REALTIME_PROCESSED_GREEN_X_AXIS_TAG,
                    REALTIME_PROCESSED_GREEN_Y_AXIS_TAG,
                    REALTIME_PROCESSED_PEAKS_SERIES_TAG,
                    "Detected Peaks",
                )

        dpg.add_spacer(height=8)

        with dpg.child_window(
            tag=REALTIME_FINAL_PROCESSED_CONTAINER_TAG,
            width=-1,
            height=REALTIME_PLOT_HEIGHT + 55,
            border=True,
            show=False,
        ):
            create_signal_plot(
                "Final Processed Green signal",
                "Final Processed Green",
                REALTIME_FINAL_PROCESSED_GREEN_SERIES_TAG,
                REALTIME_FINAL_PROCESSED_GREEN_X_AXIS_TAG,
                REALTIME_FINAL_PROCESSED_GREEN_Y_AXIS_TAG,
                REALTIME_FINAL_PROCESSED_PEAKS_SERIES_TAG,
                "Detected Peaks",
            )

    create_save_config_window()

    dpg.bind_item_theme(REALTIME_ORIGINAL_GREEN_SERIES_TAG, original_green_theme)
    dpg.bind_item_theme(REALTIME_PROCESSED_GREEN_SERIES_TAG, processed_green_theme)
    dpg.bind_item_theme(REALTIME_FINAL_PROCESSED_GREEN_SERIES_TAG, processed_green_theme)
    refresh_realtime_config_list(select_first=True)
    update_plots()


def create_config_form():
    config_ui.create(apply_runtime_config)


def set_visible_range(start, end):
    state["visible_range_start"] = int(start)
    state["visible_range_end"] = int(end)
    update_final_processed_plot()


def set_scatter_data(series_tag, x_values, y_values):
    if not dpg.does_item_exist(series_tag):
        return

    dpg.set_value(series_tag, [x_values, y_values])


def filter_points_by_x_range(x_values, y_values, x_min, x_max):
    visible_x_values = []
    visible_y_values = []

    for x_value, y_value in zip(x_values, y_values):
        if x_min <= x_value <= x_max:
            visible_x_values.append(x_value)
            visible_y_values.append(y_value)

    return visible_x_values, visible_y_values


def hide_final_processed_plot():
    state["show_final_processed_plot"] = False

    if dpg.does_item_exist(REALTIME_FINAL_PROCESSED_CONTAINER_TAG):
        dpg.configure_item(REALTIME_FINAL_PROCESSED_CONTAINER_TAG, show=False)


def get_final_processed_visible_data():
    processed_x_values = state["processed_x_values"]
    processed_green = state["processed_green"]

    if not processed_x_values or not processed_green:
        return [], []

    if not state["x_values"]:
        return processed_x_values, processed_green

    start_index = max(0, min(state["visible_range_start"], len(state["x_values"]) - 1))
    end_index = max(start_index + 1, min(state["visible_range_end"], len(state["x_values"])))

    x_min = state["x_values"][start_index]
    x_max = state["x_values"][end_index - 1]

    visible_x_values = []
    visible_green_values = []

    for x_value, green_value in zip(processed_x_values, processed_green):
        if x_min <= x_value <= x_max:
            visible_x_values.append(x_value)
            visible_green_values.append(green_value)

    return visible_x_values, visible_green_values


def update_final_processed_plot():
    if not dpg.does_item_exist(REALTIME_FINAL_PROCESSED_CONTAINER_TAG):
        return

    dpg.configure_item(
        REALTIME_FINAL_PROCESSED_CONTAINER_TAG,
        show=state["show_final_processed_plot"],
    )

    if not state["show_final_processed_plot"]:
        return

    visible_x_values, visible_green_values = get_final_processed_visible_data()

    set_plot_data(
        REALTIME_FINAL_PROCESSED_GREEN_SERIES_TAG,
        REALTIME_FINAL_PROCESSED_GREEN_X_AXIS_TAG,
        REALTIME_FINAL_PROCESSED_GREEN_Y_AXIS_TAG,
        visible_x_values,
        visible_green_values,
    )

    if visible_x_values:
        visible_peak_x_values, visible_peak_green_values = filter_points_by_x_range(
            state["peak_x_values"],
            state["peak_green_values"],
            visible_x_values[0],
            visible_x_values[-1],
        )
    else:
        visible_peak_x_values = []
        visible_peak_green_values = []

    set_scatter_data(
        REALTIME_FINAL_PROCESSED_PEAKS_SERIES_TAG,
        visible_peak_x_values,
        visible_peak_green_values,
    )