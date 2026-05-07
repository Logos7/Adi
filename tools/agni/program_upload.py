from __future__ import annotations

try:
    from tools.agni.upload_sutra import assemble_file, upload_words
except ModuleNotFoundError:
    from upload_sutra import assemble_file, upload_words


def upload_text_program(port: str, baud: int, path: str, boot_timeout: float, ack_timeout: float) -> None:
    words = assemble_file(path, graphics="off")
    upload_words(port, baud, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)


def upload_graphics_program(
    port: str,
    baud: int,
    path: str,
    width: int | None,
    height: int | None,
    max_iter: int,
    boot_timeout: float,
    ack_timeout: float,
) -> None:
    normalized_path = path.replace("\\", "/").lower()
    words = assemble_file(
        path,
        width=width,
        height=height,
        max_iter=max_iter if "fractals" in normalized_path else None,
        graphics="auto",
    )
    upload_words(port, baud, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)
