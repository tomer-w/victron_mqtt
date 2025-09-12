# Complex is: "Switch {output:switch_{output}_custom_name} Dimming"
def replace_complex_ids(orig_str: str, match_func) -> str:
    """Replace placeholders in the string with matched items from self.key_values."""
    import re

    # Match {key:name_with_nested_{placeholder}} in the string
    pattern = re.compile(r"\{(?P<moniker>[^:]+:(?:[^{}]|{[^{}]*})+)\}")
    return pattern.sub(match_func, orig_str)

# Complex is: "Switch {output:switch_{output}_custom_name} Dimming"
# Simple is: "Switch {output} Dimming"
def replace_complex_id_to_simple(orig_str: str) -> str:
    def replace_match(match):
        moniker = match.group('moniker')
        key, suffix = moniker.split(':', 1)
        assert key and suffix, f"Invalid moniker format: {moniker} in topic: {orig_str}"
        return f"{{{key}}}"

    return replace_complex_ids(orig_str, replace_match)
