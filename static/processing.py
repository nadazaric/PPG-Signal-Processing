# Removes the unstable part from the start of the signal.
def trim_signal_start(
    x_values,
    signals,
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

    trimmed_signals = {
        signal_name: signal_values[start_index:]
        for signal_name, signal_values in signals.items()
    }

    return (
        x_values[start_index:],
        trimmed_signals,
    )


# Subtracts the selected channel or channel combination from Green.
def subtract_channels(
    signals,
    subtraction_mode,
):
    green = signals["green"]
    red = signals["red"]
    infrared = signals["infrared"]

    if subtraction_mode == "none":
        return list(green)

    if subtraction_mode == "red":
        return [
            green_value - red_value
            for green_value, red_value in zip(
                green,
                red,
            )
        ]

    if subtraction_mode == "infrared":
        return [
            green_value - infrared_value
            for green_value, infrared_value in zip(
                green,
                infrared,
            )
        ]

    if subtraction_mode == "red_infrared_mean":
        return [
            green_value - ((red_value + infrared_value) / 2.0)
            for green_value, red_value, infrared_value in zip(
                green,
                red,
                infrared,
            )
        ]

    raise ValueError(
        f"Unsupported channel subtraction mode: {subtraction_mode}"
    )


# Centers the signal around zero by removing its mean value.
def center_signal(signal_values):
    if not signal_values:
        return []

    mean_value = sum(signal_values) / len(signal_values)

    return [
        value - mean_value
        for value in signal_values
    ]


# Applies all configured processing steps to the Green signal.
def process_green_signal(
    x_values,
    signals,
    config,
):
    processed_x_values = list(x_values)

    processed_signals = {
        "green": list(signals["green"]),
        "red": list(signals["red"]),
        "infrared": list(signals["infrared"]),
    }

    processed_x_values, processed_signals = trim_signal_start(
        processed_x_values,
        processed_signals,
        config.STARTUP_TRIM_SECONDS,
    )

    processed_green = subtract_channels(
        processed_signals,
        config.CHANNEL_SUBTRACTION,
    )

    processed_green = center_signal(
        processed_green,
    )

    return (
        processed_x_values,
        processed_green,
    )