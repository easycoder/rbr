#!/bin/bash
# Deploy RBR Chat to Hetzner server
# Shared files come from the chat project; instance config is local.

SERVER="root@89.167.127.185"
REMOTE_DIR="/root/rbrchat"
LOCAL_DIR="$(dirname "$0")"
CHAT_DIR="$HOME/dev/chat"

echo "=== Deploying RBR Chat to $SERVER ==="

# Create remote directory
echo "Creating remote directory..."
ssh $SERVER "mkdir -p $REMOTE_DIR/chat-data/topics"

# Copy shared files from chat project
echo "Copying shared files..."
scp "$CHAT_DIR/chat-server.py" \
    "$CHAT_DIR/chat-main.ecs" \
    "$CHAT_DIR/chat.json" \
    "$CHAT_DIR/index.html" \
    "$SERVER:$REMOTE_DIR/"

# Copy instance-specific files
echo "Copying instance config..."
scp "$LOCAL_DIR/chat-config.json" \
    "$LOCAL_DIR/chat-users.json" \
    "$LOCAL_DIR/credentials.json" \
    "$SERVER:$REMOTE_DIR/"

# Install systemd service
echo "Installing systemd service..."
scp "$LOCAL_DIR/rbrchat.service" "$SERVER:/etc/systemd/system/"
ssh $SERVER "ufw allow 8081 2>/dev/null; systemctl daemon-reload && systemctl enable rbrchat && systemctl restart rbrchat"

# Check status
echo ""
echo "=== Service status ==="
ssh $SERVER "systemctl status rbrchat --no-pager -l"

echo ""
echo "=== Done ==="
echo "Chat should be available at: http://89.167.127.185:8081/rbrchat/"
