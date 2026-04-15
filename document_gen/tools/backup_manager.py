import os
import shutil
import datetime
import argparse
import sys

# Directories to backup
DIRS_TO_BACKUP = ["api", "agents", "switch", "banks", "psps"]
BACKUP_ROOT = "backups"

def create_backup(tag=None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}"
    if tag:
        folder_name += f"_{tag}"
    
    backup_path = os.path.join(BACKUP_ROOT, folder_name)
    
    if os.path.exists(backup_path):
        print(f"Backup path {backup_path} already exists. Aborting.")
        return None

    os.makedirs(backup_path)
    print(f"Creating backup at: {backup_path}")

    for dirname in DIRS_TO_BACKUP:
        src = os.path.join(os.getcwd(), dirname)
        dst = os.path.join(backup_path, dirname)
        
        if os.path.exists(src):
            print(f"  Copying {dirname}...")
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'venv', '.venv', '.git'))
        else:
            print(f"  Warning: {dirname} not found, skipping.")
            
    print("Backup complete.")
    return backup_path

def restore_backup(backup_path):
    if not os.path.exists(backup_path):
        print(f"Backup path {backup_path} does not exist.")
        sys.exit(1)

    print(f"Restoring from: {backup_path}")
    
    # Verification prompt
    confirm = input(f"This will OVERWRITE current files in {DIRS_TO_BACKUP}. Are you sure? (y/N): ")
    if confirm.lower() != 'y':
        print("Restore cancelled.")
        return

    for dirname in DIRS_TO_BACKUP:
        src = os.path.join(backup_path, dirname)
        dst = os.path.join(os.getcwd(), dirname)
        
        if os.path.exists(src):
            print(f"  Restoring {dirname}...")
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            print(f"  Warning: {dirname} not found in backup, skipping.")

    print("Restore complete.")

def list_backups():
    if not os.path.exists(BACKUP_ROOT):
        print("No backups found.")
        return

    backups = sorted(os.listdir(BACKUP_ROOT))
    print("Available backups:")
    for b in backups:
        print(f" - {b}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup Manager")
    subparsers = parser.add_subparsers(dest="command")

    backup_parser = subparsers.add_parser("backup", help="Create a new backup")
    backup_parser.add_argument("tag", nargs="?", help="Optional tag for the backup")

    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("backup_folder", help="Name of the backup folder to restore")

    list_parser = subparsers.add_parser("list", help="List available backups")

    args = parser.parse_args()

    if args.command == "backup":
        create_backup(args.tag)
    elif args.command == "restore":
        restore_path = os.path.join(BACKUP_ROOT, args.backup_folder)
        restore_backup(restore_path)
    elif args.command == "list":
        list_backups()
    else:
        parser.print_help()
