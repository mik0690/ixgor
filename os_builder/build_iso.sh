#!/bin/bash
# Run this script inside your Debian VM as root to generate the BootOS.iso
# It uses Alpine Linux as an ultra-lightweight base.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. sudo ./build_iso.sh)"
  exit 1
fi

echo "[*] Installing required packages..."
apt-get update
apt-get install -y wget xorriso syslinux syslinux-utils isolinux squashfs-tools cpio gzip

WORKDIR="/tmp/os_build"
ROOTFS="$WORKDIR/rootfs"
ISODIR="$WORKDIR/iso"

rm -rf "$WORKDIR"
mkdir -p "$ROOTFS" "$ISODIR/boot/syslinux"

echo "[*] Downloading Alpine Mini Rootfs..."
# Get latest alpine minirootfs for x86_64
ALPINE_TAR="alpine-minirootfs-3.19.1-x86_64.tar.gz"
wget -q "https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/$ALPINE_TAR" -O "$WORKDIR/$ALPINE_TAR"

echo "[*] Extracting Rootfs..."
tar -xzf "$WORKDIR/$ALPINE_TAR" -C "$ROOTFS"

echo "[*] Installing Python and configuring the installer..."
# We need to mount proc, sys, dev to chroot properly
mount -t proc none "$ROOTFS/proc"
mount -o bind /sys "$ROOTFS/sys"
mount -o bind /dev "$ROOTFS/dev"

# Setup DNS in chroot
cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf"

# Run commands inside the Alpine chroot
chroot "$ROOTFS" /bin/sh -c "apk update && apk add python3 parted e2fsprogs bash nano util-linux"

# Copy our installer script
cp ../installer/main.py "$ROOTFS/usr/local/bin/bootos_installer.py"
chmod +x "$ROOTFS/usr/local/bin/bootos_installer.py"

# Configure init to run our script on boot
cat << 'EOF' > "$ROOTFS/etc/inittab"
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default
tty1::respawn:/usr/bin/python3 /usr/local/bin/bootos_installer.py
tty2::respawn:/sbin/getty 38400 tty2
tty3::respawn:/sbin/getty 38400 tty3
::ctrlaltdel:/sbin/reboot
::shutdown:/sbin/openrc shutdown
EOF

# Clean up chroot
rm "$ROOTFS/etc/resolv.conf"
umount "$ROOTFS/proc"
umount "$ROOTFS/sys"
umount "$ROOTFS/dev"

echo "[*] Building Initramfs..."
cd "$ROOTFS"
find . -print0 | cpio --null -ov --format=newc | gzip -9 > "$ISODIR/boot/initramfs.gz"

echo "[*] Downloading Alpine Kernel..."
# We can extract the kernel from the rootfs (Alpine provides linux-virt or linux-lts)
mount -t proc none "$ROOTFS/proc"
chroot "$ROOTFS" /bin/sh -c "apk add linux-lts"
cp "$ROOTFS/boot/vmlinuz-lts" "$ISODIR/boot/vmlinuz"
umount "$ROOTFS/proc"

echo "[*] Configuring Syslinux Bootloader..."
cp /usr/lib/ISOLINUX/isolinux.bin "$ISODIR/boot/syslinux/"
cp /usr/lib/syslinux/modules/bios/ldlinux.c32 "$ISODIR/boot/syslinux/"

cat << 'EOF' > "$ISODIR/boot/syslinux/syslinux.cfg"
DEFAULT bootos
LABEL bootos
  KERNEL /boot/vmlinuz
  APPEND initrd=/boot/initramfs.gz root=/dev/ram0 rw quiet
EOF

echo "[*] Generating ISO..."
cd "$WORKDIR"
xorriso -as mkisofs \
  -o "/tmp/BootOS.iso" \
  -b boot/syslinux/isolinux.bin \
  -c boot/syslinux/boot.cat \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  "$ISODIR"

echo "[+] Success! ISO generated at: /tmp/BootOS.iso"
cp "/tmp/BootOS.iso" "$(pwd)/../BootOS.iso"
echo "[+] Copied to $(pwd)/../BootOS.iso"
