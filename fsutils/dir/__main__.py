import argparse

from .DirNode import Dir


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="A collection of fsutils.dir utilities")
    subparsers = parser.add_subparsers(help="commands", dest="action")

    serialize = subparsers.add_parser("serialize", help="Serialize directory")
    serialize.add_argument("PATH", help="Directory to serialize", default="./")
    serialize.add_argument(
        "--chunk",
        "-c",
        help="Chunk refers to how many bytes should be read from each file during the serialization process. A higher number might yield more accurate results at the cost of time/space complexity",
        default=16392,
    )

    describe = subparsers.add_parser(
        "describe", help="Provide a quick overview of the directory contents"
    )
    describe.add_argument("PATH", help="Target directory")
    describe.add_argument("--size", "-s", help="Include sum of the file sizes in the results")
    return parser.parse_args()


def main(dir_path: str, action: str, *args, **kwargs) -> int:
    """Execute the given action."""
    path = Dir(dir_path)
    match action:
        case "serialize":
            db = path.serialize(replace=True)
            print(len(db))
            return 0
        case "describe":
            path.describe()
            return 0
        case _:
            print("\033[31mError:\033[0m", action, "is not a know action")
            return -1


if __name__ == "__main__":
    args = parse_args()
    main(args.PATH, args.action)
