import msvcrt
from time import sleep


_readline_cached_line = ""


def readline(echo: bool = True) -> None | str:
    global _readline_cached_line

    if msvcrt.kbhit():
        key_pressed = msvcrt.getch()
        if key_pressed in b"\x00\xe0":
            key_pressed += msvcrt.getch()
        elif key_pressed == b"\x03":
            raise KeyboardInterrupt
        elif key_pressed == b"\r":
            line = _readline_cached_line + "\n"
            _readline_cached_line = ""
            print(flush=True)
            return line
        elif key_pressed == b"\x08":
            _readline_cached_line = _readline_cached_line[:-1]
            if echo:
                print("\b \b", end="", flush=True)
        else:
            decoded_char = key_pressed.decode("cp850", errors="ignore")
            _readline_cached_line += decoded_char
            print(decoded_char, end="", flush=True)
        # print(f"\33[2K\r{message}", end="", flush=True)
    return None


if __name__ == "__main__":
    while True:
        try:
            message = readline()
            if message is not None:
                print(f"{message=}")
            sleep(0.1)
        except KeyboardInterrupt:
            break
