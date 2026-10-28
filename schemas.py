"""Tool schemas. The first sentence of each description stays within 60 characters."""

CHECK = {
    "name": "scar_check",
    "description": (
        "Check a denied command shape against scars. "
        "Returns the receipt when a kept shape covers the call, and does not run the call."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tool": {"type": "string", "description": "Tool name to compare."},
            "arguments": {"type": "object", "description": "Argument object to compare."},
        },
        "required": ["tool", "arguments"],
    },
}

LIST = {
    "name": "scar_list",
    "description": (
        "List denied command scars kept on this computer. "
        "Reads the ledger and does not change it."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

FORGET = {
    "name": "scar_forget",
    "description": (
        "Forget one scar after the person approves it. "
        "Hermes shows the approval card first when the question fits. "
        "A question past 7 lines of 63 columns is not sent, and the scar stays."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "minimum": 1, "description": "Scar id from scar_list."},
        },
        "required": ["id"],
    },
}

ALL_SCHEMAS = [CHECK, LIST, FORGET]
