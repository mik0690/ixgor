import urllib.request
import re
import json
import os

print("[*] Fetching all OS list from DistroWatch...")
url = "https://distrowatch.com/index.php?dataspan=1"

# Using standard browser headers to avoid basic 403 blocks
req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='ignore')
except Exception as e:
    print(f"[!] Failed to fetch DistroWatch: {e}")
    exit(1)

# Basic regex to extract distributions from the Page Hit Ranking table
# DistroWatch ranking table usually has links like: <a href="mint">Mint</a>
pattern = re.compile(r'<td class="phr2"><a href="([^"]+)">(.*?)</a></td>')
matches = pattern.findall(html)

if not matches:
    print("[!] Regex failed to find OS list. DistroWatch HTML might have changed.")
    exit(1)

print(f"[*] Found {len(matches)} distributions! Generating database.json...")

os_list = []
for idx, (href, name) in enumerate(matches):
    # Determine category based on rank (1-20 recommended, rest high_end or standard)
    category = "recommended" if idx < 20 else "high_end"
    
    # We set default minimum specs since DistroWatch doesn't expose them in the table
    # Lighter distros get lower defaults
    lower_name = name.lower()
    if any(lite in lower_name for lite in ['puppy', 'alpine', 'tiny', 'lubuntu', 'xfce', 'lite']):
        min_ram = 512
        min_disk = 5000
    else:
        min_ram = 2048
        min_disk = 15000

    os_entry = {
        "id": href.lower(),
        "name": name,
        "category": category,
        "min_ram_mb": min_ram,
        "min_disk_mb": min_disk,
        "editions": [
            {
                "name": "Standard Edition",
                "download_url": f"https://distrowatch.com/{href}", # DistroWatch page link as fallback
                "incompatible_flags": []
            }
        ]
    }
    os_list.append(os_entry)

db_path = os.path.join(os.path.dirname(__file__), 'database.json')

with open(db_path, 'w') as f:
    json.dump({"os_list": os_list}, f, indent=4)

print(f"[+] Successfully wrote {len(matches)} OS entries to database.json!")
