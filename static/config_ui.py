import dearpygui.dearpygui as dpg


CONFIG_WINDOW_TAG = "static_config_window"
CONFIG_NAME_TAG = "static_config_name"

STARTUP_TRIM_INPUT_TAG = "static_config_startup_trim"
CHANNEL_SUBTRACTION_INPUT_TAG = "static_config_channel_subtraction"
FILTER_TYPE_INPUT_TAG = "static_config_filter_type"
SAMPLING_FREQUENCY_INPUT_TAG = "static_config_sampling_frequency"
LOWER_CUTOFF_FREQUENCY_INPUT_TAG = "static_config_lower_cutoff_frequency"
UPPER_CUTOFF_FREQUENCY_INPUT_TAG = "static_config_upper_cutoff_frequency"
FILTER_COEFFICIENT_COUNT_INPUT_TAG = "static_config_filter_coefficient_count"
FILTER_WINDOW_TYPE_INPUT_TAG = "static_config_filter_window_type"

ARTIFACT_DETECTION_ENABLED_INPUT_TAG = "static_config_artifact_detection_enabled"
SHOW_ARTIFACTS_ON_PLOT_INPUT_TAG = "static_config_show_artifacts_on_plot"
ARTIFACT_JUMP_THRESHOLD_FACTOR_INPUT_TAG = "static_config_artifact_jump_threshold_factor"
ARTIFACT_PADDING_SECONDS_INPUT_TAG = "static_config_artifact_padding_seconds"

RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG = "static_config_range_artifact_detection_enabled"
ARTIFACT_RANGE_WINDOW_SECONDS_INPUT_TAG = "static_config_artifact_range_window_seconds"
ARTIFACT_RANGE_THRESHOLD_FACTOR_INPUT_TAG = "static_config_artifact_range_threshold_factor"

CONFIG_FORM_STATUS_TAG = "static_config_form_status"

CONFIG_WINDOW_WIDTH = 500
CONFIG_WINDOW_HEIGHT = 520
CONFIG_INPUT_WIDTH = 210

CHANNEL_SUBTRACTION_OPTIONS = (
    "none",
    "red",
    "infrared",
    "red_infrared_mean",
)

FILTER_TYPE_OPTIONS = (
    "highpass",
    "lowpass",
    "bandpass",
    "none",
)

FILTER_WINDOW_OPTIONS = (
    "hamming",
    "hann",
    "blackman",
)

state = {
    "config_name": None,
    "on_apply": None,
}


def update_filter_inputs(sender=None, app_data=None, user_data=None):
    filter_type = dpg.get_value(FILTER_TYPE_INPUT_TAG)
    filter_enabled = filter_type != "none"
    lower_cutoff_enabled = filter_type in ("highpass", "bandpass")
    upper_cutoff_enabled = filter_type in ("lowpass", "bandpass")

    dpg.configure_item(LOWER_CUTOFF_FREQUENCY_INPUT_TAG, enabled=lower_cutoff_enabled)
    dpg.configure_item(UPPER_CUTOFF_FREQUENCY_INPUT_TAG, enabled=upper_cutoff_enabled)
    dpg.configure_item(FILTER_COEFFICIENT_COUNT_INPUT_TAG, enabled=filter_enabled)
    dpg.configure_item(FILTER_WINDOW_TYPE_INPUT_TAG, enabled=filter_enabled)


def update_artifact_inputs(sender=None, app_data=None, user_data=None):
    artifact_detection_enabled = bool(dpg.get_value(ARTIFACT_DETECTION_ENABLED_INPUT_TAG))
    range_detection_enabled = bool(dpg.get_value(RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG))
    range_inputs_enabled = artifact_detection_enabled and range_detection_enabled

    dpg.configure_item(SHOW_ARTIFACTS_ON_PLOT_INPUT_TAG, enabled=artifact_detection_enabled)
    dpg.configure_item(ARTIFACT_JUMP_THRESHOLD_FACTOR_INPUT_TAG, enabled=artifact_detection_enabled)
    dpg.configure_item(ARTIFACT_PADDING_SECONDS_INPUT_TAG, enabled=artifact_detection_enabled)
    dpg.configure_item(RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG, enabled=artifact_detection_enabled)
    dpg.configure_item(ARTIFACT_RANGE_WINDOW_SECONDS_INPUT_TAG, enabled=range_inputs_enabled)
    dpg.configure_item(ARTIFACT_RANGE_THRESHOLD_FACTOR_INPUT_TAG, enabled=range_inputs_enabled)


def read_float(tag):
    return float(dpg.get_value(tag))


def read_int(tag):
    return int(dpg.get_value(tag))


def apply_config(sender=None, app_data=None, user_data=None):
    on_apply = state["on_apply"]

    if on_apply is None:
        return

    try:
        startup_trim_seconds = read_float(STARTUP_TRIM_INPUT_TAG)
        channel_subtraction = dpg.get_value(CHANNEL_SUBTRACTION_INPUT_TAG)
        filter_type = dpg.get_value(FILTER_TYPE_INPUT_TAG)
        sampling_frequency = read_float(SAMPLING_FREQUENCY_INPUT_TAG)
        lower_cutoff_frequency = read_float(LOWER_CUTOFF_FREQUENCY_INPUT_TAG)
        upper_cutoff_frequency = read_float(UPPER_CUTOFF_FREQUENCY_INPUT_TAG)
        filter_coefficient_count = read_int(FILTER_COEFFICIENT_COUNT_INPUT_TAG)
        filter_window_type = dpg.get_value(FILTER_WINDOW_TYPE_INPUT_TAG)
        artifact_detection_enabled = bool(dpg.get_value(ARTIFACT_DETECTION_ENABLED_INPUT_TAG))
        show_artifacts_on_plot = bool(dpg.get_value(SHOW_ARTIFACTS_ON_PLOT_INPUT_TAG))
        artifact_jump_threshold_factor = read_float(ARTIFACT_JUMP_THRESHOLD_FACTOR_INPUT_TAG)
        artifact_padding_seconds = read_float(ARTIFACT_PADDING_SECONDS_INPUT_TAG)
        range_artifact_detection_enabled = bool(dpg.get_value(RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG))
        artifact_range_window_seconds = read_float(ARTIFACT_RANGE_WINDOW_SECONDS_INPUT_TAG)
        artifact_range_threshold_factor = read_float(ARTIFACT_RANGE_THRESHOLD_FACTOR_INPUT_TAG)

        validate_config_values(
            startup_trim_seconds,
            channel_subtraction,
            filter_type,
            sampling_frequency,
            lower_cutoff_frequency,
            upper_cutoff_frequency,
            filter_coefficient_count,
            filter_window_type,
            artifact_jump_threshold_factor,
            artifact_padding_seconds,
            artifact_range_window_seconds,
            artifact_range_threshold_factor,
        )

        on_apply(
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
        )

        dpg.configure_item(CONFIG_WINDOW_TAG, show=False)

    except Exception as error:
        dpg.set_value(CONFIG_FORM_STATUS_TAG, str(error))


def validate_config_values(
    startup_trim_seconds,
    channel_subtraction,
    filter_type,
    sampling_frequency,
    lower_cutoff_frequency,
    upper_cutoff_frequency,
    filter_coefficient_count,
    filter_window_type,
    artifact_jump_threshold_factor,
    artifact_padding_seconds,
    artifact_range_window_seconds,
    artifact_range_threshold_factor,
):
    if startup_trim_seconds < 0:
        raise ValueError("Vrijeme uklanjanja pocetka ne moze biti negativno.")

    if channel_subtraction not in CHANNEL_SUBTRACTION_OPTIONS:
        raise ValueError("Izabran je nepodrzan nacin oduzimanja kanala.")

    if filter_type not in FILTER_TYPE_OPTIONS:
        raise ValueError("Izabran je nepodrzan tip filtera.")

    if sampling_frequency <= 0:
        raise ValueError("Frekvencija uzorkovanja mora biti veca od nule.")

    nyquist_frequency = sampling_frequency / 2.0

    if filter_type in ("highpass", "bandpass"):
        if lower_cutoff_frequency <= 0:
            raise ValueError("Donja granicna frekvencija mora biti veca od nule.")

        if lower_cutoff_frequency >= nyquist_frequency:
            raise ValueError("Donja granicna frekvencija mora biti manja od polovine frekvencije uzorkovanja.")

    if filter_type in ("lowpass", "bandpass"):
        if upper_cutoff_frequency <= 0:
            raise ValueError("Gornja granicna frekvencija mora biti veca od nule.")

        if upper_cutoff_frequency >= nyquist_frequency:
            raise ValueError("Gornja granicna frekvencija mora biti manja od polovine frekvencije uzorkovanja.")

    if filter_type == "bandpass" and lower_cutoff_frequency >= upper_cutoff_frequency:
        raise ValueError("Donja granicna frekvencija mora biti manja od gornje granicne frekvencije.")

    if filter_type != "none":
        if filter_coefficient_count <= 0:
            raise ValueError("Broj koeficijenata mora biti veci od nule.")

        if filter_coefficient_count % 2 == 0:
            raise ValueError("Broj koeficijenata mora biti neparan.")

        if filter_window_type not in FILTER_WINDOW_OPTIONS:
            raise ValueError("Izabran je nepodrzan tip prozora.")

    if artifact_jump_threshold_factor <= 0:
        raise ValueError("Faktor praga za skok mora biti veci od nule.")

    if artifact_padding_seconds < 0:
        raise ValueError("Vrijeme prosirenja artefakta ne moze biti negativno.")

    if artifact_range_window_seconds <= 0:
        raise ValueError("Prozor za range mora biti veci od nule.")

    if artifact_range_threshold_factor <= 0:
        raise ValueError("Faktor praga za range mora biti veci od nule.")


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
        dpg.add_input_int(tag=tag, min_value=minimum, min_clamped=True, width=-1)


def add_combo_row(label, items, tag, callback=None):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_combo(items, tag=tag, width=-1, callback=callback)


def add_checkbox_row(label, tag, callback=None):
    with dpg.table_row():
        dpg.add_text(label)
        dpg.add_checkbox(tag=tag, callback=callback)


def add_config_table(add_rows):
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
        add_rows()


def add_basic_settings():
    add_float_row(
        "Uklanjanje pocetka [s]",
        STARTUP_TRIM_INPUT_TAG,
        0.0,
        "%.2f",
    )

    add_combo_row(
        "Oduzimanje kanala",
        CHANNEL_SUBTRACTION_OPTIONS,
        CHANNEL_SUBTRACTION_INPUT_TAG,
    )

    add_float_row(
        "Frekvencija uzorkovanja [Hz]",
        SAMPLING_FREQUENCY_INPUT_TAG,
        0.01,
        "%.2f",
    )


def add_filter_settings():
    add_combo_row(
        "Tip filtera",
        FILTER_TYPE_OPTIONS,
        FILTER_TYPE_INPUT_TAG,
        update_filter_inputs,
    )

    add_float_row(
        "Donja granicna frekvencija [Hz]",
        LOWER_CUTOFF_FREQUENCY_INPUT_TAG,
        0.01,
        "%.2f",
    )

    add_float_row(
        "Gornja granicna frekvencija [Hz]",
        UPPER_CUTOFF_FREQUENCY_INPUT_TAG,
        0.01,
        "%.2f",
    )

    add_int_row("Broj koeficijenata", FILTER_COEFFICIENT_COUNT_INPUT_TAG, 1)

    add_combo_row("Tip prozora", FILTER_WINDOW_OPTIONS, FILTER_WINDOW_TYPE_INPUT_TAG)


def add_artifact_settings():
    add_checkbox_row(
        "Detekcija artefakata",
        ARTIFACT_DETECTION_ENABLED_INPUT_TAG,
        update_artifact_inputs,
    )

    add_checkbox_row("Prikaz artefakata na grafu", SHOW_ARTIFACTS_ON_PLOT_INPUT_TAG)

    add_float_row(
        "Faktor praga za skok",
        ARTIFACT_JUMP_THRESHOLD_FACTOR_INPUT_TAG,
        0.01,
        "%.2f",
    )

    add_float_row(
        "Prosirenje artefakta [s]",
        ARTIFACT_PADDING_SECONDS_INPUT_TAG,
        0.0,
        "%.2f",
    )

    add_checkbox_row(
        "Range detekcija artefakata",
        RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG,
        update_artifact_inputs,
    )

    add_float_row(
        "Prozor za range [s]",
        ARTIFACT_RANGE_WINDOW_SECONDS_INPUT_TAG,
        0.01,
        "%.2f",
    )

    add_float_row(
        "Faktor praga za range",
        ARTIFACT_RANGE_THRESHOLD_FACTOR_INPUT_TAG,
        0.01,
        "%.2f",
    )


def create(on_apply):
    state["on_apply"] = on_apply

    with dpg.window(
        label="Izmjena konfiguracije",
        tag=CONFIG_WINDOW_TAG,
        width=CONFIG_WINDOW_WIDTH,
        height=CONFIG_WINDOW_HEIGHT,
        modal=True,
        show=False,
        no_resize=True,
        no_collapse=True,
    ):
        dpg.add_text("", tag=CONFIG_NAME_TAG)
        dpg.add_spacer(height=4)

        with dpg.collapsing_header(label="Osnovna obrada", default_open=True):
            add_config_table(add_basic_settings)

        with dpg.collapsing_header(label="Filter", default_open=True):
            add_config_table(add_filter_settings)

        with dpg.collapsing_header(label="Artefakti", default_open=True):
            add_config_table(add_artifact_settings)

        dpg.add_spacer(height=8)
        dpg.add_text("", tag=CONFIG_FORM_STATUS_TAG, color=(239, 68, 68, 255), wrap=460)
        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Primijeni", width=100, callback=apply_config)
            dpg.add_button(label="Odustani", width=100, callback=close_config_form)


def open_config_form(config_name, config):
    state["config_name"] = config_name

    dpg.set_value(CONFIG_NAME_TAG, f"Konfiguracija: {config_name}")
    dpg.set_value(STARTUP_TRIM_INPUT_TAG, float(config.STARTUP_TRIM_SECONDS))
    dpg.set_value(CHANNEL_SUBTRACTION_INPUT_TAG, config.CHANNEL_SUBTRACTION)
    dpg.set_value(FILTER_TYPE_INPUT_TAG, config.FILTER_TYPE)
    dpg.set_value(SAMPLING_FREQUENCY_INPUT_TAG, float(config.SAMPLING_FREQUENCY_HZ))
    dpg.set_value(LOWER_CUTOFF_FREQUENCY_INPUT_TAG, float(config.LOWER_CUTOFF_FREQUENCY_HZ))
    dpg.set_value(UPPER_CUTOFF_FREQUENCY_INPUT_TAG, float(config.UPPER_CUTOFF_FREQUENCY_HZ))
    dpg.set_value(FILTER_COEFFICIENT_COUNT_INPUT_TAG, int(config.FILTER_COEFFICIENT_COUNT))
    dpg.set_value(FILTER_WINDOW_TYPE_INPUT_TAG, config.FILTER_WINDOW_TYPE)
    dpg.set_value(ARTIFACT_DETECTION_ENABLED_INPUT_TAG, bool(getattr(config, "ARTIFACT_DETECTION_ENABLED", False)))
    dpg.set_value(SHOW_ARTIFACTS_ON_PLOT_INPUT_TAG, bool(getattr(config, "SHOW_ARTIFACTS_ON_PLOT", False)))
    dpg.set_value(ARTIFACT_JUMP_THRESHOLD_FACTOR_INPUT_TAG, float(getattr(config, "ARTIFACT_JUMP_THRESHOLD_FACTOR", 8.0)))
    dpg.set_value(ARTIFACT_PADDING_SECONDS_INPUT_TAG, float(getattr(config, "ARTIFACT_PADDING_SECONDS", 0.5)))
    dpg.set_value(RANGE_ARTIFACT_DETECTION_ENABLED_INPUT_TAG, bool(getattr(config, "RANGE_ARTIFACT_DETECTION_ENABLED", False)))
    dpg.set_value(ARTIFACT_RANGE_WINDOW_SECONDS_INPUT_TAG, float(getattr(config, "ARTIFACT_RANGE_WINDOW_SECONDS", 0.5)))
    dpg.set_value(ARTIFACT_RANGE_THRESHOLD_FACTOR_INPUT_TAG, float(getattr(config, "ARTIFACT_RANGE_THRESHOLD_FACTOR", 6.0)))

    update_filter_inputs()
    update_artifact_inputs()

    dpg.set_value(CONFIG_FORM_STATUS_TAG, "")
    dpg.configure_item(CONFIG_WINDOW_TAG, show=True)
    center_config_window()
    dpg.focus_item(CONFIG_WINDOW_TAG)