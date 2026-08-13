import dearpygui.dearpygui as dpg


CONFIG_WINDOW_TAG = "realtime_config_window"
CONFIG_NAME_TAG = "realtime_config_name"
STARTUP_TRIM_INPUT_TAG = "realtime_config_startup_trim"
CONFIG_FORM_STATUS_TAG = "realtime_config_form_status"

CONFIG_WINDOW_WIDTH = 420
CONFIG_WINDOW_HEIGHT = 210
CONFIG_INPUT_WIDTH = 180

state = {
    "config_name": None,
    "on_apply": None,
}


def read_float(tag):
    return float(dpg.get_value(tag))


def validate_config_values(startup_trim_seconds):
    if startup_trim_seconds < 0:
        raise ValueError("Vrijeme uklanjanja pocetka ne moze biti negativno.")


def apply_config(sender=None, app_data=None, user_data=None):
    on_apply = state["on_apply"]

    if on_apply is None:
        return

    try:
        startup_trim_seconds = read_float(STARTUP_TRIM_INPUT_TAG)
        validate_config_values(startup_trim_seconds)
        on_apply(startup_trim_seconds)
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

        with dpg.collapsing_header(label="Opste", default_open=True):
            add_config_table()

        dpg.add_spacer(height=8)
        dpg.add_text("", tag=CONFIG_FORM_STATUS_TAG, color=(239, 68, 68, 255), wrap=380)
        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Primijeni", width=100, callback=apply_config)
            dpg.add_button(label="Odustani", width=100, callback=close_config_form)


def open_config_form(config_name, config):
    state["config_name"] = config_name

    dpg.set_value(CONFIG_NAME_TAG, f"Konfiguracija: {config_name}")
    dpg.set_value(STARTUP_TRIM_INPUT_TAG, float(config.STARTUP_TRIM_SECONDS))
    dpg.set_value(CONFIG_FORM_STATUS_TAG, "")
    dpg.configure_item(CONFIG_WINDOW_TAG, show=True)
    center_config_window()
    dpg.focus_item(CONFIG_WINDOW_TAG)