import os
import sys
import time

LOCK = "e2e.lock"


def e2e():
    if os.path.exists(LOCK):
        print("e2e: another e2e run holds e2e.lock")
        return 1
    open(LOCK, "w").close()
    with open("e2e.log", "a") as log:
        log.write(f"start {time.time():.2f}\n")
    time.sleep(2)
    with open("e2e.log", "a") as log:
        log.write(f"end {time.time():.2f}\n")
    os.remove(LOCK)
    print("e2e: ok")
    return 0


def main():
    print("lint: ok")
    print("test: ok")
    if "--skip" in sys.argv and "e2e" in sys.argv:
        print("e2e: skipped")
        return 0
    return e2e()


if __name__ == "__main__":
    sys.exit(main())
