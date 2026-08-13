def process_green_signal(x_values, signals, config):
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
    processed_green = list(signals.get("green", [])[start_index:])

    if getattr(config, "INVERT_PROCESSED_SIGNAL", False):
        processed_green = [-value for value in processed_green]

    data_size = min(len(processed_x_values), len(processed_green))

    return processed_x_values[:data_size], processed_green[:data_size]