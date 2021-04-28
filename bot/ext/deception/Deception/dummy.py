from dataclasses import dataclass

"""
These are dataclasses imagined to imposter
discord classes for testing purposes.
"""


@dataclass
class Member:
    name: str
    id: int
    display_name: str = "abcdef"
