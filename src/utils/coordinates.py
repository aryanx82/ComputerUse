def translate_coordinates(x: int, y: int, scale: float) -> tuple[int, int]:
    return int(x / scale), int(y / scale)
