#!/bin/bash
# Install or remove a policy-override data vault for thermald (≥ 2.5.12).
# Run as root (pkexec).
#   vault-override.sh install /path/to/vault.bin   # thermald loads this instead of the firmware GDDV
#   vault-override.sh remove                        # back to the firmware vault
# The file name is derived from DMI strings exactly as thermald does
# (crc32 of sys_vendor, product_family, product_name, product_sku).
set -eu
crc32() { python3 -c '
import sys
crc=0
for b in sys.argv[1].encode():
    crc^=b
    for _ in range(8): crc=(crc>>1)^(0xedb88320 if crc&1 else 0)
print(crc)' "$1"; }
dmi() { head -n1 "/sys/class/dmi/id/$1" 2>/dev/null || true; }
NAME="/lib/firmware/intel/dtt/dtt_data_vault_$(crc32 "$(dmi sys_vendor)")_$(crc32 "$(dmi product_family)")_$(crc32 "$(dmi product_name)")_$(crc32 "$(dmi product_sku)").bin"
FEATURES=/etc/thermald/thermald-features.xml
case "${1:-}" in
  install)
    SRC=${2:?vault file}
    [ "$(stat -c %s "$SRC")" -le 4096 ] || { echo "vault larger than thermald's 4 KiB limit"; exit 1; }
    install -d /lib/firmware/intel/dtt
    install -m 0644 -o root -g root "$SRC" "$NAME"
    if [ ! -f $FEATURES ]; then
      cat > $FEATURES <<'EOF'
<ThermaldFeatures>
	<DbusControl> 0 </DbusControl>
	<XMLThermalConfig> 1 </XMLThermalConfig>
	<DataVaultFromFileSystem> 1 </DataVaultFromFileSystem>
	<KobjectUeventSupport> 1 </KobjectUeventSupport>
</ThermaldFeatures>
EOF
    fi
    echo "installed $NAME"
    ;;
  remove)
    rm -f "$NAME"
    echo "removed $NAME (features file left in place)"
    ;;
  *) echo "usage: $0 install VAULT.bin | remove"; exit 2 ;;
esac
systemctl restart thermald
sleep 8
LOG=$(journalctl -u thermald -b --no-pager -o cat --since -10s)
echo "$LOG" | grep -E "Loading data vault|Look for File|GDDV|adaptive|Condition Set matched" | tail -6
# A vault thermald cannot parse makes it drop --adaptive and run its generic engine
# (no DTT policy, MSR PL1 stepping, no_turbo toggling). Never leave that in place.
if echo "$LOG" | grep -q "Ignoring --adaptive option"; then
  echo "thermald rejected the vault and fell back to the non-adaptive engine" >&2
  if [ "${1:-}" = install ]; then
    rm -f "$NAME"; systemctl restart thermald
    echo "override removed again; firmware vault active" >&2
  fi
  exit 1
fi
