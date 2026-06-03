import subprocess
print("Fetching...")
subprocess.run(["python3", "-m", "kiboy", "fetch"])
print("Deduping...")
subprocess.run(["python3", "-m", "kiboy", "dedup"])
print("Pipeling...")
subprocess.run(["python3", "-m", "kiboy", "pipeline"])
print("Generating thumbnails...")
subprocess.run(["python3", "-m", "kiboy", "thumbnail", "--pending"])
