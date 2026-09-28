#!/bin/bash
# Installs render-watch on the render box (debof) as a systemd --user service, from plannit on the queueing
# box (debnuc), with that box's farm config (~/.config/plannit/farm.conf: PLANNIT_DIR says where plannit is). On debof:
#   ssh nuc 'cat <plannit on debnuc>/farm/install-debof.sh' > /tmp/t && bash /tmp/t
LOG=/tmp/render-watch-install.log; exec > >(tee "$LOG") 2>&1
set -x
mkdir -p ~/.local/bin ~/.config/systemd/user
ssh nuc 'cat ~/.config/plannit/farm.conf' > ~/.config/render-watch.conf \
  || { echo "!! no ~/.config/plannit/farm.conf on debnuc — copy plannit's farm/farm.conf.example there first"; exit 1; }
. ~/.config/render-watch.conf
FARM="$PLANNIT_DIR/farm"
ssh nuc "cat ~/$FARM/render-watch.sh" > ~/.local/bin/render-watch && chmod +x ~/.local/bin/render-watch
ssh nuc "cat ~/$FARM/render-watch.service" > ~/.config/systemd/user/render-watch.service
bash -n ~/.local/bin/render-watch && bash -n ~/.config/render-watch.conf
# the service runs without your desktop's ssh-agent: the key to debnuc must work on its own
env -u SSH_AUTH_SOCK ssh -o BatchMode=yes -o ConnectTimeout=10 nuc 'echo key-ok' \
  || echo "!! ssh nuc needs the agent/passphrase — the service will not reach debnuc"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || echo "!! no nvidia-smi"
# keep user services running without a login session (asks for your sudo password)
sudo loginctl enable-linger "$USER"
loginctl show-user "$USER" -p Linger
systemctl --user daemon-reload
systemctl --user enable --now render-watch.service
sleep 5
systemctl --user --no-pager status render-watch.service | head -12
journalctl --user -u render-watch --no-pager -n 10
set +x
ssh nuc "cat > ~/from-debof/render-watch-install.log" < "$LOG"
echo "== installed. Logs: journalctl --user -u render-watch -f"
