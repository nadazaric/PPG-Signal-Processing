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


def process_green_signal(x_values, signals, config):
    green_values = signals.get("green", [])
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
    processed_green = list(green_values[start_index:])

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

    # INVERT PROCESSED SIGNAL
    if getattr(config, "INVERT_PROCESSED_SIGNAL", False):
        processed_green = [-value for value in processed_green]

    data_size = min(len(processed_x_values), len(processed_green))

    return processed_x_values[:data_size], processed_green[:data_size]