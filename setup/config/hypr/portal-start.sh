#!/bin/bash
sleep 2
killall -q xdg-desktop-portal xdg-desktop-portal-hyprland
/usr/lib/xdg-desktop-portal-hyprland &
sleep 2
/usr/lib/xdg-desktop-portal &
