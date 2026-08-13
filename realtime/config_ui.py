import dearpygui.dearpygui as dpg


CONFIG_WINDOW_TAG = "realtime_config_window"
CONFIG_NAME_TAG = "realtime_config_name"
STARTUP_TRIM_INPUT_TAG = "realtime_config_startup_trim"
CONFIG_FORM_STATUS_TAG = "realtime_config_form_status"
INVERT_PROCESSED_SIGNAL_INPUT_TAG = "realtime_config_invert_processed_signal"
CHANNEL_SUBTRACTION_INPUT_TAG = "realtime_config_channel_subtraction"
DC_REMOVAL_ENABLED_INPUT_TAG = "realtime_config_dc_removal_enabled"
DC_REMOVAL_WINDOW_TYPE_INPUT_TAG = "realtime_config_dc_removal_window_type"
DC_REMOVAL_WINDOW_SECONDS_INPUT_TAG = "realtime_config_dc_removal_window_seconds"
HIGH_PASS_FILTER_ENABLED_INPUT_TAG = "realtime_config_high_pass_filter_enabled"
HIGH_PASS_CUTOFF_HZ_INPUT_TAG = "realtime_config_high_pass_cutoff_hz"
LOW_PASS_FILTER_ENABLED_INPUT_TAG = "realtime_config_low_pass_filter_enabled"
LOW_PASS_CUTOFF_HZ_INPUT_TAG = "realtime_config_low_pass_cutoff_hz"
HIGH_PASS_FILTER_PASSES_INPUT_TAG = "realtime_config_high_pass_filter_passes"
LOW_PASS_FILTER_PASSES_INPUT_TAG = "realtime_config_low_pass_filter_passes"
PEAK_DETECTION_ENABLED_INPUT_TAG = "realtime_config_peak_detection_enabled"
PEAK_MIN_DISTANCE_SECONDS_INPUT_TAG = "realtime_config_peak_min_distance_seconds"
PEAK_MIN_HEIGHT_INPUT_TAG = "realtime_config_peak_min_height"

CHANNEL_SUBTRACTION_OPTIONS = (
    "none",
    "red",
    "infrared",
    "red_infrared_mean",
)
DC_REMOVAL_WINDOW_TYPE_OPTIONS = ("causal", "centered")

CONFIG_WINDOW_WIDTH = 440
CONFIG_WINDOW_HEIGHT = 700
CONFIG_INPUT_WIDTH = 180

state = {
    "config_name": None,
    "on_apply": None,
}


def read_float(tag):
    return float(dpg.get_value(tag))


def read_int(tag):
    return int(dpg.get_value(tag))


def normalize_dc_removal_window_type(window_type):
    if window_type in DC_REMOVAL_WINDOW_TYPE_OPTIONS:
        return window_type

    return DC_REMOVAL_WINDOW_TYPE_OPTIONS[0]


def normalize_channel_subtraction(channel_subtraction):
    if channel_subtraction in CHANNEL_SUBTRACTION_OPTIONS:
        return channel_subtraction

    return CHANNEL_SUBTRACTION_OPTIONS[0]


def update_dc_removal_inputs(sender=None, app_data=None, user_data=None):
    dc_removal_enabled = bool(dpg.get_value(DC_REMOVAL_ENABLED_INPUT_TAG))

    dpg.configure_item(
        DC_REMOVAL_WINDOW_TYPE_INPUT_TAG,
        enabled=dc_removal_enabled,
    )
    dpg.configure_item(
        DC_REMOVAL_WINDOW_SECONDS_INPUT_TAG,
        enabled=dc_removal_enabled,
    )


def update_filter_inputs(sender=None, app_data=None, user_data=None):
    high_pass_enabled = bool(dpg.get_value(HIGH_PASS_FILTER_ENABLED_INPUT_TAG))
    low_pass_enabled = bool(dpg.get_value(LOW_PASS_FILTER_ENABLED_INPUT_TAG))

    dpg.configure_item(HIGH_PASS_CUTOFF_HZ_INPUT_TAG, enabled=high_pass_enabled)
    dpg.configure_item(LOW_PASS_CUTOFF_HZ_INPUT_TAG, enabled=low_pass_enabled)
    dpg.configure_item(HIGH_PASS_FILTER_PASSES_INPUT_TAG, enabled=high_pass_enabled)
    dpg.configure_item(LOW_PASS_FILTER_PASSES_INPUT_TAG, enabled=low_pass_enabled)


def update_peak_detection_inputs(sender=None, app_data=None, user_data=None):
    peak_detection_enabled = bool(dpg.get_value(PEAK_DETECTION_ENABLED_INPUT_TAG))

    dpg.configure_item(
        PEAK_MIN_DISTANCE_SECONDS_INPUT_TAG,
        enabled=peak_detection_enabled,
    )
    dpg.configure_item(
        PEAK_MIN_HEIGHT_INPUT_TAG,
        enabled=peak_detection_enabled,
    )


def validate_config_values(
        startup_trim_seconds,
        dc_removal_enabled,
        dc_removal_window_seconds,
        high_pass_enabled,
        high_pass_cutoff_hz,
        low_pass_enabled,
        low_pass_cutoff_hz,
        high_pass_filter_passes,
        low_pass_filter_passes,
        peak_detection_enabled,
        peak_min_distance_seconds,
):
    if startup_trim_seconds < 0:
        raise ValueError("Vrijeme uklanjanja pocetka ne moze biti negativno.")

    if dc_removal_enabled and dc_removal_window_seconds <= 0:
        raise ValueError("Prozor za DC mora biti veci od 0.")

    if high_pass_enabled and high_pass_cutoff_hz <= 0:
        raise ValueError("High-pass granicna frekvencija mora biti veca od 0.")

    if low_pass_enabled and low_pass_cutoff_hz <= 0:
        raise ValueError("Low-pass granicna frekvencija mora biti veca od 0.")

    if high_pass_enabled and low_pass_enabled and high_pass_cutoff_hz >= low_pass_cutoff_hz:
        raise ValueError("High-pass granica mora biti manja od low-pass granice.")

    if high_pass_enabled and high_pass_filter_passes < 1:
        raise ValueError("High-pass broj prolaza mora biti najmanje 1.")

    if low_pass_enabled and low_pass_filter_passes < 1:
        raise ValueError("Low-pass broj prolaza mora biti najmanje 1.")

    if peak_detection_enabled and peak_min_distance_seconds <= 0:
        raise ValueError("Minimalno rastojanje izmedju vrhova mora biti vece od 0.")


def apply_config(sender=None, app_data=None, user_data=None):
    on_apply = state["on_apply"]

    if on_apply is None:
        return

    try:
        startup_trim_seconds = read_float(STARTUP_TRIM_INPUT_TAG)
        invert_processed_signal = bool(dpg.get_value(INVERT_PROCESSED_SIGNAL_INPUT_TAG))
        channel_subtraction = normalize_channel_subtraction(
            dpg.get_value(CHANNEL_SUBTRACTION_INPUT_TAG)
        )

        dc_removal_enabled = bool(dpg.get_value(DC_REMOVAL_ENABLED_INPUT_TAG))
        dc_removal_window_type = normalize_dc_removal_window_type(
            dpg.get_value(DC_REMOVAL_WINDOW_TYPE_INPUT_TAG)
        )
        dc_removal_window_seconds = read_float(DC_REMOVAL_WINDOW_SECONDS_INPUT_TAG)

        high_pass_enabled = bool(dpg.get_value(HIGH_PASS_FILTER_ENABLED_INPUT_TAG))
        high_pass_cutoff_hz = read_float(HIGH_PASS_CUTOFF_HZ_INPUT_TAG)

        low_pass_enabled = bool(dpg.get_value(LOW_PASS_FILTER_ENABLED_INPUT_TAG))
        low_pass_cutoff_hz = read_float(LOW_PASS_CUTOFF_HZ_INPUT_TAG)

        high_pass_filter_passes = read_int(HIGH_PASS_FILTER_PASSES_INPUT_TAG)
        low_pass_filter_passes = read_int(LOW_PASS_FILTER_PASSES_INPUT_TAG)

        peak_detection_enabled = bool(dpg.get_value(PEAK_DETECTION_ENABLED_INPUT_TAG))
        peak_min_distance_seconds = read_float(PEAK_MIN_DISTANCE_SECONDS_INPUT_TAG)
        peak_min_height = read_float(PEAK_MIN_HEIGHT_INPUT_TAG)

        validate_config_values(
            startup_trim_seconds,
            dc_removal_enabled,
            dc_removal_window_seconds,
            high_pass_enabled,
            high_pass_cutoff_hz,
            low_pass_enabled,
            low_pass_cutoff_hz,
            high_pass_filter_passes,
            low_pass_filter_passes,
            peak_detection_enabled,
            peak_min_distance_seconds,
        )

        on_apply(
            startup_trim_seconds,
            channel_subtraction,
            dc_removal_enabled,
            dc_removal_window_type,
            dc_removal_window_seconds,
            invert_processed_signal,
            high_pass_enabled,
            high_pass_cutoff_hz,
            low_pass_enabled,
            low_pass_cutoff_hz,
            high_pass_filter_passes,
            low_pass_filter_passes,
            peak_detection_enabled,
            peak_min_distance_seconds,
            peak_min_height,
        )

        dpg.configure_item(CONFIG_WINDOW_TAG, show=False)

    except Exception as error:
        dpg.set_value(CONFIG_FORM_STATUS_TAG, str(error))


def close_config_form(sender=None, app_data=None, user_data=None):
    dpg.configure_item(CONFIG_WINDOW_TAG, show=False)


def center_config_window():
    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()
    window_x = max(0, (viewport_width - CONFIG_WINDOW_WIDTH) // 2)
    window_y = max(0, (viewport_height - CONFIG_WINDOW_HEIGHT) // 2)
    dpg.set_item_pos(CONFIG_WINDOW_TAG, [window_x, window_y])


def add_float_row(label, tag, minimum, number_format):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_input_float(
            tag=tag,
            min_value=minimum,
            min_clamped=True,
            format=number_format,
            width=-1,
        )


def add_int_row(label, tag, minimum):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_input_int(
            tag=tag,
            min_value=minimum,
            min_clamped=True,
            width=-1,
        )


def add_checkbox_row(label, tag, callback=None):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_checkbox(tag=tag, callback=callback)


def add_combo_row(label, items, tag):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_combo(
            list(items),
            tag=tag,
            default_value=items[0],
            width=-1,
        )


def add_channel_subtraction_table():
    with dpg.table(
        header_row=False,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=CONFIG_INPUT_WIDTH)

        add_combo_row(
            "Oduzimanje kanala",
            CHANNEL_SUBTRACTION_OPTIONS,
            CHANNEL_SUBTRACTION_INPUT_TAG,
        )


def add_config_table():
    with dpg.table(
        header_row=False,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=CONFIG_INPUT_WIDTH)

        add_float_row(
            "Uklanjanje pocetka [s]",
            STARTUP_TRIM_INPUT_TAG,
            0.0,
            "%.2f",
        )

        add_checkbox_row(
            "Invertuj signal",
            INVERT_PROCESSED_SIGNAL_INPUT_TAG,
        )


def add_dc_removal_table():
    with dpg.table(
        header_row=False,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=CONFIG_INPUT_WIDTH)

        add_checkbox_row(
            "Ukloni DC komponentu",
            DC_REMOVAL_ENABLED_INPUT_TAG,
            update_dc_removal_inputs,
        )

        add_combo_row(
            "Tip prozora",
            DC_REMOVAL_WINDOW_TYPE_OPTIONS,
            DC_REMOVAL_WINDOW_TYPE_INPUT_TAG,
        )

        add_float_row(
            "Trajanje prozora [s]",
            DC_REMOVAL_WINDOW_SECONDS_INPUT_TAG,
            0.01,
            "%.2f",
        )


def add_filter_table():
    with dpg.table(
        header_row=False,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=CONFIG_INPUT_WIDTH)

        add_checkbox_row(
            "Visokopropusni filter",
            HIGH_PASS_FILTER_ENABLED_INPUT_TAG,
            update_filter_inputs,
        )

        add_float_row(
            "High-pass granica [Hz]",
            HIGH_PASS_CUTOFF_HZ_INPUT_TAG,
            0.01,
            "%.2f",
        )

        add_int_row(
            "High-pass broj prolaza",
            HIGH_PASS_FILTER_PASSES_INPUT_TAG,
            1,
        )

        add_checkbox_row(
            "Niskopropusni filter",
            LOW_PASS_FILTER_ENABLED_INPUT_TAG,
            update_filter_inputs,
        )

        add_float_row(
            "Low-pass granica [Hz]",
            LOW_PASS_CUTOFF_HZ_INPUT_TAG,
            0.01,
            "%.2f",
        )

        add_int_row(
            "Low-pass broj prolaza",
            LOW_PASS_FILTER_PASSES_INPUT_TAG,
            1,
        )


def add_peak_detection_table():
    with dpg.table(
        header_row=False,
        borders_innerH=False,
        borders_innerV=False,
        borders_outerH=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(width_stretch=True)
        dpg.add_table_column(width_fixed=True, init_width_or_weight=CONFIG_INPUT_WIDTH)

        add_checkbox_row(
            "Detektuj vrhove",
            PEAK_DETECTION_ENABLED_INPUT_TAG,
            update_peak_detection_inputs,
        )

        add_float_row(
            "Minimalno rastojanje [s]",
            PEAK_MIN_DISTANCE_SECONDS_INPUT_TAG,
            0.01,
            "%.2f",
        )

        add_float_row(
            "Minimalna visina",
            PEAK_MIN_HEIGHT_INPUT_TAG,
            -1000000.0,
            "%.0f",
        )


def create(on_apply):
    state["on_apply"] = on_apply

    with dpg.window(
        label="Izmjena realtime konfiguracije",
        tag=CONFIG_WINDOW_TAG,
        width=CONFIG_WINDOW_WIDTH,
        height=CONFIG_WINDOW_HEIGHT,
        modal=True,
        show=False,
        no_resize=True,
        no_collapse=True,
    ):
        dpg.add_text("", tag=CONFIG_NAME_TAG)
        dpg.add_spacer(height=6)

        with dpg.collapsing_header(label="Opsta podesavanja", default_open=True):
            add_config_table()

        dpg.add_spacer(height=6)

        with dpg.collapsing_header(label="Kombinovanje kanala", default_open=True):
            add_channel_subtraction_table()

        dpg.add_spacer(height=6)

        with dpg.collapsing_header(label="Uklanjanje DC komponente", default_open=True):
            add_dc_removal_table()

        dpg.add_spacer(height=6)

        with dpg.collapsing_header(label="Filtriranje signala", default_open=True):
            add_filter_table()

        dpg.add_spacer(height=6)

        with dpg.collapsing_header(label="Detekcija vrhova", default_open=True):
            add_peak_detection_table()

        dpg.add_spacer(height=8)
        dpg.add_text("", tag=CONFIG_FORM_STATUS_TAG, color=(239, 68, 68, 255), wrap=400)
        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Primijeni", width=100, callback=apply_config)
            dpg.add_button(label="Odustani", width=100, callback=close_config_form)


def open_config_form(config_name, config):
    state["config_name"] = config_name

    dpg.set_value(CONFIG_NAME_TAG, f"Konfiguracija: {config_name}")
    dpg.set_value(
        STARTUP_TRIM_INPUT_TAG,
        float(getattr(config, "STARTUP_TRIM_SECONDS", 0.0)),
    )
    dpg.set_value(
        INVERT_PROCESSED_SIGNAL_INPUT_TAG,
        bool(getattr(config, "INVERT_PROCESSED_SIGNAL", False)),
    )
    dpg.configure_item(
        CHANNEL_SUBTRACTION_INPUT_TAG,
        items=list(CHANNEL_SUBTRACTION_OPTIONS),
    )
    dpg.set_value(
        CHANNEL_SUBTRACTION_INPUT_TAG,
        normalize_channel_subtraction(
            getattr(config, "CHANNEL_SUBTRACTION", "none")
        ),
    )
    dpg.set_value(
        DC_REMOVAL_ENABLED_INPUT_TAG,
        bool(getattr(config, "DC_REMOVAL_ENABLED", False)),
    )
    dpg.configure_item(
        DC_REMOVAL_WINDOW_TYPE_INPUT_TAG,
        items=list(DC_REMOVAL_WINDOW_TYPE_OPTIONS),
    )
    dpg.set_value(
        DC_REMOVAL_WINDOW_TYPE_INPUT_TAG,
        normalize_dc_removal_window_type(
            getattr(config, "DC_REMOVAL_WINDOW_TYPE", "causal")
        ),
    )
    dpg.set_value(
        DC_REMOVAL_WINDOW_SECONDS_INPUT_TAG,
        float(getattr(config, "DC_REMOVAL_WINDOW_SECONDS", 2.0)),
    )
    dpg.set_value(CONFIG_FORM_STATUS_TAG, "")

    update_dc_removal_inputs()

    dpg.set_value(
        HIGH_PASS_FILTER_ENABLED_INPUT_TAG,
        bool(getattr(config, "HIGH_PASS_FILTER_ENABLED", False)),
    )
    dpg.set_value(
        HIGH_PASS_CUTOFF_HZ_INPUT_TAG,
        float(getattr(config, "HIGH_PASS_CUTOFF_HZ", 0.5)),
    )
    dpg.set_value(
        LOW_PASS_FILTER_ENABLED_INPUT_TAG,
        bool(getattr(config, "LOW_PASS_FILTER_ENABLED", False)),
    )
    dpg.set_value(
        LOW_PASS_CUTOFF_HZ_INPUT_TAG,
        float(getattr(config, "LOW_PASS_CUTOFF_HZ", 5.0)),
    )
    dpg.set_value(
        HIGH_PASS_FILTER_PASSES_INPUT_TAG,
        int(getattr(config, "HIGH_PASS_FILTER_PASSES", 1)),
    )
    dpg.set_value(
        LOW_PASS_FILTER_PASSES_INPUT_TAG,
        int(getattr(config, "LOW_PASS_FILTER_PASSES", 1)),
    )

    update_filter_inputs()

    dpg.set_value(
        PEAK_DETECTION_ENABLED_INPUT_TAG,
        bool(getattr(config, "PEAK_DETECTION_ENABLED", False)),
    )
    dpg.set_value(
        PEAK_MIN_DISTANCE_SECONDS_INPUT_TAG,
        float(getattr(config, "PEAK_MIN_DISTANCE_SECONDS", 0.4)),
    )
    dpg.set_value(
        PEAK_MIN_HEIGHT_INPUT_TAG,
        float(getattr(config, "PEAK_MIN_HEIGHT", 0.0)),
    )

    update_peak_detection_inputs()

    dpg.configure_item(CONFIG_WINDOW_TAG, show=True)
    center_config_window()
    dpg.focus_item(CONFIG_WINDOW_TAG)