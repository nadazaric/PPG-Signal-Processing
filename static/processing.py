import numpy as np
from numpy import median
from scipy.signal import firwin


# Removes the unstable part from the start of the signal.
def trim_signal_start(x_values, signals, startup_trim_seconds):
    start_index = next(
        (index for index, x_value in enumerate(x_values) if x_value >= startup_trim_seconds),
        len(x_values),
    )

    trimmed_signals = {
        signal_name: signal_values[start_index:]
        for signal_name, signal_values in signals.items()
    }

    return x_values[start_index:], trimmed_signals


# Subtracts the selected channel or channel combination from Green.
def subtract_channels(signals, subtraction_mode):
    green = signals["green"]
    red = signals["red"]
    infrared = signals["infrared"]

    if subtraction_mode == "none":
        return list(green)

    if subtraction_mode == "red":
        return [
            green_value - red_value
            for green_value, red_value in zip(green, red)
        ]

    if subtraction_mode == "infrared":
        return [
            green_value - infrared_value
            for green_value, infrared_value in zip(green, infrared)
        ]

    if subtraction_mode == "red_infrared_mean":
        return [
            green_value - ((red_value + infrared_value) / 2.0)
            for green_value, red_value, infrared_value in zip(green, red, infrared)
        ]

    raise ValueError(f"Unsupported channel subtraction mode: {subtraction_mode}")


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
def apply_fir_filter(signal_values, filter_coefficients):
    if not signal_values:
        return []

    coefficient_count = len(filter_coefficients)

    if coefficient_count == 0:
        raise ValueError("Filter must contain at least one coefficient.")

    if coefficient_count % 2 == 0:
        raise ValueError("A centered FIR filter must contain an odd number of coefficients.")

    half_window_size = coefficient_count // 2

    if len(signal_values) <= half_window_size:
        raise ValueError("The signal is too short for the selected FIR filter.")

    left_extension = list(reversed(signal_values[1:half_window_size + 1]))
    right_extension = list(reversed(signal_values[-half_window_size - 1:-1]))
    extended_signal = left_extension + list(signal_values) + right_extension
    filtered_signal = []

    for center_index in range(len(signal_values)):
        filtered_value = 0.0

        for coefficient_index in range(coefficient_count):
            signal_value = extended_signal[center_index + coefficient_index]
            coefficient = filter_coefficients[coefficient_index]
            filtered_value += coefficient * signal_value

        filtered_signal.append(filtered_value)

    return filtered_signal


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

    supported_filter_types = {"lowpass", "highpass", "bandpass", "bandstop"}

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


# Marks filter edge samples as invalid because FIR filtering can produce unreliable values near signal boundaries.
def mark_filter_edges_as_invalid(valid_samples, filter_coefficient_count):
    filter_edge_samples = min(filter_coefficient_count // 2, len(valid_samples) // 2)

    if filter_edge_samples <= 0:
        return valid_samples

    valid_samples[:filter_edge_samples] = False
    valid_samples[len(valid_samples) - filter_edge_samples:] = False

    return valid_samples


# Detects sudden sample-to-sample jumps and marks the surrounding region as invalid.
def mark_jump_artifacts(
    signal_values,
    valid_samples,
    sampling_frequency,
    jump_threshold_factor,
    artifact_padding_seconds,
):
    if len(signal_values) == 0:
        return valid_samples

    signal_differences = np.abs(np.diff(signal_values, prepend=signal_values[0]))
    median_difference = np.median(signal_differences)
    mad_difference = np.median(np.abs(signal_differences - median_difference))
    robust_difference_std = 1.4826 * mad_difference
    jump_threshold = median_difference + jump_threshold_factor * robust_difference_std
    jump_artifacts = signal_differences > jump_threshold
    padding_samples = int(artifact_padding_seconds * sampling_frequency)
    artifact_indices = np.where(jump_artifacts)[0]

    for artifact_index in artifact_indices:
        start_index = max(0, artifact_index - padding_samples)
        end_index = min(len(valid_samples), artifact_index + padding_samples + 1)
        valid_samples[start_index:end_index] = False

    return valid_samples


# Detects unusually large local signal ranges and marks those windows as possible motion artifacts.
def mark_range_artifacts(
    signal_values,
    valid_samples,
    sampling_frequency,
    range_window_seconds,
    range_threshold_factor,
    artifact_padding_seconds,
):
    sample_count = len(signal_values)

    if sample_count == 0:
        return valid_samples

    window_size = max(1, int(round(range_window_seconds * sampling_frequency)))
    window_size = min(window_size, sample_count)
    local_ranges = []

    for start_index in range(0, sample_count - window_size + 1):
        window_values = signal_values[start_index:start_index + window_size]
        local_ranges.append(np.max(window_values) - np.min(window_values))

    if not local_ranges:
        return valid_samples

    local_ranges = np.asarray(local_ranges)
    median_range = np.median(local_ranges)
    mad_range = np.median(np.abs(local_ranges - median_range))
    robust_range_std = 1.4826 * mad_range
    range_threshold = median_range + range_threshold_factor * robust_range_std
    padding_samples = int(artifact_padding_seconds * sampling_frequency)

    for start_index, local_range in enumerate(local_ranges):
        if local_range <= range_threshold:
            continue

        artifact_start_index = max(0, start_index - padding_samples)
        artifact_end_index = min(sample_count, start_index + window_size + padding_samples)
        valid_samples[artifact_start_index:artifact_end_index] = False

    return valid_samples


# Combines all artifact detection checks and returns a boolean mask indicating which samples are valid.
def detect_artifact_samples(
    signal_values,
    sampling_frequency,
    filter_coefficient_count,
    jump_threshold_factor=8.0,
    artifact_padding_seconds=0.5,
    range_detection_enabled=False,
    range_window_seconds=0.5,
    range_threshold_factor=6.0,
):
    signal_values = np.asarray(signal_values)

    if len(signal_values) == 0:
        return np.asarray([], dtype=bool)

    valid_samples = np.ones(len(signal_values), dtype=bool)
    valid_samples = mark_filter_edges_as_invalid(valid_samples, filter_coefficient_count)

    valid_samples = mark_jump_artifacts(
        signal_values,
        valid_samples,
        sampling_frequency,
        jump_threshold_factor,
        artifact_padding_seconds,
    )

    if range_detection_enabled:
        valid_samples = mark_range_artifacts(
            signal_values,
            valid_samples,
            sampling_frequency,
            range_window_seconds,
            range_threshold_factor,
            artifact_padding_seconds,
        )

    return valid_samples


def normalize_signal(signal_values, valid_samples, normalization_type):
    if normalization_type == "none":
        return signal_values

    valid_values = [value for value, is_valid in zip(signal_values, valid_samples) if is_valid]

    if len(valid_values) == 0:
        return signal_values

    if normalization_type == "robust_z_score":
        return normalize_with_robust_z_score(signal_values, valid_values)

    if normalization_type == "min_max":
        return normalize_with_min_max(signal_values, valid_values)

    return signal_values


def normalize_with_robust_z_score(signal_values, valid_values):
    median_value = median(valid_values)
    deviations = [abs(value - median_value) for value in valid_values]
    mad_value = median(deviations)

    robust_std = 1.4826 * mad_value
    return [(value - median_value) / robust_std for value in signal_values]


def normalize_with_min_max(signal_values, valid_values):
    min_value = min(valid_values)
    max_value = max(valid_values)

    if min_value == max_value:
        return signal_values

    normalized_values = [(value - min_value) / (max_value - min_value) for value in signal_values]
    return [min(1.0, max(0.0, value)) for value in normalized_values]


def invert_signal(signal_values):
    return [-value for value in signal_values]

# Applies all configured processing steps to the Green signal.
def process_green_signal(x_values, signals, config):
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

    processed_green = subtract_channels(processed_signals, config.CHANNEL_SUBTRACTION)
    processed_green = center_signal(processed_green)
    filter_type = config.FILTER_TYPE
    filter_coefficient_count = 1

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

        filter_coefficient_count = config.FILTER_COEFFICIENT_COUNT

        filter_coefficients = design_fir_filter(
            sampling_frequency=config.SAMPLING_FREQUENCY_HZ,
            cutoff_frequencies=cutoff_frequencies,
            coefficient_count=filter_coefficient_count,
            filter_type=filter_type,
            window_type=config.FILTER_WINDOW_TYPE,
        )

        processed_green = apply_fir_filter(processed_green, filter_coefficients)

    valid_samples = np.ones(len(processed_green), dtype=bool)

    if getattr(config, "ARTIFACT_DETECTION_ENABLED", False):
        valid_samples = detect_artifact_samples(
            signal_values=processed_green,
            sampling_frequency=config.SAMPLING_FREQUENCY_HZ,
            filter_coefficient_count=filter_coefficient_count,
            jump_threshold_factor=getattr(config, "ARTIFACT_JUMP_THRESHOLD_FACTOR", 8.0),
            artifact_padding_seconds=getattr(config, "ARTIFACT_PADDING_SECONDS", 0.5),
            range_detection_enabled=getattr(config, "RANGE_ARTIFACT_DETECTION_ENABLED", False),
            range_window_seconds=getattr(config, "ARTIFACT_RANGE_WINDOW_SECONDS", 0.5),
            range_threshold_factor=getattr(config, "ARTIFACT_RANGE_THRESHOLD_FACTOR", 6.0),
        )

    processed_green = normalize_signal(processed_green, valid_samples, config.NORMALIZATION_TYPE)

    if getattr(config, "INVERT_PROCESSED_SIGNAL", False):
        processed_green = invert_signal(processed_green)

    return processed_x_values, processed_green, valid_samples