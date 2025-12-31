#!/usr/bin/env bash

shell_profile="$HOME/.profile"

# ------------------- NVM --------------------------------------------------------

# Might be discovered via zsh plugin instead
has_nvm=$(cat "$shell_profile" | grep 'NVM_DIR="$HOME/.nvm"')
if [ -z "$has_nvm" ]; then
    echo "NVM not found in $shell_profile, installing NVM...";

    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash;
    # wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash;

cat << 'EOF' | tee -a "$HOME/.profile" > /dev/null
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
EOF

else
    echo "NVM already installed in $shell_profile, skipping installation."
fi

# ------------------- BUN --------------------------------------------------------

has_bun=$(cat "$shell_profile" | grep 'PATH="$HOME/.bun/bin:$PATH"')
if [ -z "$has_bun" ]; then
    echo "Bun not found in $shell_profile, installing Bun...";

    curl -fsSL https://bun.com/install | bash;

cat << 'EOF' | tee -a "$HOME/.profile" > /dev/null
if [ -d "$HOME/.bun/bin" ]; then
    export PATH="$HOME/.bun/bin:$PATH"
fi
EOF

else
    echo "Bun already installed in $shell_profile, skipping installation."
fi

# ------------------- PNPM -------------------------------------------------------

has_pnpm=$(cat "$shell_profile" | grep 'PATH="$HOME/.local/share/pnpm:$PATH"')
if [ -z "$has_pnpm" ]; then
    echo "PNPM not found in $shell_profile, installing PNPM...";

    curl -fsSL https://get.pnpm.io/install.sh | sh -;

    ls -ah "$HOME/.local/share/pnpm";

    echo "Adding to PATH -> might need to remove automatic .zshrc, .bashrc entries added by the pnpm install script";

cat << 'EOF' | tee -a "$HOME/.profile" > /dev/null
export PNPM_HOME="$HOME/.local/share/pnpm"
if [ -d "$PNPM_HOME" ]; then
	export PATH="$PNPM_HOME:$PATH"
fi
EOF

else
    echo "PNPM already installed in $shell_profile, skipping installation."
fi

# ------------------- ---- -------------------------------------------------------

source "$shell_profile"