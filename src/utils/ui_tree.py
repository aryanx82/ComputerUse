"""
Unified UI Tree Normalizer & Semantic Search Utilities.

Normalizes platform-specific accessibility trees (macOS AXUIElement and Android uiautomator)
into a unified schema with automatic center-point calculation for direct clicking.
"""

from typing import Dict, Any, List, Optional


# Role normalization lookup tables
MACOS_ROLE_MAP: Dict[str, str] = {
    "AXButton": "button",
    "AXTextField": "text_field",
    "AXTextArea": "text_field",
    "AXStaticText": "text",
    "AXImage": "image",
    "AXWindow": "window",
    "AXGroup": "container",
    "AXCheckBox": "checkbox",
    "AXRadioButton": "radio",
    "AXPopUpButton": "dropdown",
    "AXComboBox": "dropdown",
    "AXScrollArea": "scroll_area",
    "AXList": "list",
    "AXTable": "list",
    "AXOutline": "list",
    "AXMenuItem": "menu_item",
    "AXMenuBarItem": "menu_item",
    "AXLink": "link",
    "AXSlider": "slider",
    "AXTabGroup": "tab_group",
}

ANDROID_CLASS_MAP: Dict[str, str] = {
    "Button": "button",
    "ImageButton": "button",
    "EditText": "text_field",
    "TextView": "text",
    "ImageView": "image",
    "CheckBox": "checkbox",
    "RadioButton": "radio",
    "Spinner": "dropdown",
    "ScrollView": "scroll_area",
    "HorizontalScrollView": "scroll_area",
    "ListView": "list",
    "RecyclerView": "list",
    "ViewGroup": "container",
    "FrameLayout": "container",
    "LinearLayout": "container",
    "RelativeLayout": "container",
    "Switch": "checkbox",
    "SeekBar": "slider",
}


def normalize_node(raw_node: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """
    Recursively normalize a raw UI node from macOS or Android into the standard schema.
    """
    node: Dict[str, Any] = {}

    # 1. Normalize Role
    raw_role = raw_node.get("role", "")
    if platform == "macos":
        normalized_role = MACOS_ROLE_MAP.get(raw_role, raw_role.lower().replace("ax", ""))
    elif platform == "android":
        normalized_role = ANDROID_CLASS_MAP.get(raw_role, raw_role.lower())
    else:
        normalized_role = raw_role.lower()
    node["role"] = normalized_role or "unknown"

    # 2. Normalize Label and Text
    title = raw_node.get("title") or raw_node.get("description") or ""
    text = raw_node.get("text") or raw_node.get("value") or ""
    label = title or text or ""

    if label:
        node["label"] = label
    if text:
        node["text"] = text

    # 3. Normalize Bounds and Compute Center Click Point
    bounds = raw_node.get("bounds")
    if bounds and isinstance(bounds, dict):
        x = int(bounds.get("x", 0))
        y = int(bounds.get("y", 0))
        w = int(bounds.get("width", 0))
        h = int(bounds.get("height", 0))

        node["bounds"] = {"x": x, "y": y, "width": w, "height": h}
        # Center coordinates for direct clicking
        node["center"] = {"x": x + (w // 2), "y": y + (h // 2)}

    # 4. Normalize States
    states: Dict[str, bool] = {}
    raw_states = raw_node.get("states", {})
    if isinstance(raw_states, dict):
        for k, v in raw_states.items():
            if v:
                states[k] = True

    if raw_node.get("enabled"):
        states["enabled"] = True
    if raw_node.get("focused"):
        states["focused"] = True
    if node["role"] in ("button", "link", "checkbox", "radio", "menu_item"):
        states["clickable"] = True

    if states:
        node["states"] = states

    # 5. Identifier
    ident = raw_node.get("resource_id") or raw_node.get("bundle_id") or raw_node.get("package") or ""
    if ident:
        node["identifier"] = ident

    # 6. Normalize Children Recursively
    raw_children = raw_node.get("children", [])
    if isinstance(raw_children, list):
        norm_children = []
        for child in raw_children:
            if isinstance(child, dict):
                c = normalize_node(child, platform)
                # Keep node if it has meaningful label, center, or children
                if "center" in c or "label" in c or "children" in c:
                    norm_children.append(c)
        if norm_children:
            node["children"] = norm_children

    return node


def normalize_ui_tree(raw_tree: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """
    Normalize an entire hierarchy tree into the unified schema.
    """
    root = normalize_node(raw_tree, platform)
    root["platform"] = platform
    root["app_name"] = raw_tree.get("app_name") or raw_tree.get("package") or "Unknown"
    return root


def search_elements(
    node: Dict[str, Any],
    text_query: Optional[str] = None,
    role_query: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, Any]]:
    """
    Recursively search a normalized tree for elements matching text or role queries.
    Returns a flattened list of matching elements with their click centers.
    """
    results: List[Dict[str, Any]] = []

    def _traverse(cur: Dict[str, Any]):
        if len(results) >= max_results:
            return

        matches_text = True
        if text_query:
            q = text_query.lower()
            cur_label = cur.get("label", "").lower()
            cur_text = cur.get("text", "").lower()
            matches_text = q in cur_label or q in cur_text

        matches_role = True
        if role_query:
            r = role_query.lower()
            cur_role = cur.get("role", "").lower()
            matches_role = r in cur_role

        if matches_text and matches_role and "center" in cur:
            results.append({
                "role": cur.get("role", "unknown"),
                "label": cur.get("label") or cur.get("text") or "",
                "bounds": cur.get("bounds"),
                "center": cur.get("center"),
                "identifier": cur.get("identifier", ""),
                "states": cur.get("states", {})
            })

        for child in cur.get("children", []):
            _traverse(child)

    _traverse(node)
    return results
