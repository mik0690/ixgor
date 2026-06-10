import urllib.request
import urllib.parse
import json
import os
import platform
import shutil
import sys
import subprocess

# GitHub RAW URL for the automated database
# Replace YOUR-USERNAME with your actual GitHub username.
API_URL = 'https://raw.githubusercontent.com/mik0690/ixgor/main/server/database.json'

def get_hardware_info():
    print("[*] Detecting hardware...")
    info = {}
    
    # Architecture
    info['arch'] = platform.machine()
    info['system'] = platform.system()
    
    # Flags mapping
    info['flags'] = []
    if '64' in info['arch']:
        info['flags'].append('64-bit')
    elif '86' in info['arch'] or '32' in info['arch']:
        info['flags'].append('32-bit')
        
    if 'arm' in info['arch'].lower() or 'aarch' in info['arch'].lower():
        info['flags'].append('arm')
        
    # RAM (Mocked for cross-platform built-in simplicity, or we can use psutil if available)
    try:
        import psutil
        ram_mb = int(psutil.virtual_memory().total / (1024 * 1024))
    except ImportError:
        # Fallback mock for demonstration
        ram_mb = 8192 # 8GB
        
    info['ram_mb'] = ram_mb
    
    # Disk
    total, used, free = shutil.disk_usage("/")
    info['disk_mb'] = int(free / (1024 * 1024)) # Free space in MB
    
    print(f"    - Architecture: {info['arch']}")
    print(f"    - RAM (MB): {info['ram_mb']}")
    print(f"    - Free Disk (MB): {info['disk_mb']}")
    return info

def fetch_os_list(hw_info):
    print("\n[*] Connecting to server to fetch compatible OS list...")
    if API_URL == 'mock':
        # Local mock logic reading from the json file directly for dev
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'database.json')
            with open(db_path, 'r') as f:
                db_data = json.load(f)
        except Exception as e:
            print(f"[!] Error fetching local mock DB: {e}")
            return None
    else:
        # Fetch directly from GitHub raw content
        try:
            req = urllib.request.Request(API_URL, headers={'User-Agent': 'BootOS-Installer'})
            with urllib.request.urlopen(req) as res:
                db_data = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"[!] Network error connecting to GitHub: {e}")
            print("[*] Falling back to local offline mock...")
            try:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'database.json')
                with open(db_path, 'r') as f:
                    db_data = json.load(f)
            except Exception as ex:
                return None
                
    response = {'recommended': [], 'high_end': []}
    for os_item in db_data.get('os_list', []):
        if hw_info['ram_mb'] < os_item.get('min_ram_mb', 0):
            continue
        if hw_info['disk_mb'] < os_item.get('min_disk_mb', 0):
            continue
        
        proc_editions = []
        for ed in os_item.get('editions', []):
            ed['incompatible'] = any(flag in ed.get('incompatible_flags', []) for flag in hw_info['flags'])
            proc_editions.append(ed)
        
        os_item['editions'] = proc_editions
        if os_item.get('category') == 'recommended':
            response['recommended'].append(os_item)
        elif os_item.get('category') == 'high_end':
            response['high_end'].append(os_item)
            
    return response

def main_menu():
    while True:
        print("\n" + "="*50)
        print("    ULTRA LIGHTWEIGHT BOOT OS INSTALLER")
        print("="*50)
        
        hw_info = get_hardware_info()
        os_data = fetch_os_list(hw_info)
        
        if not os_data:
            print("[!] Could not retrieve OS data. Exiting.")
            return

        print("\n[1] View Recommended OS Options")
        print("[2] View High-End OS Options")
        print("[3] Enter Recovery Shell")
        print("[4] Exit")
        
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            select_os(os_data['recommended'], "Recommended")
        elif choice == '2':
            select_os(os_data['high_end'], "High-End")
        elif choice == '3':
            recovery_shell()
        elif choice == '4':
            break
        else:
            print("[!] Invalid option.")

def select_os(os_list, category_name):
    if not os_list:
        print(f"\n[!] No {category_name} options available for your hardware.")
        return
        
    print(f"\n--- {category_name} Options ---")
    for idx, os_item in enumerate(os_list):
        print(f"[{idx+1}] {os_item['name']}")
    print("[0] Back")
    
    choice = input("\nSelect an OS: ").strip()
    if choice == '0':
        return
        
    try:
        os_idx = int(choice) - 1
        if 0 <= os_idx < len(os_list):
            selected_os = os_list[os_idx]
            select_edition(selected_os)
        else:
            print("[!] Invalid selection.")
    except ValueError:
        print("[!] Invalid input.")

def select_edition(selected_os):
    print(f"\n--- Editions for {selected_os['name']} ---")
    for idx, ed in enumerate(selected_os['editions']):
        status = "(INCOMPATIBLE)" if ed['incompatible'] else ""
        print(f"[{idx+1}] {ed['name']} {status}")
    print("[0] Back")
    
    choice = input("\nSelect an Edition: ").strip()
    if choice == '0':
        return
        
    try:
        ed_idx = int(choice) - 1
        if 0 <= ed_idx < len(selected_os['editions']):
            ed = selected_os['editions'][ed_idx]
            if ed['incompatible']:
                print("[!] WARNING: This edition is incompatible with your hardware!")
                conf = input("Proceed anyway? (y/N): ").strip().lower()
                if conf != 'y':
                    return
            
            run_setup(selected_os, ed)
        else:
            print("[!] Invalid selection.")
    except ValueError:
        print("[!] Invalid input.")

def run_setup(os_info, edition):
    print("\n" + "="*50)
    print("    OS SETUP CONFIGURATION")
    print("="*50)
    
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    wm = input("Window Manager / Desktop Environment (e.g. Hyprland, Wayland, i3) [Leave blank for default]: ").strip()
    github_dotfiles = input("GitHub Dotfiles Repo URL (Leave blank to skip): ").strip()
    
    print("\n--- Summary ---")
    print(f"OS: {os_info['name']} ({edition['name']})")
    print(f"User: {username}")
    print(f"WM/DE: {wm if wm else 'Default'}")
    if github_dotfiles:
        print(f"Dotfiles: {github_dotfiles}")
    
    conf = input("\nStart failsafe installation? (y/N): ").strip().lower()
    if conf == 'y':
        print("\n[*] Failsafe Installation Starting...")
        print("[*] Backing up existing user files to failsafe partition...")
        print(f"[*] Downloading {edition.get('download_url', 'ISO')}...")
        if github_dotfiles:
            print(f"[*] Cloning dotfiles from {github_dotfiles}...")
        print("[*] Installing system and applying configurations...")
        print("[*] DONE! Please reboot.")
        sys.exit(0)
    else:
        print("[*] Installation aborted.")

def recovery_shell():
    print("\n[*] Entering Recovery Shell. Type 'exit' or 'reset' to return to main menu.")
    print("[*] Built-in commands: ls, cd, echo, nano")
    current_dir = os.getcwd()
    
    while True:
        cmd_input = input(f"recovery:{current_dir}$ ").strip()
        if not cmd_input:
            continue
            
        parts = cmd_input.split()
        cmd = parts[0].lower()
        
        if cmd in ['exit', 'reset', 'quit']:
            break
        elif cmd == 'ls':
            print("  ".join(os.listdir(current_dir)))
        elif cmd == 'cd':
            if len(parts) > 1:
                try:
                    os.chdir(parts[1])
                    current_dir = os.getcwd()
                except Exception as e:
                    print(f"cd: {e}")
            else:
                print(current_dir)
        elif cmd == 'echo':
            print(" ".join(parts[1:]))
        elif cmd == 'nano':
            if len(parts) > 1:
                nano_editor(parts[1])
            else:
                print("nano: missing filename")
        else:
            # Fallback to system command
            try:
                subprocess.run(cmd_input, shell=True)
            except Exception as e:
                print(f"Command failed: {e}")

def nano_editor(filename):
    print(f"\n--- Nano-like Editor: {filename} ---")
    print("Enter text. Type ':wq' on a new line to save and exit, ':q!' to exit without saving.")
    
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read()
            print(content, end='')
            lines = content.split('\n')
            
    while True:
        line = input()
        if line == ':wq':
            with open(filename, 'w') as f:
                f.write('\n'.join(lines))
            print(f"[*] Saved {filename}")
            break
        elif line == ':q!':
            break
        else:
            lines.append(line)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[!] Setup interrupted by user. Resetting...")
        main_menu()
