import contextlib
import sys


MAX_CODE_LENGTH = 50_000
MAX_OUTPUT_LENGTH = 65_536


class OutputLimitExceeded(Exception):
    pass


class LimitedWriter:
    def __init__(
        self,
        original_stream,
        maximum_length: int,
    ):
        self.original_stream = original_stream
        self.remaining = maximum_length

    def write(self, text) -> int:
        text = str(text)

        if self.remaining <= 0:
            raise OutputLimitExceeded

        allowed_text = text[: self.remaining]

        self.original_stream.write(allowed_text)
        self.original_stream.flush()

        self.remaining -= len(allowed_text)

        if len(allowed_text) < len(text):
            raise OutputLimitExceeded

        return len(allowed_text)

    def flush(self) -> None:
        self.original_stream.flush()


def main() -> None:
    code = sys.stdin.read(
        MAX_CODE_LENGTH + 1
    )

    if len(code) > MAX_CODE_LENGTH:
        print(
            "Code size limit exceeded.",
            file=sys.stderr,
        )
        raise SystemExit(121)

    limited_stdout = LimitedWriter(
        sys.stdout,
        MAX_OUTPUT_LENGTH,
    )

    limited_stderr = LimitedWriter(
        sys.stderr,
        MAX_OUTPUT_LENGTH,
    )

    execution_globals = {
        "__name__": "__main__",
        "__file__": "solution.py",
    }

    try:
        compiled_code = compile(
            code,
            "solution.py",
            "exec",
        )

        with (
            contextlib.redirect_stdout(
                limited_stdout
            ),
            contextlib.redirect_stderr(
                limited_stderr
            ),
        ):
            exec(
                compiled_code,
                execution_globals,
                execution_globals,
            )

    except OutputLimitExceeded:
        print(
            "\nOutput limit exceeded.",
            file=sys.__stderr__,
        )
        raise SystemExit(120)


if __name__ == "__main__":
    main()