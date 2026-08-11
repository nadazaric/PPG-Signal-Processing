import types
from pathlib import Path

import dearpygui.dearpygui as dpg

from static import config_ui
from static.processing import process_green_signal


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_CONFIGS_DIR = BASE_DIR / "static_configs"

CONFIG_COMBO_TAG = "static_config_combo"
CONFIG_STATUS_TAG = "static_config_status"
CONFIG_DETAILS_BUTTON_TAG = "static_config_details_button"
CONFIG_DETAILS_TEXT_TAG = "static_config_details_text"
HEART_RATE_STATUS_TAG = "static_heart_rate_status"

ORIGINAL_GREEN_SERIES_TAG = "static_original_green_series"
ORIGINAL_GREEN_X_AXIS_TAG = "static_original_green_x_axis"
ORIGINAL_GREEN_Y_AXIS_TAG = "static_original_green_y_axis"

PROCESSED_GREEN_SERIES_TAG = "static_processed_green_series"
PROCESSED_GREEN_X_AXIS_TAG = "static_processed_green_x_axis"
PROCESSED_GREEN_Y_AXIS_TAG = "static_processed_green_y_axis"
PROCESSED_ARTIFACT_SERIES_TAG = "static_processed_artifact_series"
PROCESSED_PEAK_SERIES_TAG = "static_processed_peak_series"

state = {
    "x_values": [],
    "signals": {},
    "processed_x_values": [],
    "processed_green": [],
    "valid_samples": [],
    "peak_indices": [],
    "config": None,
    "config_name": None,
    "start_index": 0,
    "end_index": None,
    "heart_rate_metrics": None,
}


def find_static_configs():
    if not STATIC_CONFIGS_DIR.exists():
        return []

    return sorted(
        path.stem
        for path in STATIC_CONFIGS_DIR.glob("*.py")
        if path.name != "__init__.py"
    )


def load_static_config(config_name):
    config_path = STATIC_CONFIGS_DIR / f"{config_name}.py"

    if not config_path.exists():
        raise FileNotFoundError(f"Konfiguracija ne postoji: {config_path}")

    config_module = types.ModuleType(f"static_config_{config_name}")
    config_content = config_path.read_text(encoding="utf-8")
    exec(compile(config_content, str(config_path), "exec"), config_module.__dict__)

    return config_module


def config_value(config, name, default="-"):
    return getattr(config, name, default)


def update_config_status():
    config = state["config"]
    config_name = state["config_name"]

    if config is None or config_name is None:
        dpg.set_value(CONFIG_STATUS_TAG, "")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        return

    details = (
        f"Uklanjanje pocetka: {config.STARTUP_TRIM_SECONDS} s\n"
        f"Oduzimanje kanala: {config.CHANNEL_SUBTRACTION}\n"
        f"Tip filtera: {config.FILTER_TYPE}\n"
        f"Frekvencija uzorkovanja: {config.SAMPLING_FREQUENCY_HZ} Hz\n"
        f"Invertovan signal: {config_value(config, 'INVERT_PROCESSED_SIGNAL', False)}\n"
        f"Donja granicna frekvencija: {config.LOWER_CUTOFF_FREQUENCY_HZ} Hz\n"
        f"Gornja granicna frekvencija: {config.UPPER_CUTOFF_FREQUENCY_HZ} Hz\n"
        f"Broj koeficijenata: {config.FILTER_COEFFICIENT_COUNT}\n"
        f"Tip prozora: {config.FILTER_WINDOW_TYPE}\n"
        f"Detekcija artefakata: {config_value(config, 'ARTIFACT_DETECTION_ENABLED', False)}\n"
        f"Prikaz artefakata na grafu: {config_value(config, 'SHOW_ARTIFACTS_ON_PLOT', False)}\n"
        f"Faktor praga za skok: {config_value(config, 'ARTIFACT_JUMP_THRESHOLD_FACTOR')}\n"
        f"Prosirenje artefakta: {config_value(config, 'ARTIFACT_PADDING_SECONDS')} s\n"
        f"Range detekcija artefakata: {config_value(config, 'RANGE_ARTIFACT_DETECTION_ENABLED', False)}\n"
        f"Prozor za range: {config_value(config, 'ARTIFACT_RANGE_WINDOW_SECONDS')} s\n"
        f"Faktor praga za range: {config_value(config, 'ARTIFACT_RANGE_THRESHOLD_FACTOR')}\n"
        f"Normalizacija: {config_value(config, 'NORMALIZATION_TYPE', 'none')}\n"
        f"Detekcija vrhova: {config_value(config, 'PEAK_DETECTION_ENABLED', False)}\n"
        f"Koristi minimalno rastojanje: {config_value(config, 'PEAK_MIN_DISTANCE_ENABLED', True)}\n"
        f"Minimalno rastojanje izmedju vrhova: {config_value(config, 'PEAK_MIN_DISTANCE_SECONDS', 0.4)} s\n"
        f"Koristi prominence: {config_value(config, 'PEAK_PROMINENCE_ENABLED', True)}\n"
        f"Faktor prominence: {config_value(config, 'PEAK_PROMINENCE_FACTOR', 0.6)}"
    )

    dpg.set_value(CONFIG_DETAILS_TEXT_TAG, details)
    dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=True)


def update_heart_rate_status():
    if not dpg.does_item_exist(HEART_RATE_STATUS_TAG):
        return

    metrics = state["heart_rate_metrics"]

    if not metrics:
        dpg.set_value(HEART_RATE_STATUS_TAG, "Prosjecan BPM: -")
        return

    peak_count = metrics.get("peak_count", len(state["peak_indices"]))
    rr_interval_count = metrics.get("rr_interval_count", len(metrics.get("rr_intervals", [])))
    average_bpm = metrics.get("average_bpm")

    if average_bpm is None:
        dpg.set_value(
            HEART_RATE_STATUS_TAG,
            f"Prosjecan BPM: - | Vrhovi: {peak_count} | RR intervali: {rr_interval_count}",
        )

        return

    min_bpm = metrics.get("min_bpm")
    max_bpm = metrics.get("max_bpm")
    bpm_range_text = ""

    if min_bpm is not None and max_bpm is not None:
        bpm_range_text = f" | Opseg: {min_bpm:.1f}-{max_bpm:.1f} BPM"

    dpg.set_value(
        HEART_RATE_STATUS_TAG,
        (
            f"Prosjecan BPM: {average_bpm:.1f} | "
            f"Vrhovi: {peak_count} | "
            f"RR intervali: {rr_interval_count}"
            f"{bpm_range_text}"
        ),
    )


def process_current_data():
    config = state["config"]
    signals = state["signals"]
    required_signals = ("green", "red", "infrared")
    has_all_signals = all(
        signal_name in signals and len(signals[signal_name]) > 0
        for signal_name in required_signals
    )

    if config is None or not state["x_values"] or not has_all_signals:
        state["processed_x_values"] = []
        state["processed_green"] = []
        state["valid_samples"] = []
        state["peak_indices"] = []
        state["heart_rate_metrics"] = None
        update_heart_rate_status()
        return

    processing_result = process_green_signal(state["x_values"], signals, config)
    state["processed_x_values"] = processing_result[0]
    state["processed_green"] = processing_result[1]
    state["valid_samples"] = processing_result[2]
    state["peak_indices"] = processing_result[3] if len(processing_result) > 3 else []
    state["heart_rate_metrics"] = processing_result[4] if len(processing_result) > 4 else None
    update_heart_rate_status()


def apply_runtime_config(
    startup_trim_seconds,
    channel_subtraction,
    filter_type,
    sampling_frequency,
    lower_cutoff_frequency,
    upper_cutoff_frequency,
    filter_coefficient_count,
    filter_window_type,
    artifact_detection_enabled,
    show_artifacts_on_plot,
    artifact_jump_threshold_factor,
    artifact_padding_seconds,
    range_artifact_detection_enabled,
    artifact_range_window_seconds,
    artifact_range_threshold_factor,
    normalization_type,
    invert_processed_signal,
    peak_detection_enabled,
    peak_min_distance_enabled,
    peak_min_distance_seconds,
    peak_prominence_enabled,
    peak_prominence_factor,
):
    config = state["config"]

    if config is None:
        raise ValueError("Nijedna konfiguracija nije izabrana.")

    config.STARTUP_TRIM_SECONDS = startup_trim_seconds
    config.CHANNEL_SUBTRACTION = channel_subtraction
    config.FILTER_TYPE = filter_type
    config.SAMPLING_FREQUENCY_HZ = sampling_frequency
    config.LOWER_CUTOFF_FREQUENCY_HZ = lower_cutoff_frequency
    config.UPPER_CUTOFF_FREQUENCY_HZ = upper_cutoff_frequency
    config.FILTER_COEFFICIENT_COUNT = filter_coefficient_count
    config.FILTER_WINDOW_TYPE = filter_window_type
    config.ARTIFACT_DETECTION_ENABLED = artifact_detection_enabled
    config.SHOW_ARTIFACTS_ON_PLOT = show_artifacts_on_plot
    config.ARTIFACT_JUMP_THRESHOLD_FACTOR = artifact_jump_threshold_factor
    config.ARTIFACT_PADDING_SECONDS = artifact_padding_seconds
    config.RANGE_ARTIFACT_DETECTION_ENABLED = range_artifact_detection_enabled
    config.ARTIFACT_RANGE_WINDOW_SECONDS = artifact_range_window_seconds
    config.ARTIFACT_RANGE_THRESHOLD_FACTOR = artifact_range_threshold_factor
    config.NORMALIZATION_TYPE = normalization_type
    config.INVERT_PROCESSED_SIGNAL = invert_processed_signal
    config.PEAK_DETECTION_ENABLED = peak_detection_enabled
    config.PEAK_MIN_DISTANCE_ENABLED = peak_min_distance_enabled
    config.PEAK_MIN_DISTANCE_SECONDS = peak_min_distance_seconds
    config.PEAK_PROMINENCE_ENABLED = peak_prominence_enabled
    config.PEAK_PROMINENCE_FACTOR = peak_prominence_factor

    process_current_data()
    update_plots()
    update_heart_rate_status()
    update_config_status()


def open_config_form(sender=None, app_data=None, user_data=None):
    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if not selected_config or state["config"] is None:
        dpg.set_value(CONFIG_STATUS_TAG, "Prvo izaberi konfiguraciju.")
        return

    config_ui.open_config_form(selected_config, state["config"])


def set_plot_data(series_tag, x_axis_tag, y_axis_tag, x_values, y_values):
    if not dpg.does_item_exist(series_tag):
        return

    data_size = min(len(x_values), len(y_values))

    if data_size == 0:
        dpg.set_value(series_tag, [[], []])
        return

    dpg.set_value(series_tag, [x_values[:data_size], y_values[:data_size]])
    dpg.fit_axis_data(x_axis_tag)
    dpg.fit_axis_data(y_axis_tag)


def clear_processed_plot():
    set_plot_data(
        PROCESSED_GREEN_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        [],
        [],
    )

    set_plot_data(
        PROCESSED_ARTIFACT_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        [],
        [],
    )

    set_plot_data(
        PROCESSED_PEAK_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        [],
        [],
    )


def update_plots():
    original_green = list(state["signals"].get("green", []))
    original_data_size = min(len(state["x_values"]), len(original_green))
    start_index = min(state["start_index"], original_data_size)
    end_index = original_data_size if state["end_index"] is None else min(state["end_index"], original_data_size)
    visible_x_values = state["x_values"][start_index:end_index]
    visible_original_green = original_green[start_index:end_index]

    set_plot_data(
        ORIGINAL_GREEN_SERIES_TAG,
        ORIGINAL_GREEN_X_AXIS_TAG,
        ORIGINAL_GREEN_Y_AXIS_TAG,
        visible_x_values,
        visible_original_green,
    )

    if not visible_x_values:
        clear_processed_plot()
        return

    visible_start_time = visible_x_values[0]
    visible_end_time = visible_x_values[-1]

    processed_start_index = next(
        (
            index
            for index, x_value in enumerate(state["processed_x_values"])
            if x_value >= visible_start_time
        ),
        len(state["processed_x_values"]),
    )

    processed_end_index = next(
        (
            index
            for index, x_value in enumerate(state["processed_x_values"])
            if x_value > visible_end_time
        ),
        len(state["processed_x_values"]),
    )

    visible_processed_x = state["processed_x_values"][processed_start_index:processed_end_index]
    visible_processed_green = state["processed_green"][processed_start_index:processed_end_index]

    set_plot_data(
        PROCESSED_GREEN_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        visible_processed_x,
        visible_processed_green,
    )

    update_artifact_plot(
        visible_processed_x,
        visible_processed_green,
        processed_start_index,
        processed_end_index,
    )

    update_peak_plot(processed_start_index, processed_end_index)


def update_artifact_plot(
    visible_processed_x,
    visible_processed_green,
    processed_start_index,
    processed_end_index,
):
    config = state["config"]
    show_artifacts = (
        config is not None
        and getattr(config, "ARTIFACT_DETECTION_ENABLED", False)
        and getattr(config, "SHOW_ARTIFACTS_ON_PLOT", False)
    )

    if not show_artifacts:
        set_plot_data(
            PROCESSED_ARTIFACT_SERIES_TAG,
            PROCESSED_GREEN_X_AXIS_TAG,
            PROCESSED_GREEN_Y_AXIS_TAG,
            [],
            [],
        )
        return

    visible_valid_samples = state["valid_samples"][processed_start_index:processed_end_index]
    artifact_x_values = []
    artifact_y_values = []

    for x_value, y_value, valid_sample in zip(
        visible_processed_x,
        visible_processed_green,
        visible_valid_samples,
    ):
        if valid_sample:
            continue

        artifact_x_values.append(x_value)
        artifact_y_values.append(y_value)

    set_plot_data(
        PROCESSED_ARTIFACT_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        artifact_x_values,
        artifact_y_values,
    )


def update_peak_plot(processed_start_index, processed_end_index):
    config = state["config"]
    show_peaks = config is not None and getattr(config, "PEAK_DETECTION_ENABLED", False)

    if not show_peaks:
        set_plot_data(
            PROCESSED_PEAK_SERIES_TAG,
            PROCESSED_GREEN_X_AXIS_TAG,
            PROCESSED_GREEN_Y_AXIS_TAG,
            [],
            [],
        )

        return

    peak_x_values = []
    peak_y_values = []

    for peak_index in state["peak_indices"]:
        if peak_index < processed_start_index or peak_index >= processed_end_index:
            continue

        peak_x_values.append(state["processed_x_values"][peak_index])
        peak_y_values.append(state["processed_green"][peak_index])

    set_plot_data(
        PROCESSED_PEAK_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        peak_x_values,
        peak_y_values,
    )


def select_static_config(sender=None, app_data=None, user_data=None):
    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if not selected_config:
        state["config"] = None
        state["config_name"] = None
        dpg.set_value(CONFIG_STATUS_TAG, "Nije izabrana konfiguracija.")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        process_current_data()
        update_plots()
        return

    try:
        state["config"] = load_static_config(selected_config)
        state["config_name"] = selected_config
        process_current_data()
        update_plots()
        update_config_status()

    except Exception as error:
        state["config"] = None
        state["config_name"] = None
        state["processed_x_values"] = []
        state["processed_green"] = []
        state["valid_samples"] = []
        state["peak_indices"] = []
        state["heart_rate_metrics"] = None
        update_heart_rate_status()
        dpg.set_value(CONFIG_STATUS_TAG, f"Greska pri ucitavanju konfiguracije: {error}")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        update_plots()


def refresh_static_config_list(sender=None, app_data=None, user_data=None, select_first=False):
    config_names = find_static_configs()
    dpg.configure_item(CONFIG_COMBO_TAG, items=config_names)

    if not config_names:
        state["config"] = None
        state["config_name"] = None
        dpg.set_value(CONFIG_COMBO_TAG, "")
        dpg.set_value(CONFIG_STATUS_TAG, "Nema dostupnih konfiguracija.")
        dpg.set_value(CONFIG_DETAILS_TEXT_TAG, "")
        dpg.configure_item(CONFIG_DETAILS_BUTTON_TAG, show=False)
        process_current_data()
        update_plots()
        return

    selected_config = dpg.get_value(CONFIG_COMBO_TAG)

    if select_first or selected_config not in config_names:
        dpg.set_value(CONFIG_COMBO_TAG, config_names[0])

    select_static_config()


def set_data(x_values, signals):
    state["x_values"] = list(x_values)
    state["signals"] = signals
    state["start_index"] = 0
    state["end_index"] = len(state["x_values"])

    process_current_data()
    update_plots()


def create_line_theme(color, line_weight):
    with dpg.theme() as line_theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, line_weight, category=dpg.mvThemeCat_Plots)

    return line_theme


def create_scatter_theme(color, marker_size):
    with dpg.theme() as scatter_theme:
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, marker_size, category=dpg.mvThemeCat_Plots)

    return scatter_theme


def create_signal_plot(
    label,
    series_label,
    series_tag,
    x_axis_tag,
    y_axis_tag,
    artifact_series_tag=None,
    peak_series_tag=None,
):
    with dpg.plot(label=label, width=-1, height=250):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Vrijeme [s]", tag=x_axis_tag)
        dpg.add_plot_axis(dpg.mvYAxis, label="Green", tag=y_axis_tag)
        dpg.add_line_series([], [], label=series_label, parent=y_axis_tag, tag=series_tag)

        if artifact_series_tag is not None:
            dpg.add_scatter_series([], [], label="Invalid samples", parent=y_axis_tag, tag=artifact_series_tag)

        if peak_series_tag is not None:
            dpg.add_scatter_series([], [], label="Peaks", parent=y_axis_tag, tag=peak_series_tag)


def create():
    original_green_theme = create_line_theme((34, 197, 94, 255), 2.0)
    processed_green_theme = create_line_theme((255, 215, 0, 255), 2.0)
    artifact_theme = create_scatter_theme((239, 68, 68, 255), 4.0)
    peak_theme = create_scatter_theme((59, 130, 246, 255), 5.0)

    with dpg.child_window(width=-1, height=-1, border=True):
        with dpg.group(horizontal=True):
            dpg.add_text("Konfiguracija:")
            dpg.add_combo(
                [],
                width=300,
                tag=CONFIG_COMBO_TAG,
                callback=select_static_config,
            )
            dpg.add_button(label="Osvjezi", callback=refresh_static_config_list)
            dpg.add_button(label="Izmijeni", callback=open_config_form)
            dpg.add_button(label="Detalji", tag=CONFIG_DETAILS_BUTTON_TAG, show=False)

            with dpg.tooltip(parent=CONFIG_DETAILS_BUTTON_TAG):
                dpg.add_text("", tag=CONFIG_DETAILS_TEXT_TAG)

        dpg.add_spacer(height=6)

        create_signal_plot(
            label="Original Green signal",
            series_label="Original Green",
            series_tag=ORIGINAL_GREEN_SERIES_TAG,
            x_axis_tag=ORIGINAL_GREEN_X_AXIS_TAG,
            y_axis_tag=ORIGINAL_GREEN_Y_AXIS_TAG,
        )

        dpg.add_spacer(height=10)

        create_signal_plot(
            label="Processed Green signal",
            series_label="Processed Green",
            series_tag=PROCESSED_GREEN_SERIES_TAG,
            x_axis_tag=PROCESSED_GREEN_X_AXIS_TAG,
            y_axis_tag=PROCESSED_GREEN_Y_AXIS_TAG,
            artifact_series_tag=PROCESSED_ARTIFACT_SERIES_TAG,
            peak_series_tag=PROCESSED_PEAK_SERIES_TAG,
        )

        dpg.add_text("Prosjecan BPM: -", tag=HEART_RATE_STATUS_TAG)

    dpg.bind_item_theme(ORIGINAL_GREEN_SERIES_TAG, original_green_theme)
    dpg.bind_item_theme(PROCESSED_GREEN_SERIES_TAG, processed_green_theme)
    dpg.bind_item_theme(PROCESSED_ARTIFACT_SERIES_TAG, artifact_theme)
    dpg.bind_item_theme(PROCESSED_PEAK_SERIES_TAG, peak_theme)

    refresh_static_config_list(select_first=True)
    update_plots()


def create_config_form():
    config_ui.create(apply_runtime_config)


def set_visible_range(start_index, end_index):
    state["start_index"] = max(0, start_index)
    state["end_index"] = max(state["start_index"], end_index)
    update_plots()