from train.common import parser, require_data


def main() -> None:
    cli = parser("Train formation classifier")
    cli.add_argument("--min-per-class", type=int, default=30)
    args = cli.parse_args()
    require_data(args.min_per_class, 0)


if __name__ == "__main__":
    main()
