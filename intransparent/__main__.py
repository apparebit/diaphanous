import sys

if sys.version_info < (3, 10):
    print(f"{__package__} requires at least Python 3.10!")
    sys.exit(1)

from .main import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
