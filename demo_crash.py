import argparse
import multiprocessing
import time


def burn_cpu() -> None:
    while True:
        pass


def use_memory(megabytes: int) -> None:
    data = [bytearray(1024 * 1024) for _ in range(megabytes)]
    while data:
        time.sleep(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CPU/RAM stress test")
    parser.add_argument("--scenario", choices=["cpu", "ram", "both"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--workers", type=int, default=multiprocessing.cpu_count())
    parser.add_argument("--memory-mb", type=int, default=512)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.scenario:
        choice = input("1) CPU\n2) RAM\n3) Both\nSelect: ").strip()
        args.scenario = {"1": "cpu", "2": "ram", "3": "both"}.get(choice)
    if not args.scenario:
        raise SystemExit("Invalid scenario")

    processes = []
    if args.scenario in {"cpu", "both"}:
        for _ in range(max(1, args.workers)):
            processes.append(multiprocessing.Process(target=burn_cpu))
    if args.scenario in {"ram", "both"}:
        processes.append(multiprocessing.Process(target=use_memory, args=(args.memory_mb,)))

    print(f"Starting {args.scenario} stress for {args.duration}s")
    for process in processes:
        process.start()

    try:
        time.sleep(max(1, args.duration))
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()
    print("Stress test finished")


if __name__ == "__main__":
    main()
