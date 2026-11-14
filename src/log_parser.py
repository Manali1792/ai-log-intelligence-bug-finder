import re
import hashlib

ERROR_LEVELS = {"ERROR", "CRITICAL", "FATAL"}

def extract_errors(log_text: str) -> list[str]:
    """Extract error and critical-level log entries."""

    error_logs = []

    for line in log_text.splitlines():
        match = re.search(
            r"\b(ERROR|CRITICAL|FATAL)\b",
            line,
            re.IGNORECASE
        )

        if match:
            error_logs.append(line.strip())

    return error_logs


def extract_error_contexts(
    log_text: str,
    context_lines: int = 2
) -> list[str]:
    """Extract error entries along with surrounding log lines."""

    lines = log_text.splitlines()

    error_indices = [
        index
        for index, line in enumerate(lines)
        if re.search(
            r"\b(ERROR|CRITICAL|FATAL)\b",
            line,
            re.IGNORECASE
        )
    ]

    if not error_indices:
        return []

    ranges = []

    for index in error_indices:
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)

        if ranges and start <= ranges[-1][1]:
            ranges[-1][1] = max(ranges[-1][1], end)
        else:
            ranges.append([start, end])

    return [
        "\n".join(lines[start:end])
        for start, end in ranges
    ]

#error fingerprinting means, if sam error comes multiple times so we combine it to one

# this function converts error message to standard format

def normalize_error(error_line: str) -> str:
    """Normalize dynamic values while preserving meaningful error codes."""

    normalized = error_line.strip()

    # 1. Normalize timestamps
    normalized = re.sub(
        r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
        "<TIMESTAMP>",
        normalized
    )

    # 2. Normalize UUIDs
    normalized = re.sub(
        r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b",
        "<UUID>",
        normalized
    )

    # 3. Normalize IP addresses
    normalized = re.sub(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "<IP>",
        normalized
    )

    # 4. Normalize labelled dynamic IDs only, if there is like http 400 or http 500 etc so it will not normalise , so that it will not combine 
    normalized = re.sub(
        r"\b(user|order|customer|request|session|transaction|account|payment)[\s_-]*(?:id)?\s*[:=#]?\s*\d+\b",
        lambda match: f"{match.group(1).lower()} <ID>",
        normalized,
        flags=re.IGNORECASE
    )

    return normalized

#---------------------------------------------------------------------------------------------------

def generate_fingerprint(error_line: str) -> str:
    """Generate a stable fingerprint for similar errors."""

    normalized = normalize_error(error_line)

    # Ignore severity while identifying the underlying error
    normalized = re.sub(
        r"\b(ERROR|CRITICAL|FATAL)\b",
        "<SEVERITY>",
        normalized,
        flags=re.IGNORECASE
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

#------------------------------------------------------------------------------------------

def group_errors(log_text: str) -> list[dict]:
    """Group similar errors and track their frequency and timeline."""

    groups = {}

    severity_priority = {
        "ERROR": 1,
        "CRITICAL": 2,
        "FATAL": 3
    }   #higher no. means higher severity

    for error_line in extract_errors(log_text):

        fingerprint = generate_fingerprint(error_line)

        # Extract timestamp, if available
        timestamp_match = re.search(
            r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
            error_line
        )
        #output of re.search() function is a Match object not a direct matching text
        timestamp = (
            timestamp_match.group()
            if timestamp_match
            else None
        )

        # Extract severity
        severity_match = re.search(
            r"\b(ERROR|CRITICAL|FATAL)\b",
            error_line,
            flags=re.IGNORECASE
        )

        severity = severity_match.group().upper()

        if fingerprint not in groups:
            groups[fingerprint] = {
                "fingerprint": fingerprint,
                "normalized_error": normalize_error(error_line),
                "count": 0,
                "severity": severity,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "examples": []
            }

        group = groups[fingerprint]

        group["count"] += 1

        # Keep the highest severity seen in this group
        if severity_priority[severity] > severity_priority[group["severity"]]:
            group["severity"] = severity

        # Update timeline
        if timestamp:
            if group["first_seen"] is None or timestamp < group["first_seen"]:
                group["first_seen"] = timestamp

            if group["last_seen"] is None or timestamp > group["last_seen"]:
                group["last_seen"] = timestamp

        # Keep maximum 3 original examples
        if len(group["examples"]) < 3:
            group["examples"].append(error_line)

    return sorted(
        groups.values(),
        key=lambda item: item["count"],
        reverse=True
    )

#---------------------------------------------------------------------------------

# def group_errors(log_text: str) -> list[dict]:
#     """Group similar error messages using fingerprints."""

#     groups = {}

#     for line in extract_errors(log_text):

#         fingerprint = generate_fingerprint(line)

    #     if fingerprint not in groups:
    #         groups[fingerprint] = {
    #             "fingerprint": fingerprint,
    #             "normalized_error": normalize_error(line),
    #             "count": 0,
    #             "examples": []
    #         }

    #     groups[fingerprint]["count"] += 1

    #     if len(groups[fingerprint]["examples"]) < 3:
    #         groups[fingerprint]["examples"].append(line)

    # return list(groups.values())  #convert Dictionary groups to list mein 
