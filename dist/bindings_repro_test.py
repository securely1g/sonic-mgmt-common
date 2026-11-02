"""Regenerate real owner bindings twice, bypassing action-cache restoration."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    driver, generator, models = [Path(p).absolute() for p in sys.argv[1:]]
    with tempfile.TemporaryDirectory() as temporary:
        outputs = [Path(temporary) / (str(i) + ".go") for i in range(2)]
        for output in outputs:
            subprocess.run([str(driver), "--generator", str(generator),
                            "--models", str(models), "--output", str(output)], check=True)
        if outputs[0].read_bytes() != outputs[1].read_bytes():
            evidence = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", temporary))
            for i, output in enumerate(outputs):
                shutil.copyfile(output, evidence / ("bindings-" + str(i) + ".go"))
        assert outputs[0].read_bytes() == outputs[1].read_bytes(), (
            "Regenerating the same owner schema changed the Go bindings")
        print("Two independent generator processes produced byte-identical owner bindings")


if __name__ == "__main__":
    main()
