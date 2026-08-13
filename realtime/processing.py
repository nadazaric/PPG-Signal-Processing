import math


def limit_to_same_size(x_values, signal_values):
    data_size = min(len(x_values), len(signal_values))
    return list(x_values[:data_size]), list(signal_values[:data_size])


def subtract_causal_moving_average(x_values, signal_values, window_seconds):
    x_values, signal_values = limit_to_same_size(x_values, signal_values)

    if not x_values or not signal_values:
        return [], []

    result = []
    start = 0
    window_sum = 0.0

    for i, value in enumerate(signal_values):
        window_sum += value

        while start < i and x_values[i] - x_values[start] > window_seconds:
            window_sum -= signal_values[start]
            start += 1

        baseline = window_sum / (i - start + 1)
        result.append(value - baseline)

    return x_values, result


def subtract_centered_moving_average(x_values, signal_values, window_seconds):
    x_values, signal_values = limit_to_same_size(x_values, signal_values)

    if not x_values or not signal_values:
        return [], []

    result_x = []
    result_y = []
    half_window = window_seconds / 2.0
    last_time = x_values[-1]
    start = 0
    end = 0
    window_sum = 0.0

    for i, value in enumerate(signal_values):
        current_time = x_values[i]

        if last_time - current_time < half_window:
            break

        while start < i and current_time - x_values[start] > half_window:
            window_sum -= signal_values[start]
            start += 1

        while end < len(signal_values) and x_values[end] - current_time <= half_window:
            window_sum += signal_values[end]
            end += 1

        window_count = end - start

        if window_count <= 0:
            continue

        baseline = window_sum / window_count
        result_x.append(current_time)
        result_y.append(value - baseline)

    return result_x, result_y


def apply_high_pass_filter(x_values, signal_values, cutoff_hz):
    x_values, signal_values = limit_to_same_size(x_values, signal_values)

    if not x_values or not signal_values or cutoff_hz <= 0:
        return x_values, signal_values

    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    result = [0.0]
    previous_input = signal_values[0]
    previous_output = 0.0

    for i in range(1, len(signal_values)):
        dt = max(x_values[i] - x_values[i - 1], 0.000001)
        alpha = rc / (rc + dt)
        output = alpha * (previous_output + signal_values[i] - previous_input)

        result.append(output)
        previous_input = signal_values[i]
        previous_output = output

    return x_values, result


def apply_low_pass_filter(x_values, signal_values, cutoff_hz):
    x_values, signal_values = limit_to_same_size(x_values, signal_values)

    if not x_values or not signal_values or cutoff_hz <= 0:
        return x_values, signal_values

    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    result = [signal_values[0]]
    previous_output = signal_values[0]

    for i in range(1, len(signal_values)):
        dt = max(x_values[i] - x_values[i - 1], 0.000001)
        alpha = dt / (rc + dt)
        output = previous_output + alpha * (signal_values[i] - previous_output)

        result.append(output)
        previous_output = output

    return x_values, result


def apply_filter_repeatedly(filter_function, x_values, signal_values, cutoff_hz, filter_passes):
    filter_passes = max(1, int(filter_passes))

    for _ in range(filter_passes):
        x_values, signal_values = filter_function(
            x_values,
            signal_values,
            cutoff_hz,
        )

    return x_values, signal_values


def calculate_channel_subtraction_signal(signals, channel_subtraction):
    green_values = list(signals.get("green", []))

    if channel_subtraction == "red":
        red_values = list(signals.get("red", []))
        data_size = min(len(green_values), len(red_values))

        return [
            green_values[index] - red_values[index]
            for index in range(data_size)
        ]

    if channel_subtraction == "infrared":
        infrared_values = list(signals.get("infrared", []))
        data_size = min(len(green_values), len(infrared_values))

        return [
            green_values[index] - infrared_values[index]
            for index in range(data_size)
        ]

    if channel_subtraction == "red_infrared_mean":
        red_values = list(signals.get("red", []))
        infrared_values = list(signals.get("infrared", []))
        data_size = min(len(green_values), len(red_values), len(infrared_values))

        return [
            green_values[index] - ((red_values[index] + infrared_values[index]) / 2.0)
            for index in range(data_size)
        ]

    return green_values


def detect_peaks(x_values, signal_values, config):
    x_values, signal_values = limit_to_same_size(x_values, signal_values)

    if not getattr(config, "PEAK_DETECTION_ENABLED", False):
        return [], []

    if len(x_values) < 3 or len(signal_values) < 3:
        return [], []

    min_distance_seconds = getattr(config, "PEAK_MIN_DISTANCE_SECONDS", 0.4)
    min_height = getattr(config, "PEAK_MIN_HEIGHT", 0.0)

    peak_x_values = []
    peak_y_values = []

    for index in range(1, len(signal_values) - 1):
        previous_value = signal_values[index - 1]
        current_value = signal_values[index]
        next_value = signal_values[index + 1]

        is_local_peak = current_value > previous_value and current_value >= next_value

        if not is_local_peak or current_value < min_height:
            continue

        if not peak_x_values:
            peak_x_values.append(x_values[index])
            peak_y_values.append(current_value)
            continue

        distance_from_previous_peak = x_values[index] - peak_x_values[-1]

        if distance_from_previous_peak >= min_distance_seconds:
            peak_x_values.append(x_values[index])
            peak_y_values.append(current_value)
        elif current_value > peak_y_values[-1]:
            peak_x_values[-1] = x_values[index]
            peak_y_values[-1] = current_value

    return peak_x_values, peak_y_values


def process_green_signal(x_values, signals, config):
    green_values = list(signals.get("green", []))
    x_values, green_values = limit_to_same_size(x_values, green_values)

    if not x_values or not green_values:
        return [], []

    # TRIM START
    startup_trim_seconds = getattr(config, "STARTUP_TRIM_SECONDS", 0.0)
    start_index = next(
        (
            index
            for index, x_value in enumerate(x_values)
            if x_value >= startup_trim_seconds
        ),
        len(x_values),
    )

    processed_x_values = list(x_values[start_index:])
    processed_signals = {
        signal_name: list(signal_values[start_index:])
        for signal_name, signal_values in signals.items()
    }

    # CHANNEL SUBTRACTION
    channel_subtraction = getattr(config, "CHANNEL_SUBTRACTION", "none")
    processed_green = calculate_channel_subtraction_signal(
        processed_signals,
        channel_subtraction,
    )
    processed_x_values, processed_green = limit_to_same_size(
        processed_x_values,
        processed_green,
    )

    if not processed_x_values or not processed_green:
        return [], []

    # DC COMPONENT REMOVAL
    if getattr(config, "DC_REMOVAL_ENABLED", False):
        window_type = getattr(config, "DC_REMOVAL_WINDOW_TYPE", "causal")
        window_seconds = getattr(config, "DC_REMOVAL_WINDOW_SECONDS", 2.0)

        if window_type == "centered":
            processed_x_values, processed_green = subtract_centered_moving_average(
                processed_x_values,
                processed_green,
                window_seconds,
            )
        else:
            processed_x_values, processed_green = subtract_causal_moving_average(
                processed_x_values,
                processed_green,
                window_seconds,
            )

    # FILTERING
    if getattr(config, "HIGH_PASS_FILTER_ENABLED", False):
        processed_x_values, processed_green = apply_filter_repeatedly(
            apply_high_pass_filter,
            processed_x_values,
            processed_green,
            getattr(config, "HIGH_PASS_CUTOFF_HZ", 0.5),
            getattr(config, "HIGH_PASS_FILTER_PASSES", 1),
        )

    if getattr(config, "LOW_PASS_FILTER_ENABLED", False):
        processed_x_values, processed_green = apply_filter_repeatedly(
            apply_low_pass_filter,
            processed_x_values,
            processed_green,
            getattr(config, "LOW_PASS_CUTOFF_HZ", 5.0),
            getattr(config, "LOW_PASS_FILTER_PASSES", 1),
        )

    # INVERT PROCESSED SIGNAL
    if getattr(config, "INVERT_PROCESSED_SIGNAL", False):
        processed_green = [-value for value in processed_green]

    data_size = min(len(processed_x_values), len(processed_green))

    return processed_x_values[:data_size], processed_green[:data_size]