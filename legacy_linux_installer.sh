#!/bin/bash

# Set the paths to check
paths_to_check=(~/ ~/Downloads)

# Set the keyword to search for
keyword="hellfire"

# Check if any 7z file with the keyword exists in any of the paths
echo "Searching for 7z files with '$keyword' in ~/ and ~/Downloads..."
for path in "${paths_to_check[@]}"; do
  for file in "$path"/*.7z; do
    if [[ "$file" == *"$keyword"* ]]; then
      file_found=true
      echo "Found 7z file with '$keyword': $file"
      break 2
    fi
  done
done

# If a file is found, check if 7z is installed
if [ "$file_found" = true ]; then
  echo "Checking if 7z is installed..."
  if ! command -v 7z &>/dev/null; then
    # 7z is not installed, try to install p7zip-full
    echo "7z is not installed. Installing p7zip-full..."
    sudo apt-get update && sudo apt-get install -y p7zip-full
    echo "p7zip-full installed successfully."
  else
    echo "7z is already installed."
  fi

  # Create the HellFire directory if it doesn't exist, or clean it if it does
  hellfire_dir=~/HellFire
  echo "Preparing HellFire directory..."
  if [ -d "$hellfire_dir" ]; then
    echo "Cleaning existing HellFire directory..."
    rm -rf "$hellfire_dir"/*
  else
    echo "Creating new HellFire directory..."
    mkdir -p "$hellfire_dir"
  fi

  # Extract the contents of the 7z file to the HellFire directory
  echo "Extracting $file to HellFire directory..."
  7z x -o"$hellfire_dir" "$file"
  echo "Extraction complete."

  # Create a symlink to the firefox binary in /usr/bin/
  firefox_bin="$hellfire_dir/firefox/firefox"
  symlink_target=/usr/bin/hellfire
  if [ -x "$firefox_bin" ]; then
    if [ -L "$symlink_target" ]; then
      echo "Symlink to firefox binary already exists in /usr/bin/. Skipping creation."
    else
      echo "Creating symlink to firefox binary in /usr/bin/..."
      sudo ln -sf "$firefox_bin" "$symlink_target"
      echo "Symlink created. You can now run 'hellfire' in the terminal to open the firefox binary."
    fi
  else
    echo "Firefox binary not found in $hellfire_dir/firefox/. Symlink not created."
  fi

  # Create a desktop shortcut for Hellfire
  desktop_file=~/.local/share/applications/hellfire.desktop
  echo "Creating desktop shortcut for Hellfire..."
  echo "[Desktop Entry]" >> $desktop_file
  echo "Name=HellFire" >> $desktop_file
  echo "Exec=hellfire" >> $desktop_file
  echo "Terminal=false" >> $desktop_file
  echo "Type=Application" >> $desktop_file
  chmod +x $desktop_file
  update-desktop-database ~/.local/share/applications
  echo "Desktop shortcut created. You can now find HellFire in your application menu."
else
  echo "No 7z files with '$keyword' found in ~/ or ~/Downloads."
fi
