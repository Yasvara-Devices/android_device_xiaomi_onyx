#!/vendor/bin/sh
#
# set_charger_poweroff_mode.sh
#
# Ensures charger_partition power_off_mode stays set to 1 (offline charging enabled)
# after charger_partition.ko's charger_partition_prepare() unconditionally resets it to 2.
#
# Ghidra RE Analysis:
#   charger_partition_prepare() at charger_partition.ko writes:
#     *(charger_partition + 0xa8) = 0x200000002  // power_off_mode=2 (upper 32-bit)
#   This happens ~5 seconds after boot when charger_partition_work() finds UFS SCSI device.
#
# Strategy: Write power_off_mode=1 every 5 seconds for 5 iterations (25 seconds total).
# This guarantees at least one write happens AFTER charger_partition_prepare() completes.

SYSFS="/sys/class/xm_power/charger/charger_partition/charger_partition_poweroffmode"

for i in 1 2 3 4 5; do
    sleep 5
    if [ -f "$SYSFS" ]; then
        CURRENT=$(cat "$SYSFS" 2>/dev/null || echo "unreadable")
        echo 1 > "$SYSFS"
        log -t charger_poweroff_mode "Iteration $i: set power_off_mode=1 (was: $CURRENT)"
    else
        log -t charger_poweroff_mode "Iteration $i: sysfs not available yet"
    fi
done

FINAL=$(cat "$SYSFS" 2>/dev/null || echo "N/A")
log -t charger_poweroff_mode "Done. Final power_off_mode=$FINAL"
