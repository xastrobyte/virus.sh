from typing import List

from model import Entry, Directory, NormalFile, VirusFile


def __dir_arg_parse(directory: Directory, directory_path: str) -> Entry:
    """Parses a concatenated directory path to return the proper target
    which may be a file or directory
    """
    dir_split = directory_path.split("/")
    for target in dir_split:
        if target == "..":
            if directory.get_parent():
                directory = directory.get_parent()
        elif directory.get_name() != target and target != ".":
            directory = directory.get_entry(target)
    return directory


def ls(console, args):
    """Mimics the ls command to list the contents of a Directory
    which will distinguish the directories from files
    by placing the Directories first and Files second
    """

    # Keep track of the options for the ls command
    options = {
        "show_hidden": {
            "identifier": "a",
            "value": False}}
    targets = []

    # Iterate through all of the args, separating options from targets
    for arg in args:
        if arg.startswith("-"):
            for opt in options:
                options[opt]["value"] = options[opt]["identifier"] in arg
        else:
            targets.append(arg)

    # List the results
    if len(targets) == 0:
        return console.get_current_dir().list_contents(options["show_hidden"]["value"])
    results = []
    for target in targets:
        current_dir = __dir_arg_parse(console.get_current_dir(), target)
        if current_dir:
            if len(targets) > 1:
                results.append(f"{target}{':' if isinstance(current_dir, Directory) else ''}")
            if isinstance(current_dir, Directory):
                results.append(current_dir.list_contents(options["show_hidden"]["value"]))
        else:
            results.append(f"ls: {target}: No such file or directory")
    return "\n".join(results)


def cd(console, args):
    """Mimics the cd command to change Directories"""
    if len(args) > 1:
        return "usage: cd <directory>"
    if len(args) == 0:
        usr_dir = console.get_root().get_entry("usr")
        username = console.get_save().get_username()
        console.set_current_dir(usr_dir.get_entry(username))
        return

    target = args[0].split("/")
    for tgt in target:
        current_dir = console.get_current_dir()
        if tgt == ".":
            continue
        elif tgt == "..":
            if (console.is_in_play() or console.is_in_tutorial()) and current_dir == console.get_save().get_trash():
                console.set_current_dir(console.get_previous_dir())
            elif current_dir.get_parent():
                console.set_current_dir(current_dir.get_parent())
            continue
        elif tgt == "Trash" and (console.is_in_play() or console.is_in_tutorial()):
            console.set_previous_dir(console.get_current_dir())
            if console.is_in_play():
                console.set_current_dir(console.get_save().get_trash())
            elif console.is_in_tutorial():
                console.set_current_dir(console.get_tutorial_trash())
            return
        found = False
        for entry in current_dir.get_entries():
            if entry.get_name() == tgt:
                if isinstance(entry, Directory):
                    found = True
                    console.set_current_dir(entry)
                else:
                    return f"cd: not a directory: {tgt}"
        if not found:
            return f"cd: {tgt}: No such file or directory"


def cat(console, args):
    if len(args) == 0:
        return "usage: cat <file(s)>"

    result = []
    for file in args:
        file = __dir_arg_parse(console.get_current_dir(), file)
        if file:
            if isinstance(file, Directory):
                result.append(f"cat: {file.get_name()}: Is a directory")
                break
            else:
                file_result = ""
                total = 0
                for byte in file.get_bytes():
                    file_result += f"{hex(byte)[2:].rjust(2, '0')} "
                    total += 1
                    if total % 16 == 0:
                        file_result += "\n"
                result.append(file_result)
    return "\n".join(result)


def rm(console, args):
    if len(args) == 0:
        return "usage: rm [-r] file ..."

    recursive = "-r" in args or (len(args) > 0 and args[0].startswith("-") and "r" in args[0])

    target = None
    for entry in console.get_current_dir().get_entries():
        if entry.get_name() == args[-1]:
            target = entry
    if not target or console.get_root() is None:
        return f"rm: {args[-1]}: No such file or directory"

    # The wrong virus file was deleted
    if isinstance(target, VirusFile):
        if target.get_number() != console.get_save().get_virus_files()[0] + 1:
            console.get_save().increase_speed(target)
            return "rm: Incorrect virus file deleted: File moved to new location; New file spawned"
        else:
            console.get_save().remove_virus(target)
            return f"rm: Successful deletion: {target} removed"

    else:
        removed = __rm_helper(target, recursive)
        console.get_current_dir().remove_entry(target)
        for entry in removed:
            entry.set_parent(console.get_trash())
        console.get_trash().add_entries(removed)


def __rm_helper(directory: Directory, recursive: bool = True) -> List[Entry]:
    removed = []
    for entry in directory.get_entries():
        if isinstance(entry, Directory):
            if entry.get_size() == 0 or recursive:
                removed.append(entry)
        elif isinstance(entry, NormalFile):
            removed.append(entry)
    for entry in removed:
        directory.remove_entry(entry)
    return removed


def restore(console, args):
    if len(args) == 0:
        return "usage: restore <file>"

    if console.get_current_dir() != console.get_trash():
        return "restore: must be in Trash directory"

    if len(args) == 1 and args[0] == "*":
        args = [entry.get_name() for entry in console.get_trash().get_entries()]
    result = []
    for entry in args:
        file = __dir_arg_parse(console.get_trash(), entry)
        if file:
            if isinstance(file, NormalFile):
                file = file.restore(console.get_root())
                console.get_save().restored_file()
                result.append(f"{file.get_name()} restored to {str(file)}")
            else:
                result.append(f"restore: {file.get_name()}: is not a valid file")
        else:
            result.append(f"restore: {entry}: No such file")
    return "\n".join(result)


def trace(console, args):
    if len(args) == 0:
        return "usage: trace <file(s)>"

    if console.is_in_play():
        trash = console.get_trash()
        result = []
        for file in args:
            file = __dir_arg_parse(trash, file)
            if file:
                if isinstance(file, Directory):
                    result.append(f"trace: {file.get_name()}: Is a directory")
                    continue
                else:
                    for log in console.get_save().get_deletion_log():
                        if file.get_name() == log[1].split("/")[-1]:
                            result.append(log[2])
        return "\n".join(result)


def mntr(console, args):
    if len(args) != 0:
        return "usage: mntr"

    save = console.get_save()
    log = save.get_deletion_log()
    speed = save.get_speed()
    result = "last log entry: {}\nspeed: {}s\nvirus files deleted: {}\nfiles deleted by virus: {}"
    return result.format(
        log[-1][1]
        if len(log) != 0
        else "None found", speed,
        save.get_virus_files()[0], save.get_normal_files()[0])


def track(console, args):
    if len(args) == 0:
        tracked_files = console.get_save().get_tracked_files()
        return "\n".join([
            f"{i + 1}: {tracked_files[i]}"
            for i in range(len(tracked_files))
            if tracked_files[i] is not None
        ])
    elif len(args) % 2 != 0:
        return "usage: track [<number> <file> ...]"

    target_numbers = []
    targets = []
    for i in range(0, len(args), 2):
        if not args[i].isdigit():
            return f"track: {args[i]}: not a number"
        target_numbers.append(int(args[i]))
        targets.append(args[i + 1])
    messages = []
    for i in range(len(targets)):
        target = targets[i]
        target_number = target_numbers[i]
        tgt = __dir_arg_parse(console.get_current_dir(), target)
        messages.append("track: {}".format(
            f"{tgt} tracked"
            if tgt is not None
            else f"{tgt}: No such file or directory"))
        if tgt:
            console.get_save().track_virus(target_number, tgt)
    return "\n".join(messages)


def tut(_, args):
    if len(args) != 0:
        return "usage: tut"
    return "Type ./tutorial.sh"


def help_command():
    return ("ls [directory] -> Lists the specified directory, or the current one if none is given\n" +
            "cd [directory] -> Changes the current directory, or moves to the beginning directory if none is given\n" +
            "cat <file> -> Prints out the contents of a file\n" +
            "rm [-r] [directory OR file] -> Removes a directory or file and moves it to the Trash\n" +
            "track [<number> <file> ...] -> Allows you to track a virus file with a number to identify it easier.\n" +
            "\tIf nothing is given, it will show you the files you're tracking currently.\n" +
            "trace <file> -> (Can only be used in the Trash directory) Allows you to trace where a file was deleted from\n" +
            "mntr -> Shows you the most recently deleted file, the speed at which files are deleted by the virus, how\n" +
            "\tmany virus files you've deleted, and how many files have been deleted by the virus.\n" +
            "restore <file> -> Restores a file to its original location (Can only be used in the Trash directory)\n" +
            "help -> Shows this help message!")
