#!/usr/bin/env sh
# For example for installing vscode 'code'

KEY_URL="https://download.docker.com/linux/ubuntu/gpg"
KEY_NAME="docker"
PKGS_SOURCE=https://download.docker.com/linux/ubuntu
INSTALL_PKGS="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"


TEMP_DIR="/dev/shm"
KEYRINGS_DIR="/usr/share/keyrings"
TEMP_KEY_FILE="$TEMP_DIR/$KEY_NAME.gpg"
PROD_KEY_FILE="$KEYRINGS_DIR/$KEY_NAME.gpg"

SRC_LIST_FILE="/etc/apt/sources.list.d/${KEY_NAME}.list"
CURRENT_DEBIAN_CODENAME=$(cat /etc/os-release | grep VERSION_CODENAME | cut -d '=' -f 2)


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
wget -qO- "$KEY_URL" | gpg --dearmor > "$TEMP_KEY_FILE"


if [ -f "$PROD_KEY_FILE" ] && [ -s "$PROD_KEY_FILE" ] ; then
    echo "$PROD_KEY_FILE already exists and is not empty do you want to replace it? (y/n)"
    read -r RESPONSE
    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        echo "Replacing $PROD_KEY_FILE with $TEMP_KEY_FILE"
        sudo install -D -o root -g root -m 644 "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
    fi
else
    echo "Creating keyring at $PROD_KEY_FILE from $TEMP_KEY_FILE"
    sudo install -D -o root -g root -m 644 "$TEMP_KEY_FILE" "$PROD_KEY_FILE"
fi


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
echo "deb [arch=$ARCH signed-by=$PROD_KEY_FILE] $PKGS_SOURCE $CURRENT_DEBIAN_CODENAME stable" | sudo tee "$SRC_LIST_FILE"
#sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
rm -f "$TEMP_KEY_FILE"

sudo apt update

# sudo apt install code
#sudo apt install code

echo "You can now install docker packages with:"
echo "sudo apt install $INSTALL_PKGS"
