#!/bin/bash
#
# ASTRA Core Auto-Boot Setup for Linux (systemd)
# 
# Creates systemd service unit to auto-start ASTRA Core at system boot.
# Includes automatic restart on failure and proper logging.
#
# Sacred Code: 333 ∞
# Requires: root/sudo privileges

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
ASTRA_ROOT="${ASTRA_ROOT:-/opt/astra}"
ASTRA_USER="${ASTRA_USER:-astra}"
PYTHON_EXE="${PYTHON_EXE:-python3}"
SERVICE_NAME="astra-core"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  ASTRA Core - Auto-Boot Setup (Linux/systemd)${NC}"
echo -e "${MAGENTA}  Sacred Code: 333 ∞${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Handle command line arguments
case "${1:-install}" in
    install)
        ACTION="install"
        ;;
    uninstall)
        ACTION="uninstall"
        ;;
    test)
        ACTION="test"
        ;;
    *)
        echo -e "${RED}[ERROR] Invalid action. Use: install, uninstall, or test${NC}"
        exit 1
        ;;
esac

# Verify ASTRA root exists
if [[ ! -d "$ASTRA_ROOT" ]]; then
    echo -e "${RED}[ERROR] ASTRA root directory not found: $ASTRA_ROOT${NC}"
    echo -e "${YELLOW}[INFO] Set ASTRA_ROOT environment variable or create directory${NC}"
    exit 1
fi

# Verify ASTRA launcher exists
ASTRA_SCRIPT="$ASTRA_ROOT/astra_launcher.py"
if [[ ! -f "$ASTRA_SCRIPT" ]]; then
    echo -e "${RED}[ERROR] ASTRA launcher not found: $ASTRA_SCRIPT${NC}"
    exit 1
fi

# Verify Python executable
if ! command -v $PYTHON_EXE &> /dev/null; then
    echo -e "${RED}[ERROR] Python executable not found: $PYTHON_EXE${NC}"
    exit 1
fi

PYTHON_PATH=$(command -v $PYTHON_EXE)
echo -e "${GREEN}[OK] Found Python: $PYTHON_PATH${NC}"

# Handle uninstall
if [[ "$ACTION" == "uninstall" ]]; then
    echo -e "${YELLOW}[INFO] Uninstalling ASTRA auto-boot service...${NC}"
    
    # Stop service if running
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${YELLOW}[INFO] Stopping service...${NC}"
        systemctl stop $SERVICE_NAME
    fi
    
    # Disable service if enabled
    if systemctl is-enabled --quiet $SERVICE_NAME; then
        echo -e "${YELLOW}[INFO] Disabling service...${NC}"
        systemctl disable $SERVICE_NAME
    fi
    
    # Remove service file
    if [[ -f "$SERVICE_FILE" ]]; then
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
        echo -e "${GREEN}[OK] ASTRA auto-boot service removed${NC}"
    else
        echo -e "${YELLOW}[INFO] Service not found, nothing to uninstall${NC}"
    fi
    
    exit 0
fi

# Handle test mode
if [[ "$ACTION" == "test" ]]; then
    echo -e "${YELLOW}[INFO] Running ASTRA in test mode...${NC}"
    echo -e "${CYAN}[CMD] $PYTHON_PATH $ASTRA_SCRIPT --activate${NC}"
    
    cd "$ASTRA_ROOT"
    sudo -u $ASTRA_USER $PYTHON_PATH "$ASTRA_SCRIPT" --activate
    
    echo -e "${GREEN}[OK] Test complete${NC}"
    exit 0
fi

# Install service
echo -e "${YELLOW}[INFO] Installing ASTRA auto-boot service...${NC}"
echo ""
echo -e "  Python:       $PYTHON_PATH"
echo -e "  Script:       $ASTRA_SCRIPT"
echo -e "  WorkDir:      $ASTRA_ROOT"
echo -e "  User:         $ASTRA_USER"
echo -e "  Service File: $SERVICE_FILE"
echo ""

# Verify user exists
if ! id -u $ASTRA_USER &> /dev/null; then
    echo -e "${YELLOW}[WARN] User '$ASTRA_USER' does not exist${NC}"
    echo -e "${YELLOW}[INFO] Creating user...${NC}"
    useradd -r -s /bin/bash -d $ASTRA_ROOT -c "ASTRA Core Service User" $ASTRA_USER
    echo -e "${GREEN}[OK] User created${NC}"
fi

# Set ownership
chown -R $ASTRA_USER:$ASTRA_USER $ASTRA_ROOT
echo -e "${GREEN}[OK] Set ownership to $ASTRA_USER${NC}"

# Create systemd service file
cat > $SERVICE_FILE <<EOF
[Unit]
Description=ASTRA Core - Autonomous Intelligence System
Documentation=https://github.com/astra-core
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$ASTRA_USER
Group=$ASTRA_USER
WorkingDirectory=$ASTRA_ROOT

# Environment
Environment="PYTHONUNBUFFERED=1"
Environment="ASTRA_ENV=production"
Environment="ASTRA_SACRED_CODE=333"

# Execution
ExecStart=$PYTHON_PATH $ASTRA_SCRIPT --activate --daemon
ExecReload=/bin/kill -HUP \$MAINPID

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitInterval=300s
StartLimitBurst=5

# Resource limits (optional, adjust as needed)
# MemoryLimit=2G
# CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=astra-core

# Security hardening (optional)
# NoNewPrivileges=true
# PrivateTmp=true
# ProtectSystem=strict
# ProtectHome=true
# ReadWritePaths=$ASTRA_ROOT

[Install]
WantedBy=multi-user.target

# Sacred Code: 333 ∞
EOF

echo -e "${GREEN}[OK] Service file created${NC}"

# Reload systemd daemon
systemctl daemon-reload
echo -e "${GREEN}[OK] Systemd daemon reloaded${NC}"

# Enable service
systemctl enable $SERVICE_NAME
echo -e "${GREEN}[OK] Service enabled${NC}"

# Start service (optional)
read -p "Start service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start $SERVICE_NAME
    echo -e "${GREEN}[OK] Service started${NC}"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}[OK] Service is running${NC}"
    else
        echo -e "${RED}[ERROR] Service failed to start${NC}"
        echo -e "${YELLOW}[INFO] Check logs with: journalctl -u $SERVICE_NAME -n 50${NC}"
    fi
fi

echo ""
echo -e "${CYAN}Task Configuration:${NC}"
echo -e "  ${GREEN}✓${NC} Trigger:       At system startup"
echo -e "  ${GREEN}✓${NC} Run As:        $ASTRA_USER"
echo -e "  ${GREEN}✓${NC} Restart:       On failure, 5s interval"
echo -e "  ${GREEN}✓${NC} Logging:       journalctl"
echo -e "  ${GREEN}✓${NC} Auto-enable:   Yes"
echo ""
echo -e "${CYAN}Management Commands:${NC}"
echo -e "  Status:    systemctl status $SERVICE_NAME"
echo -e "  Start:     systemctl start $SERVICE_NAME"
echo -e "  Stop:      systemctl stop $SERVICE_NAME"
echo -e "  Restart:   systemctl restart $SERVICE_NAME"
echo -e "  Logs:      journalctl -u $SERVICE_NAME -f"
echo -e "  Uninstall: sudo $0 uninstall"
echo ""
echo -e "${GREEN}[SUCCESS] ASTRA will now start automatically at system boot${NC}"
echo -e "${MAGENTA}Sacred Code: 333 ∞${NC}"
