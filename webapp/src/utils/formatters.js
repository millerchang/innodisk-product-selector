export function formatTemp(min, max) {
  if (min == null || max == null) return 'N/A';
  return `${min}°C ~ ${max}°C`;
}

export function formatTops(tops, basis) {
  if (tops == null) return 'N/A';
  const tag = basis ? ` (${basis})` : '';
  if (tops >= 1000) return `${(tops / 1000).toFixed(1)}K TOPS${tag}`;
  if (tops >= 100) return `${Math.round(tops)} TOPS${tag}`;
  return `${tops} TOPS${tag}`;
}

export function formatRam(gb) {
  if (gb == null) return 'N/A';
  return `${gb} GB`;
}

export function formatTdp(watt) {
  if (watt == null) return 'N/A';
  return `${watt}W`;
}

export function formatConnectivity(list) {
  if (!list || list.length === 0) return 'N/A';
  return list.join(' · ');
}

export function formatOS(list) {
  if (!list || list.length === 0) return 'N/A';
  return list.join(', ');
}

export function getMatchBadge(partNo, recommendedPartNos) {
  if (!recommendedPartNos || !recommendedPartNos.length) return null;
  const idx = recommendedPartNos.indexOf(partNo);
  if (idx === 0) return { label: 'Best Match', color: 'var(--color-match-best)' };
  if (idx === 1) return { label: 'Strong Match', color: 'var(--color-match-good)' };
  if (idx >= 2 && idx <= 4) return { label: 'Good Match', color: 'var(--color-match-ok)' };
  return null;
}

export function getPlatformIcon(platformBrand) {
  const icons = {
    Intel: '🔵',
    Qualcomm: '🔴',
    NXP: '🟢',
    'AMD-Xilinx': '🟡',
  };
  return icons[platformBrand] || '⚪';
}

export function getProductLineLabel(line) {
  const labels = {
    computing_aiot: 'AIoT BU',
    computing_ipa: 'IPA BU',
    flash: 'Flash Storage',
    dram: 'DRAM',
    camera: 'Camera',
    io: 'I/O Module',
    networking: 'Networking',
    air_sensor: 'Air Sensor',
  };
  return labels[line] || line;
}

export function formatDimensions(dims) {
  if (!dims) return '—';
  const { width_mm, depth_mm, height_mm } = dims;
  if (width_mm == null && depth_mm == null && height_mm == null) return '—';
  const w = width_mm  != null ? width_mm  : '?';
  const d = depth_mm  != null ? depth_mm  : '?';
  const h = height_mm != null ? height_mm : '?';
  return `${w} × ${d} × ${h} mm`;
}

export function getLifecycleStyle(status) {
  if (status === 'EOL') return { color: '#DC2626', label: 'EOL' };
  if (status === 'NRND') return { color: '#D97706', label: 'NRND' };
  if (status === 'Preview') return { color: '#2563EB', label: 'Preview' };
  return { color: '#16A34A', label: 'Active' };
}
