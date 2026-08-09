# Removes the unstable part from the start of the signal.
def trim_signal_start(
    x_values,
    signal_values,
    startup_trim_seconds,
):
    start_index = next(
        (
            index
            for index, x_value in enumerate(x_values)
            if x_value >= startup_trim_seconds
        ),
        len(x_values),
    )

    return (
        x_values[start_index:],
        signal_values[start_index:],
    )


# Applies all processing steps to the Green signal.
def process_green_signal(
    x_values,
    signals,
    config,
):
    processed_x_values = list(x_values)
    processed_green = list(signals.get("green", []))

    processed_x_values, processed_green = trim_signal_start(
        processed_x_values,
        processed_green,
        config.STARTUP_TRIM_SECONDS,
    )

    return (
        processed_x_values,
        processed_green,
    )