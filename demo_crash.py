import time
import multiprocessing
import sys

def cpu_stress():
    """Spawn an infinite loop to max out one CPU core."""
    while True:
        pass

def ram_stress(mb=512):
    """Allocate and hold memory to simulate RAM spike."""
    print(f"  Allocating {mb}MB RAM...")
    data = []
    for _ in range(mb):
        data.append(bytearray(1024 * 1024))  # 1MB chunks
    while True:
        time.sleep(1)

if __name__ == "__main__":
    print("=== Self-Healing Monitor — Demo ===\n")
    print("Choose a scenario:\n")
    print("  1) CPU spike   — max out all CPU cores")
    print("  2) RAM spike   — allocate 512MB of memory")
    print("  3) Both        — CPU + RAM stress")
    print("  4) Quick CPU   — 1 core for 30 seconds then stop")
    print()

    choice = input("Select (1/2/3/4): ").strip()

    processes = []

    if choice in ("1", "3"):
        cores = multiprocessing.cpu_count()
        print(f"\nSpawning {cores} CPU stress workers...")
        for _ in range(cores):
            p = multiprocessing.Process(target=cpu_stress, name="demo_cpu_stress")
            p.start()
            processes.append(p)

    if choice in ("2", "3"):
        print("\nSpawning RAM stress worker...")
        p = multiprocessing.Process(target=ram_stress, name="demo_ram_stress")
        p.start()
        processes.append(p)

    if choice == "4":
        print("\nSpawning 1 CPU worker for 30 seconds...")
        p = multiprocessing.Process(target=cpu_stress, name="demo_cpu_stress")
        p.start()
        processes.append(p)

        time.sleep(30)
        for p in processes:
            p.terminate()
        print("Done. CPU stress stopped after 30s.")
        sys.exit(0)

    if not processes:
        print("Invalid choice.")
        sys.exit(1)

    print(f"\n{len(processes)} stress worker(s) running.")
    print("   The monitor should detect and notify shortly.")
    print("   Press Ctrl+C to stop.\n")

    try:
        while True:
            alive = sum(1 for p in processes if p.is_alive())
            print(f"\r   Workers alive: {alive}/{len(processes)}", end="", flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nStopping workers...")
        for p in processes:
            p.terminate()
        print("Done.")
        sys.exit(0)
