"""Conservative parsing of channel identifiers supplied with the sample data."""

from __future__ import annotations

from dataclasses import dataclass
import re


CHANNEL_ID_PATTERN = re.compile(
    r"^(?P<prefix>POL|EEG) "
    r"(?P<electrode_code>[A-Za-z]+)"
    r"(?P<contact_text>[0-9]+)"
    r"(?P<reference_tag>-Ref)?$"
)

AUXILIARY_DC_PATTERN = re.compile(r"^POL DC(?:0[1-9]|1[0-6])$")


@dataclass(frozen=True)
class ParsedChannelId:
    """Syntactic fields only; electrode codes are not anatomical labels."""

    raw_label: str
    source_prefix: str
    electrode_code: str
    contact_text: str
    contact_number: int
    reference_tag: str | None


def parse_channel_id(label: str) -> ParsedChannelId | None:
    """Parse the observed channel syntax without inventing anatomical meaning."""

    match = CHANNEL_ID_PATTERN.fullmatch(label)
    if match is None:
        return None
    fields = match.groupdict()
    return ParsedChannelId(
        raw_label=label,
        source_prefix=fields["prefix"],
        electrode_code=fields["electrode_code"],
        contact_text=fields["contact_text"],
        contact_number=int(fields["contact_text"]),
        reference_tag=fields["reference_tag"],
    )


def is_auxiliary_dc_channel(label: str) -> bool:
    """Return whether a label belongs to the fixed DC01--DC16 input block."""

    return AUXILIARY_DC_PATTERN.fullmatch(label) is not None


def infer_channel_role(label: str) -> str:
    """Assign a conservative model-input role without inventing anatomy."""

    if is_auxiliary_dc_channel(label):
        return "auxiliary_dc"
    if parse_channel_id(label) is not None:
        return "seeg_candidate"
    return "unknown"


def neural_channel_indices(labels: list[str] | tuple[str, ...]) -> list[int]:
    """Return channels eligible for neural-signal preprocessing and modeling."""

    return [index for index, label in enumerate(labels) if infer_channel_role(label) == "seeg_candidate"]
