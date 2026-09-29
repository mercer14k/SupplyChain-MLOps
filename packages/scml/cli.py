import argparse
import json
import os
import time
from datetime import UTC, datetime

from scml.data.store import Store
from scml.services.bootstrap import bootstrap, generate_samples
from scml.services.config import Settings
from scml.services.lifecycle import Lifecycle


def main():
    parser = argparse.ArgumentParser(prog="scml")
    parser.add_argument("command", choices=["worker", "init", "keys", "generate", "drain"])
    args = parser.parse_args()
    if args.command == "generate":
        generate_samples()
        return
    settings = Settings()
    service = Lifecycle(Store(settings.root))
    if args.command == "keys":
        print("Local credentials — keep private. Paste the required role into Workspace access.")
        for role, token in settings.tokens.items():
            print(f"{role}: {token}")
        return
    bootstrap(service)
    if args.command == "init":
        return
    if args.command == "drain":
        while service.work_once():
            pass
        return
    if args.command == "worker":
        while True:
            heartbeat = settings.root / "worker-heartbeat.json"
            temp = heartbeat.with_suffix(".tmp")
            temp.write_text(json.dumps({"at": datetime.now(UTC).isoformat(), "pid": os.getpid()}))
            temp.replace(heartbeat)
            service.tick()
            worked = service.work_once()
            if not worked:
                time.sleep(2)


if __name__ == "__main__":
    main()
