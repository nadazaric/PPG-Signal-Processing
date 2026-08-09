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

ORIGINAL_GREEN_SERIES_TAG = "static_original_green_series"
ORIGINAL_GREEN_X_AXIS_TAG = "static_original_green_x_axis"
ORIGINAL_GREEN_Y_AXIS_TAG = "static_original_green_y_axis"

PROCESSED_GREEN_SERIES_TAG = "static_processed_green_series"
PROCESSED_GREEN_X_AXIS_TAG = "static_processed_green_x_axis"
PROCESSED_GREEN_Y_AXIS_TAG = "static_processed_green_y_axis"


state = {
    "x_values": [],
    "signals": {},
    "processed_x_values": [],
    "processed_green": [],
    "config": None,
    "config_name": None,
    "start_index": 0,
    "end_index": None,
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
    config_path = (
        STATIC_CONFIGS_DIR
        / f"{config_name}.py"
    )

    if not config_path.exists():
        raise FileNotFoundError(
            f"Konfiguracija ne postoji: {config_path}"
        )

    config_module = types.ModuleType(
        f"static_config_{config_name}"
    )

    config_content = config_path.read_text(
        encoding="utf-8",
    )

    exec(
        compile(
            config_content,
            str(config_path),
            "exec",
        ),
        config_module.__dict__,
    )

    return config_module


def update_config_status():
    config = state["config"]
    config_name = state["config_name"]

    if config is None or config_name is None:
        dpg.set_value(
            CONFIG_STATUS_TAG,
            "",
        )

        dpg.set_value(
            CONFIG_DETAILS_TEXT_TAG,
            "",
        )

        dpg.configure_item(
            CONFIG_DETAILS_BUTTON_TAG,
            show=False,
        )
        return

    startup_trim_seconds = getattr(
        config,
        "STARTUP_TRIM_SECONDS",
        0.0,
    )

    channel_subtraction = getattr(
        config,
        "CHANNEL_SUBTRACTION",
        "none",
    )

    dpg.set_value(
        CONFIG_DETAILS_TEXT_TAG,
        (
            "Uklanjanje pocetka: "
            f"{startup_trim_seconds} s\n"
            "Oduzimanje kanala: "
            f"{channel_subtraction}"
        ),
    )

    dpg.configure_item(
        CONFIG_DETAILS_BUTTON_TAG,
        show=True,
    )


def process_current_data():
    config = state["config"]
    signals = state["signals"]

    required_signals = (
        "green",
        "red",
        "infrared",
    )

    has_all_signals = all(
        signal_name in signals
        and len(signals[signal_name]) > 0
        for signal_name in required_signals
    )

    if (
        config is None
        or not state["x_values"]
        or not has_all_signals
    ):
        state["processed_x_values"] = []
        state["processed_green"] = []
        return

    (
        state["processed_x_values"],
        state["processed_green"],
    ) = process_green_signal(
        state["x_values"],
        signals,
        config,
    )


def apply_runtime_config(
    startup_trim_seconds,
    channel_subtraction,
):
    config = state["config"]

    if config is None:
        raise ValueError(
            "Nijedna konfiguracija nije izabrana."
        )

    config.STARTUP_TRIM_SECONDS = (
        startup_trim_seconds
    )

    config.CHANNEL_SUBTRACTION = (
        channel_subtraction
    )

    process_current_data()
    update_plots()
    update_config_status()


def open_config_form(
    sender=None,
    app_data=None,
    user_data=None,
):
    selected_config = dpg.get_value(
        CONFIG_COMBO_TAG
    )

    if (
        not selected_config
        or state["config"] is None
    ):
        dpg.set_value(
            CONFIG_STATUS_TAG,
            "Prvo izaberi konfiguraciju.",
        )
        return

    config_ui.open_config_form(
        selected_config,
        state["config"],
    )


def set_plot_data(
    series_tag,
    x_axis_tag,
    y_axis_tag,
    x_values,
    y_values,
):
    if not dpg.does_item_exist(series_tag):
        return

    data_size = min(
        len(x_values),
        len(y_values),
    )

    if data_size == 0:
        dpg.set_value(
            series_tag,
            [[], []],
        )
        return

    visible_x_values = x_values[:data_size]
    visible_y_values = y_values[:data_size]

    dpg.set_value(
        series_tag,
        [
            visible_x_values,
            visible_y_values,
        ],
    )

    dpg.fit_axis_data(
        x_axis_tag,
    )

    dpg.fit_axis_data(
        y_axis_tag,
    )


def update_plots():
    original_green = list(
        state["signals"].get(
            "green",
            [],
        )
    )

    original_data_size = min(
        len(state["x_values"]),
        len(original_green),
    )

    start_index = min(
        state["start_index"],
        original_data_size,
    )

    if state["end_index"] is None:
        end_index = original_data_size
    else:
        end_index = min(
            state["end_index"],
            original_data_size,
        )

    visible_x_values = state["x_values"][
        start_index:end_index
    ]

    visible_original_green = original_green[
        start_index:end_index
    ]

    set_plot_data(
        ORIGINAL_GREEN_SERIES_TAG,
        ORIGINAL_GREEN_X_AXIS_TAG,
        ORIGINAL_GREEN_Y_AXIS_TAG,
        visible_x_values,
        visible_original_green,
    )

    if not visible_x_values:
        set_plot_data(
            PROCESSED_GREEN_SERIES_TAG,
            PROCESSED_GREEN_X_AXIS_TAG,
            PROCESSED_GREEN_Y_AXIS_TAG,
            [],
            [],
        )
        return

    visible_start_time = visible_x_values[0]
    visible_end_time = visible_x_values[-1]

    processed_start_index = next(
        (
            index
            for index, x_value in enumerate(
                state["processed_x_values"]
            )
            if x_value >= visible_start_time
        ),
        len(state["processed_x_values"]),
    )

    processed_end_index = next(
        (
            index
            for index, x_value in enumerate(
                state["processed_x_values"]
            )
            if x_value > visible_end_time
        ),
        len(state["processed_x_values"]),
    )

    visible_processed_x = (
        state["processed_x_values"][
            processed_start_index:
            processed_end_index
        ]
    )

    visible_processed_green = (
        state["processed_green"][
            processed_start_index:
            processed_end_index
        ]
    )

    set_plot_data(
        PROCESSED_GREEN_SERIES_TAG,
        PROCESSED_GREEN_X_AXIS_TAG,
        PROCESSED_GREEN_Y_AXIS_TAG,
        visible_processed_x,
        visible_processed_green,
    )


def select_static_config(
    sender=None,
    app_data=None,
    user_data=None,
):
    selected_config = dpg.get_value(
        CONFIG_COMBO_TAG
    )

    if not selected_config:
        state["config"] = None
        state["config_name"] = None

        dpg.set_value(
            CONFIG_STATUS_TAG,
            "Nije izabrana konfiguracija.",
        )

        dpg.set_value(
            CONFIG_DETAILS_TEXT_TAG,
            "",
        )

        dpg.configure_item(
            CONFIG_DETAILS_BUTTON_TAG,
            show=False,
        )

        process_current_data()
        update_plots()
        return

    try:
        state["config"] = load_static_config(
            selected_config,
        )

        state["config_name"] = selected_config

        process_current_data()
        update_plots()
        update_config_status()

    except Exception as error:
        state["config"] = None
        state["config_name"] = None
        state["processed_x_values"] = []
        state["processed_green"] = []

        dpg.set_value(
            CONFIG_STATUS_TAG,
            (
                "Greska pri ucitavanju "
                f"konfiguracije: {error}"
            ),
        )

        dpg.set_value(
            CONFIG_DETAILS_TEXT_TAG,
            "",
        )

        dpg.configure_item(
            CONFIG_DETAILS_BUTTON_TAG,
            show=False,
        )

        update_plots()


def refresh_static_config_list(
    sender=None,
    app_data=None,
    user_data=None,
    select_first=False,
):
    config_names = find_static_configs()

    dpg.configure_item(
        CONFIG_COMBO_TAG,
        items=config_names,
    )

    if not config_names:
        state["config"] = None
        state["config_name"] = None

        dpg.set_value(
            CONFIG_COMBO_TAG,
            "",
        )

        dpg.set_value(
            CONFIG_STATUS_TAG,
            "Nema dostupnih konfiguracija.",
        )

        dpg.set_value(
            CONFIG_DETAILS_TEXT_TAG,
            "",
        )

        dpg.configure_item(
            CONFIG_DETAILS_BUTTON_TAG,
            show=False,
        )

        process_current_data()
        update_plots()
        return

    selected_config = dpg.get_value(
        CONFIG_COMBO_TAG
    )

    if (
        select_first
        or selected_config not in config_names
    ):
        dpg.set_value(
            CONFIG_COMBO_TAG,
            config_names[0],
        )

    select_static_config()


def set_data(
    x_values,
    signals,
):
    state["x_values"] = list(x_values)
    state["signals"] = signals
    state["start_index"] = 0
    state["end_index"] = len(
        state["x_values"]
    )

    process_current_data()
    update_plots()


def create_line_theme(
    color,
    line_weight,
):
    with dpg.theme() as line_theme:
        with dpg.theme_component(
            dpg.mvLineSeries
        ):
            dpg.add_theme_color(
                dpg.mvPlotCol_Line,
                color,
                category=dpg.mvThemeCat_Plots,
            )

            dpg.add_theme_style(
                dpg.mvPlotStyleVar_LineWeight,
                line_weight,
                category=dpg.mvThemeCat_Plots,
            )

    return line_theme


def create_signal_plot(
    label,
    series_label,
    series_tag,
    x_axis_tag,
    y_axis_tag,
):
    with dpg.plot(
        label=label,
        width=-1,
        height=350,
    ):
        dpg.add_plot_legend()

        dpg.add_plot_axis(
            dpg.mvXAxis,
            label="Vrijeme [s]",
            tag=x_axis_tag,
        )

        dpg.add_plot_axis(
            dpg.mvYAxis,
            label="Green",
            tag=y_axis_tag,
        )

        dpg.add_line_series(
            [],
            [],
            label=series_label,
            parent=y_axis_tag,
            tag=series_tag,
        )


def create():
    original_green_theme = create_line_theme(
        color=(34, 197, 94, 255),
        line_weight=2.0,
    )

    processed_green_theme = create_line_theme(
        color=(255, 215, 0, 255),
        line_weight=2.5,
    )

    with dpg.child_window(
        width=-1,
        height=-1,
        border=True,
    ):
        with dpg.group(horizontal=True):
            dpg.add_text(
                "Konfiguracija:"
            )

            dpg.add_combo(
                [],
                width=300,
                tag=CONFIG_COMBO_TAG,
                callback=select_static_config,
            )

            dpg.add_button(
                label="Osvjezi",
                callback=refresh_static_config_list,
            )

            dpg.add_button(
                label="Izmijeni",
                callback=open_config_form,
            )

            dpg.add_button(
                label="Detalji",
                tag=CONFIG_DETAILS_BUTTON_TAG,
                show=False,
            )

            with dpg.tooltip(
                    parent=CONFIG_DETAILS_BUTTON_TAG,
            ):
                dpg.add_text(
                    "",
                    tag=CONFIG_DETAILS_TEXT_TAG,
                )

        dpg.add_spacer(
            height=6,
        )

        create_signal_plot(
            label="Original Green signal",
            series_label="Original Green",
            series_tag=ORIGINAL_GREEN_SERIES_TAG,
            x_axis_tag=ORIGINAL_GREEN_X_AXIS_TAG,
            y_axis_tag=ORIGINAL_GREEN_Y_AXIS_TAG,
        )

        dpg.add_spacer(
            height=10,
        )

        create_signal_plot(
            label="Processed Green signal",
            series_label="Processed Green",
            series_tag=PROCESSED_GREEN_SERIES_TAG,
            x_axis_tag=PROCESSED_GREEN_X_AXIS_TAG,
            y_axis_tag=PROCESSED_GREEN_Y_AXIS_TAG,
        )

    dpg.bind_item_theme(
        ORIGINAL_GREEN_SERIES_TAG,
        original_green_theme,
    )

    dpg.bind_item_theme(
        PROCESSED_GREEN_SERIES_TAG,
        processed_green_theme,
    )

    refresh_static_config_list(
        select_first=True,
    )

    update_plots()


def create_config_form():
    config_ui.create(
        on_apply=apply_runtime_config,
    )


def set_visible_range(
    start_index,
    end_index,
):
    state["start_index"] = max(
        0,
        start_index,
    )

    state["end_index"] = max(
        state["start_index"],
        end_index,
    )

    update_plots()