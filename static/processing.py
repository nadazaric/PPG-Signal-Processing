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

# Applies a centered FIR filter using the provided coefficients.
def apply_fir_filter(
    signal_values,
    filter_coefficients,
):
    if not signal_values:
        return []

    coefficient_count = len(filter_coefficients)

    if coefficient_count == 0:
        raise ValueError("Filter must contain at least one coefficient.")

    if coefficient_count % 2 == 0:
        raise ValueError("A centered FIR filter must contain an odd number of coefficients.")

    half_window_size = (coefficient_count // 2)

    if len(signal_values) <= half_window_size:
        raise ValueError("The signal is too short for the selected FIR filter.")

    left_extension = list(
        reversed(
            signal_values[
                1:half_window_size + 1
            ]
        )
    )

    right_extension = list(
        reversed(
            signal_values[
                -half_window_size - 1:-1
            ]
        )
    )

    extended_signal = (left_extension + list(signal_values) + right_extension)

    filtered_signal = []

    for center_index in range(len(signal_values)):
        filtered_value = 0.0

        for coefficient_index in range(coefficient_count):
            signal_value = extended_signal[center_index + coefficient_index]
            coefficient = filter_coefficients[coefficient_index]
            filtered_value += (coefficient * signal_value)

        filtered_signal.append(filtered_value)

    return filtered_signal


from scipy.signal import firwin


# Designs FIR filter coefficients using the window method.
def design_fir_filter(
    sampling_frequency,
    cutoff_frequencies,
    coefficient_count,
    filter_type,
    window_type="hamming",
):
    if sampling_frequency <= 0:
        raise ValueError("Sampling frequency must be greater than zero.")

    if coefficient_count <= 0:
        raise ValueError("Coefficient count must be greater than zero.")

    if coefficient_count % 2 == 0:
        raise ValueError("Coefficient count must be odd.")

    supported_filter_types = {
        "lowpass",
        "highpass",
        "bandpass",
        "bandstop",
    }

    if filter_type not in supported_filter_types:
        raise ValueError(f"Unsupported filter type: {filter_type}.")

    filter_coefficients = firwin(
        numtaps=coefficient_count,
        cutoff=cutoff_frequencies,
        window=window_type,
        pass_zero=filter_type,
        fs=sampling_frequency,
    )

    return filter_coefficients.tolist()

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

    processed_green = center_signal(processed_green)

    filter_type = config.FILTER_TYPE

    if filter_type != "none":
        if filter_type == "highpass":
            cutoff_frequencies = config.LOWER_CUTOFF_FREQUENCY_HZ
        elif filter_type == "lowpass":
            cutoff_frequencies = config.UPPER_CUTOFF_FREQUENCY_HZ
        elif filter_type == "bandpass":
            cutoff_frequencies = (
                config.LOWER_CUTOFF_FREQUENCY_HZ,
                config.UPPER_CUTOFF_FREQUENCY_HZ,
            )
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}.")

        filter_coefficients = design_fir_filter(
            sampling_frequency=(config.SAMPLING_FREQUENCY_HZ),
            cutoff_frequencies=(cutoff_frequencies),
            coefficient_count=(config.FILTER_COEFFICIENT_COUNT),
            filter_type=(filter_type),
            window_type=(config.FILTER_WINDOW_TYPE),
        )

        processed_green = apply_fir_filter(
            signal_values=processed_green,
            filter_coefficients=(filter_coefficients),
        )

    return (processed_x_values, processed_green)