#!/usr/bin/env sh

# https://support.mozilla.org/en-US/kb/install-firefox-linux

KEY_URL="https://packages.mozilla.org/apt/repo-signing-key.gpg"
KEY_NAME="packages.mozilla.org"
PKGS_SOURCE=https://packages.mozilla.org/apt
#INSTALL_PKGS="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"


TEMP_DIR="/dev/shm"
KEYRINGS_DIR="/usr/share/keyrings"
TEMP_KEY_FILE="$TEMP_DIR/$KEY_NAME.asc"
PROD_KEY_FILE="$KEYRINGS_DIR/$KEY_NAME.asc"

SRC_LIST_FILE="/etc/apt/sources.list.d/${KEY_NAME}.list"
# CURRENT_DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d '=' -f 2)


install_if_missing() {
    PKG_NAME=$1
    IS_INSTALLED=$(apt list --installed | grep "^$PKG_NAME/")

    if [ -n "$IS_INSTALLED" ] ; then
        echo "$PKG_NAME already installed"
    else
        echo "installing $PKG_NAME"
        sudo apt update
        sudo apt install -y "$PKG_NAME"
    fi
}

install_if_missing wget
install_if_missing gpg
install_if_missing apt-transport-https

echo "Downloading $KEY_NAME GPG key from $KEY_URL to $TEMP_KEY_FILE"
wget -qO- "$KEY_URL" > "$TEMP_KEY_FILE"


if [ -f "$PROD_KEY_FILE" ] && [ -s "$PROD_KEY_FILE" ] ; then
    echo "$PROD_KEY_FILE already exists and is not empty do you want to replace it? (y/n)"
    read -r RESPONSE
    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        echo "Replacing $PROD_KEY_FILE with $TEMP_KEY_FILE"
        # sudo install -D -o root -g root -m 644 "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
        sudo cp "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
    fi
else
    echo "Creating keyring at $PROD_KEY_FILE from $TEMP_KEY_FILE"
    # sudo install -D -o root -g root -m 644 "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
    sudo cp "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
fi

FINGERPRINT=$(gpg -n -q --import --import-options import-show "$PROD_KEY_FILE" 2> /dev/null | grep -Eo "[A-Z0-9]{30,}")
if [ "$FINGERPRINT" != "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3" ] ; then
    echo "Fingerprint mismatch for Mozilla keyring! Expected 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 but got $FINGERPRINT"
    echo "Exiting to avoid potential security issues."
    sudo rm -f "$PROD_KEY_FILE"
    exit 1
fi

echo "Mozilla GPG key fingerprint verified. = $FINGERPRINT"

if [ -f "$SRC_LIST_FILE" ] && [ -s "$SRC_LIST_FILE" ] ; then
    echo "$SRC_LIST_FILE already exists and is not empty do you want to replace it? (y/n)"
    read -r RESPONSE
    if [ "$RESPONSE" != "y" ] && [ "$RESPONSE" != "Y" ] ; then
        echo "Not replacing $SRC_LIST_FILE -> exiting"
        sudo rm -f "$TEMP_KEY_FILE"
        exit 0
    fi
fi


ARCH="$(dpkg --print-architecture)"
# ARCH="amd64,arm64,armhf,i386"
# Note 32bit programs currently not enabled for package source (hence only amd64, arm64, armhf and not i386)

echo "Creating source list file at $SRC_LIST_FILE"
echo "deb [arch=$ARCH signed-by=$PROD_KEY_FILE] $PKGS_SOURCE mozilla main" | sudo tee "$SRC_LIST_FILE"
rm -f "$TEMP_KEY_FILE"

echo "Prioritizing Mozilla packages in apt preferences"

echo '
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000
' | sudo tee /etc/apt/preferences.d/mozilla 

sudo apt update

echo "Do you want to install Firefox Developer Edition? (y/n)"
read -r RESPONSE_DE
if [ "$RESPONSE_DE" = "y" ] || [ "$RESPONSE_DE" = "Y" ]; then
    sudo apt install firefox-devedition
fi

echo "Do you want to install Firefox Native? (y/n)"
read -r RESPONSE_NA
if [ "$RESPONSE_NA" = "y" ] || [ "$RESPONSE_NA" = "Y" ]; then
    sudo apt install firefox
fi