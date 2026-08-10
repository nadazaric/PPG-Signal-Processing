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
CONFIG_FORM_STATUS_TAG = "static_config_form_status"


CONFIG_WINDOW_WIDTH = 520
CONFIG_WINDOW_HEIGHT = 520
CONFIG_INPUT_WIDTH = 220


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


def update_filter_inputs(
    sender=None,
    app_data=None,
    user_data=None,
):
    filter_type = dpg.get_value(
        FILTER_TYPE_INPUT_TAG
    )

    filter_enabled = (
        filter_type != "none"
    )

    lower_cutoff_enabled = (
        filter_type
        in (
            "highpass",
            "bandpass",
        )
    )

    upper_cutoff_enabled = (
        filter_type
        in (
            "lowpass",
            "bandpass",
        )
    )

    dpg.configure_item(
        LOWER_CUTOFF_FREQUENCY_INPUT_TAG,
        enabled=lower_cutoff_enabled,
    )

    dpg.configure_item(
        UPPER_CUTOFF_FREQUENCY_INPUT_TAG,
        enabled=upper_cutoff_enabled,
    )

    dpg.configure_item(
        FILTER_COEFFICIENT_COUNT_INPUT_TAG,
        enabled=filter_enabled,
    )

    dpg.configure_item(
        FILTER_WINDOW_TYPE_INPUT_TAG,
        enabled=filter_enabled,
    )


def apply_config(
    sender=None,
    app_data=None,
    user_data=None,
):
    on_apply = state["on_apply"]

    if on_apply is None:
        return

    try:
        startup_trim_seconds = float(
            dpg.get_value(
                STARTUP_TRIM_INPUT_TAG
            )
        )

        channel_subtraction = dpg.get_value(
            CHANNEL_SUBTRACTION_INPUT_TAG
        )

        filter_type = dpg.get_value(
            FILTER_TYPE_INPUT_TAG
        )

        sampling_frequency = float(
            dpg.get_value(
                SAMPLING_FREQUENCY_INPUT_TAG
            )
        )

        lower_cutoff_frequency = float(
            dpg.get_value(
                LOWER_CUTOFF_FREQUENCY_INPUT_TAG
            )
        )

        upper_cutoff_frequency = float(
            dpg.get_value(
                UPPER_CUTOFF_FREQUENCY_INPUT_TAG
            )
        )

        filter_coefficient_count = int(
            dpg.get_value(
                FILTER_COEFFICIENT_COUNT_INPUT_TAG
            )
        )

        filter_window_type = dpg.get_value(
            FILTER_WINDOW_TYPE_INPUT_TAG
        )

        if startup_trim_seconds < 0:
            raise ValueError(
                "Vrijeme uklanjanja početka "
                "ne može biti negativno."
            )

        if (
            channel_subtraction
            not in CHANNEL_SUBTRACTION_OPTIONS
        ):
            raise ValueError(
                "Izabran je nepodržan način "
                "oduzimanja kanala."
            )

        if (
            filter_type
            not in FILTER_TYPE_OPTIONS
        ):
            raise ValueError(
                "Izabran je nepodržan tip filtera."
            )

        if sampling_frequency <= 0:
            raise ValueError(
                "Frekvencija uzorkovanja "
                "mora biti veća od nule."
            )

        nyquist_frequency = (
            sampling_frequency
            / 2.0
        )

        if (
            filter_type
            in (
                "highpass",
                "bandpass",
            )
        ):
            if lower_cutoff_frequency <= 0:
                raise ValueError(
                    "Donja granična frekvencija "
                    "mora biti veća od nule."
                )

            if (
                lower_cutoff_frequency
                >= nyquist_frequency
            ):
                raise ValueError(
                    "Donja granična frekvencija "
                    "mora biti manja od polovine "
                    "frekvencije uzorkovanja."
                )

        if (
            filter_type
            in (
                "lowpass",
                "bandpass",
            )
        ):
            if upper_cutoff_frequency <= 0:
                raise ValueError(
                    "Gornja granična frekvencija "
                    "mora biti veća od nule."
                )

            if (
                upper_cutoff_frequency
                >= nyquist_frequency
            ):
                raise ValueError(
                    "Gornja granična frekvencija "
                    "mora biti manja od polovine "
                    "frekvencije uzorkovanja."
                )

        if (
            filter_type == "bandpass"
            and lower_cutoff_frequency
            >= upper_cutoff_frequency
        ):
            raise ValueError(
                "Donja granična frekvencija mora "
                "biti manja od gornje granične "
                "frekvencije."
            )

        if filter_type != "none":
            if filter_coefficient_count <= 0:
                raise ValueError(
                    "Broj koeficijenata mora biti "
                    "veći od nule."
                )

            if (
                filter_coefficient_count
                % 2 == 0
            ):
                raise ValueError(
                    "Broj koeficijenata mora biti "
                    "neparan."
                )

            if (
                filter_window_type
                not in FILTER_WINDOW_OPTIONS
            ):
                raise ValueError(
                    "Izabran je nepodržan tip prozora."
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
        )

        dpg.configure_item(
            CONFIG_WINDOW_TAG,
            show=False,
        )

    except Exception as error:
        dpg.set_value(
            CONFIG_FORM_STATUS_TAG,
            str(error),
        )


def close_config_form(
    sender=None,
    app_data=None,
    user_data=None,
):
    dpg.configure_item(
        CONFIG_WINDOW_TAG,
        show=False,
    )


def center_config_window():
    viewport_width = (
        dpg.get_viewport_client_width()
    )

    viewport_height = (
        dpg.get_viewport_client_height()
    )

    window_x = max(
        0,
        (
            viewport_width
            - CONFIG_WINDOW_WIDTH
        )
        // 2,
    )

    window_y = max(
        0,
        (
            viewport_height
            - CONFIG_WINDOW_HEIGHT
        )
        // 2,
    )

    dpg.set_item_pos(
        CONFIG_WINDOW_TAG,
        [
            window_x,
            window_y,
        ],
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
        dpg.add_text(
            "",
            tag=CONFIG_NAME_TAG,
        )

        dpg.add_spacer(
            height=8,
        )

        with dpg.table(
            header_row=False,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
            policy=dpg.mvTable_SizingStretchProp,
        ):
            dpg.add_table_column(
                width_stretch=True,
            )

            dpg.add_table_column(
                width_fixed=True,
                init_width_or_weight=(
                    CONFIG_INPUT_WIDTH
                ),
            )

            with dpg.table_row():
                dpg.add_text(
                    "Uklanjanje početka [s]"
                )

                dpg.add_input_float(
                    tag=STARTUP_TRIM_INPUT_TAG,
                    min_value=0.0,
                    min_clamped=True,
                    format="%.2f",
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Oduzimanje kanala"
                )

                dpg.add_combo(
                    CHANNEL_SUBTRACTION_OPTIONS,
                    tag=CHANNEL_SUBTRACTION_INPUT_TAG,
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Tip filtera"
                )

                dpg.add_combo(
                    FILTER_TYPE_OPTIONS,
                    tag=FILTER_TYPE_INPUT_TAG,
                    width=-1,
                    callback=update_filter_inputs,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Frekvencija uzorkovanja [Hz]"
                )

                dpg.add_input_float(
                    tag=SAMPLING_FREQUENCY_INPUT_TAG,
                    min_value=0.01,
                    min_clamped=True,
                    format="%.2f",
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Donja granična frekvencija [Hz]"
                )

                dpg.add_input_float(
                    tag=LOWER_CUTOFF_FREQUENCY_INPUT_TAG,
                    min_value=0.01,
                    min_clamped=True,
                    format="%.2f",
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Gornja granična frekvencija [Hz]"
                )

                dpg.add_input_float(
                    tag=UPPER_CUTOFF_FREQUENCY_INPUT_TAG,
                    min_value=0.01,
                    min_clamped=True,
                    format="%.2f",
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Broj koeficijenata"
                )

                dpg.add_input_int(
                    tag=FILTER_COEFFICIENT_COUNT_INPUT_TAG,
                    min_value=1,
                    min_clamped=True,
                    width=-1,
                )

            with dpg.table_row():
                dpg.add_text(
                    "Tip prozora"
                )

                dpg.add_combo(
                    FILTER_WINDOW_OPTIONS,
                    tag=FILTER_WINDOW_TYPE_INPUT_TAG,
                    width=-1,
                )

        dpg.add_spacer(
            height=8,
        )

        dpg.add_text(
            "",
            tag=CONFIG_FORM_STATUS_TAG,
            color=(239, 68, 68, 255),
            wrap=480,
        )

        dpg.add_spacer(
            height=8,
        )

        with dpg.group(
            horizontal=True,
        ):
            dpg.add_button(
                label="Primijeni",
                width=100,
                callback=apply_config,
            )

            dpg.add_button(
                label="Odustani",
                width=100,
                callback=close_config_form,
            )


def open_config_form(
    config_name,
    config,
):
    state["config_name"] = config_name

    dpg.set_value(
        CONFIG_NAME_TAG,
        f"Konfiguracija: {config_name}",
    )

    dpg.set_value(
        STARTUP_TRIM_INPUT_TAG,
        float(
            config.STARTUP_TRIM_SECONDS
        ),
    )

    dpg.set_value(
        CHANNEL_SUBTRACTION_INPUT_TAG,
        config.CHANNEL_SUBTRACTION,
    )

    dpg.set_value(
        FILTER_TYPE_INPUT_TAG,
        config.FILTER_TYPE,
    )

    dpg.set_value(
        SAMPLING_FREQUENCY_INPUT_TAG,
        float(
            config.SAMPLING_FREQUENCY_HZ
        ),
    )

    dpg.set_value(
        LOWER_CUTOFF_FREQUENCY_INPUT_TAG,
        float(
            config.LOWER_CUTOFF_FREQUENCY_HZ
        ),
    )

    dpg.set_value(
        UPPER_CUTOFF_FREQUENCY_INPUT_TAG,
        float(
            config.UPPER_CUTOFF_FREQUENCY_HZ
        ),
    )

    dpg.set_value(
        FILTER_COEFFICIENT_COUNT_INPUT_TAG,
        int(
            config.FILTER_COEFFICIENT_COUNT
        ),
    )

    dpg.set_value(
        FILTER_WINDOW_TYPE_INPUT_TAG,
        config.FILTER_WINDOW_TYPE,
    )

    update_filter_inputs()

    dpg.set_value(
        CONFIG_FORM_STATUS_TAG,
        "",
    )

    dpg.configure_item(
        CONFIG_WINDOW_TAG,
        show=True,
    )

    center_config_window()

    dpg.focus_item(
        CONFIG_WINDOW_TAG,
    )