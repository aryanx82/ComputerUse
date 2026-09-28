from typing import List, Dict, Any, Optional
from src.router import ToolRouter

def register_interact_tools(mcp, router: ToolRouter):

    @mcp.tool()
    def click(
        device_id: str = "mac-primary",
        x: int = 0,
        y: int = 0,
        button: str = "left",
        click_count: int = 1
    ) -> str:
        """
        Perform a mouse click or tap at the specified (x, y) coordinates on the device.

        Args:
            device_id: Target device (default "mac-primary").
            x: Horizontal pixel coordinate (0 = left edge, native resolution).
            y: Vertical pixel coordinate (0 = top edge, native resolution).
            button: "left", "right" (context menu), or "center"/"middle".
            click_count: 1 for single click, 2 for double-click, 3 for triple-click.
        """
        result = router.click(device_id, x, y, button=button, click_count=click_count)
        if not result.success:
            return f"Error clicking at ({x}, {y}): {result.error}"
        click_desc = "Single" if click_count == 1 else ("Double" if click_count == 2 else f"{click_count}x")
        return f"{click_desc} {button}-clicked at ({x}, {y}) successfully."

    @mcp.tool()
    def type_text(device_id: str = "mac-primary", text: str = "") -> str:
        """
        Type text onto the device using direct Unicode injection.
        Supports full UTF-8 including accented letters, symbols, spaces, and emojis.

        Args:
            device_id: Target device (default "mac-primary").
            text: The exact string to type into the currently focused input field.
        """
        if not text:
            return "No text provided to type."
        result = router.type_text(device_id, text)
        if not result.success:
            return f"Error typing text: {result.error}"
        return f"Typed {len(text)} characters successfully."

    @mcp.tool()
    def press_key(
        device_id: str = "mac-primary",
        key: str = "return",
        modifiers: Optional[List[str]] = None
    ) -> str:
        """
        Press a keyboard key or keyboard shortcut combination.

        Args:
            device_id: Target device (default "mac-primary").
            key: Key name: "return"/"enter", "tab", "space", "escape", "backspace"/"delete",
                 "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
                 or single characters like "a"-"z", "0"-"9", "f1"-"f12".
            modifiers: Optional list of modifier keys: ["cmd"], ["ctrl"], ["alt"/"option"], ["shift"].
                       Example for Cmd+C: key="c", modifiers=["cmd"].
                       Example for Cmd+Shift+3: key="3", modifiers=["cmd", "shift"].
        """
        mods = modifiers or []
        result = router.press_key(device_id, key, modifiers=mods)
        if not result.success:
            return f"Error pressing key '{key}': {result.error}"
        combo = "+".join(mods + [key]) if mods else key
        return f"Pressed key '{combo}' successfully."

    @mcp.tool()
    def drag(
        device_id: str = "mac-primary",
        from_x: int = 0,
        from_y: int = 0,
        to_x: int = 0,
        to_y: int = 0
    ) -> str:
        """
        Perform a click-and-drag gesture from one point to another.

        Args:
            device_id: Target device (default "mac-primary").
            from_x: Starting horizontal pixel coordinate.
            from_y: Starting vertical pixel coordinate.
            to_x: Destination horizontal pixel coordinate.
            to_y: Destination vertical pixel coordinate.
        """
        result = router.drag(device_id, from_x, from_y, to_x, to_y)
        if not result.success:
            return f"Error dragging: {result.error}"
        return f"Dragged from ({from_x}, {from_y}) to ({to_x}, {to_y}) successfully."

    @mcp.tool()
    def scroll(
        device_id: str = "mac-primary",
        x: int = 500,
        y: int = 500,
        delta_y: int = -50,
        delta_x: int = 0
    ) -> str:
        """
        Scroll at a specific screen location using pixel scroll units.

        Args:
            device_id: Target device (default "mac-primary").
            x: Horizontal coordinate where the scroll wheel operates.
            y: Vertical coordinate where the scroll wheel operates.
            delta_y: Vertical scroll amount in pixels. Negative scrolls down, positive scrolls up.
            delta_x: Horizontal scroll amount in pixels (default 0).
        """
        result = router.scroll(device_id, x, y, delta_x=delta_x, delta_y=delta_y)
        if not result.success:
            return f"Error scrolling: {result.error}"
        direction = "down" if delta_y < 0 else "up"
        return f"Scrolled {direction} by {abs(delta_y)}px at ({x}, {y}) successfully."

    @mcp.tool()
    def open_app(device_id: str = "mac-primary", app_name: str = "") -> str:
        """
        Launch or activate an application on the device by its name.

        Args:
            device_id: Target device (default "mac-primary").
            app_name: Name of the application (e.g. "Safari", "Notes", "Calculator", "TextEdit", "Terminal").
        """
        if not app_name:
            return "No application name provided."
        try:
            info = router.open_app(device_id, app_name)
            return f"Application '{app_name}' activated successfully."
        except Exception as e:
            return f"Error opening app '{app_name}': {e}"

    @mcp.tool()
    def click_ui_element(
        device_id: str = "mac-primary",
        text_query: str = "",
        role_query: str = ""
    ) -> str:
        """
        Find an accessible UI element by its text/label and click its center directly.
        Bypasses the need to manually compute bounding boxes or inspect screenshots!

        Args:
            device_id: Target device ("mac-primary", "android-primary", etc.).
            text_query: Text or label of the target button, menu, or element.
            role_query: Optional role filter (e.g. "button", "link", "text_field").
        """
        if not text_query:
            return "Please provide text_query to identify the element to click."
        rq = role_query.strip() if role_query else None
        res = router.click_ui_element(device_id, text_query=text_query.strip(), role_query=rq)
        if res.success:
            return f"Successfully clicked UI element matching '{text_query}' on {device_id}."
        return f"Failed to click UI element: {res.error}"

    @mcp.tool()
    def open_url(device_id: str = "mac-primary", url: str = "https://google.com") -> str:
        """
        Open a URL in the device's default web browser across Mac or Android.

        Args:
            device_id: Target device ("mac-primary", "android-primary", etc.).
            url: The HTTP/HTTPS web address to navigate to.
        """
        try:
            res = router.open_url(device_id, url)
            return f"Opened URL '{url}' on {device_id} successfully."
        except Exception as e:
            return f"Error opening URL on {device_id}: {e}"
