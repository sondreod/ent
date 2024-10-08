import os
import tempfile
import subprocess
import argparse
from os import environ
from pathlib import Path
from datetime import datetime
from typing import Tuple
from sys import exit  # pyinstaller requires exit to be imported

COMMANDS = ("list", "last", "find", "cat", "log")
ABBR_MAP = {"ls": "list", "la": "last", "fn": "find"}

JOURNAL_DIR = Path("~/.local/share/ent").expanduser()
JOURNAL_FILE = Path("~/.local/share/ent/journal.ad").expanduser()

if not JOURNAL_FILE.is_file():
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    created_timestamp = datetime.now().isoformat(timespec="seconds", sep=" ")
    JOURNAL_FILE.write_text(f"Journal starts at {created_timestamp}\n\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?")
    parser.add_argument("tags", nargs="?")
    # parser.add_argument("-f" "--force")
    # parser.add_argument("infile", nargs="?", type=argparse.FileType("r"), default=sys.stdin)
    args = parser.parse_args()
    input_data = None
    prefilled_tags = None
    if args.command:
        command = ABBR_MAP.get(args.command, args.command)

        if command == "log":
            # TODO: add pager and flip direction, (latest entry at the top).
            for message in segment_entries():
                timestamp = message.splitlines()[0][:19]
                tags = message.splitlines()[0][19:].strip()
                print(f"\033[38;5;208m{timestamp}\033[0m {tags}")
                print(message.splitlines()[1])

        if command == "list":
            journal()

        elif command == "last":
            last_notes(10)
            print("✏  showing last 10 entries.\n")

        elif command == "find":
            try:
                search_pattern = args.tags
                journal(search_pattern)
            except IndexError:
                print("No search pattern provided.")

        elif command == "cat":
            journal()

        else:
            input_data = args.command
            print(input_data)
            if input_data.strip().startswith("#"):
                prefilled_tags = ",".join(x for x in input_data.strip().split("#") if x)
                input_data = None
        if command in COMMANDS:
            exit(0)

    created_timestamp = datetime.now().isoformat(timespec="seconds", sep=" ")
    data = [
        input_data or "",
        "",
        "--",
        f"tags: {prefilled_tags or ''}",
        f"created_at: {created_timestamp}",
        "",
        "// Write you entry above this comment,",
        "// an empty entry will abort.",
        "",
    ]

    fd = tempfile.NamedTemporaryFile(suffix=".adoc", delete=False)
    fd.write("\n".join(data).encode("utf-8"))
    fd.seek(0)
    original_entry = fd.read()
    fd.close()

    if not input_data:
        editor_paths = (
            "/usr/bin/editor",
            "/etc/alternatives/editor",
        )
        call = ["vim", "-c", "startinsert", fd.name]  # Default to vim
        for p in editor_paths:  # Check default paths
            if editor := Path(p).resolve():
                if editor.is_file() and not editor.name.startswith("vim"):
                    call = [editor, fd.name]
                    break
        else:
            if editor := environ.get("EDITOR"):  # Check EDITOR environment var
                call = [editor, fd.name]

        subprocess.call(call)

    mefile = open(fd.name, "rb")
    newdata = mefile.read()
    mefile.close()
    os.remove(mefile.name)

    if original_entry == newdata and not input_data:
        print("❗ Empty log entry, no entry created.\n")
    else:

        note = "\n".join(newdata.decode("utf-8").splitlines())

        with open(JOURNAL_FILE, "a", encoding="utf-8") as fd:
            entry, metadata = parse_note_tempfile(note)
            add_note(entry, metadata)
            if num_tags := metadata["tags"]:
                print(f"✨ Entry created with {num_tags}.\n")
            else:
                print("✨ Entry created.\n")


def parse_note_tempfile(content: str) -> Tuple[str, dict]:
    metadata = {}
    *note, metadata_str = content.split("--")

    for line in metadata_str.splitlines():
        if line and not line.startswith("//"):
            key, value = map(str.strip, line.split(":", maxsplit=1))
            metadata[key] = value

    return "\n".join(note) + "\n", metadata


def add_note(entry, metadata):
    metadata["tags"] = " ".join(
        ["#" + x.strip() for x in metadata["tags"].strip().split(",") if x]
    )
    with JOURNAL_FILE.open("a") as fd:
        fd.write(
            "\n".join(
                [
                    "",
                    "␞" + metadata["created_at"] + " " + metadata["tags"],
                    entry.strip(),
                    "",
                ]
            )
        )


def segment_entries():
    message = ""
    for line in JOURNAL_FILE.open("r"):
        if line.startswith("␞"):
            line = line[1:]
            if message:
                yield message
                message = ""
        message += line
    if message:
        yield message


def journal(tags=None):
    message = ""
    for message in segment_entries():
        if tags:
            first_line = message.splitlines()[0]
            if tags not in first_line:
                message = ""
                continue
        if message:
            print(message, end="")


def last_notes(n=0):
    for message in list(segment_entries())[-10:]:
        print(message)


if __name__ == "__main__":
    main()
