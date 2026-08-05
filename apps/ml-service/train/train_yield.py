from train.common import parser, require_data


def main() -> None:
    cli = parser("Train borehole yield classifier")
    cli.add_argument("--min-samples", type=int, default=200)
    args = cli.parse_args()
    require_data(args.min_samples, 0)


if __name__ == "__main__":
    main()
