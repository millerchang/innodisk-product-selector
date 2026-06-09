import { useEffect } from 'react';
import {
  formatTemp, formatTops, formatRam, formatTdp, formatOS,
  getPlatformIcon, getProductLineLabel, getLifecycleStyle,
} from '../utils/formatters';

/**
 * Convert stored interface string to display format.
 * "PCIe x4 Gen4" → "PCIe Gen4x4"
 * "PCIe x1 Gen3" → "PCIe Gen3x1"
 * "SATA"         → "SATA"
 */
function fmtIface(raw) {
  // Match "PCIe xN GenM" or "PCIe xN" patterns
  const full = raw.match(/^PCIe\s+x(\d+)\s+Gen(\d+)$/i);
  if (full) return `PCIe Gen${full[2]}x${full[1]}`;
  const noGen = raw.match(/^PCIe\s+x(\d+)$/i);
  if (noGen) return `PCIe x${noGen[1]}`;
  return raw; // SATA, USB3.0, etc. — return as-is
}

/** Format a single m2_slot as "N × PCIe Gen4x4 co-lay SATA" */
function formatM2Interface(slot) {
  const ifaces = slot.interface || [];
  if (ifaces.length === 0) return `${slot.count} ×  —`;
  const [primary, ...rest] = ifaces.map(fmtIface);
  const suffix = rest.length > 0 ? ` co-lay ${rest.join(' / ')}` : '';
  return `${slot.count} × ${primary}${suffix}`;
}

export default function ProductDetailModal({ product, onClose }) {
  // Close on Escape + lock body scroll while open
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handler);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const m = product.meta;
  const co = product.common || {};
  const cs = product.computing_spec || {};
  const lifecycle = getLifecycleStyle(co.lifecycle_status);
  const isComputing = ['computing_aiot', 'computing_ipa'].includes(m.product_line);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="platform-icon" style={{ fontSize: '1.6rem' }}>
              {isComputing ? getPlatformIcon(cs.platform_brand) : '🧩'}
            </span>
            <div>
              <h2 className="modal-part-no">{m.part_no}</h2>
              <div className="card-tags" style={{ marginTop: 4 }}>
                <span className="tag tag-bu">{getProductLineLabel(m.product_line)}</span>
                <span className="tag" style={{ color: lifecycle.color, borderColor: lifecycle.color }}>
                  {lifecycle.label}
                </span>
                {m.bu_owner && <span className="tag">{m.bu_owner} BU</span>}
              </div>
            </div>
          </div>
          <button className="modal-close" onClick={onClose} title="Close">✕</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {isComputing
            ? <ComputingDetail cs={cs} co={co} />
            : <EpDetail product={product} co={co} />}

          {/* Certs */}
          {co.certifications?.length > 0 && (
            <Section title="Certifications">
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {co.certifications.map(c => <span key={c} className="cert-chip">{c}</span>)}
              </div>
            </Section>
          )}

          {/* Lifecycle warnings */}
          {co.lifecycle_status === 'NRND' && (
            <div className="nrnd-warning">⚠ Not Recommended for New Designs</div>
          )}
          {co.lifecycle_status === 'Preview' && (
            <div className="preview-note">🆕 Preview — new product, preliminary datasheet</div>
          )}

          {/* Source file */}
          {m.source_file && (
            <p className="modal-source">📄 Source: {m.source_file}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Computing detail ─────────────────────────────────── */
function ComputingDetail({ cs, co }) {
  const mem = cs.memory_spec || {};
  const ports = cs.io_ports || {};

  return (
    <>
      {/* Processor */}
      <Section title="Processor">
        <Row label="Model">{cs.processor_model || '—'}</Row>
        {cs.processor_series && <Row label="Series">{cs.processor_series}</Row>}
        {cs.platform_brand && <Row label="Platform">{cs.platform_brand}</Row>}
        {cs.cpu_cores != null && (
          <Row label="CPU Cores">
            {cs.cpu_cores} cores
            {cs.cpu_p_cores != null && ` (${cs.cpu_p_cores}P + ${cs.cpu_e_cores}E)`}
          </Row>
        )}
        {cs.form_factor && <Row label="Form Factor">{cs.form_factor}</Row>}
      </Section>

      {/* Performance */}
      <Section title="Performance">
        <Row label="AI TOPS">{formatTops(cs.ai_tops)}{cs.ai_tops_dense != null ? ` Sparse / ${cs.ai_tops_dense} TOPS Dense` : ''}</Row>
        <Row label="TDP">{formatTdp(cs.tdp_watt)}</Row>
        <Row label="Op Temp">{formatTemp(co.op_temp_min_c, co.op_temp_max_c)}</Row>
        {co.temp_grade && <Row label="Temp Grade">{co.temp_grade}</Row>}
      </Section>

      {/* Memory */}
      <Section title="Memory">
        <Row label="Capacity">{formatRam(cs.ram_gb)}</Row>
        {mem.type && <Row label="Type">{mem.type}{mem.speed_mhz ? ` ${mem.speed_mhz} MHz` : ''}</Row>}
        {mem.form_factor && <Row label="Form Factor">{mem.form_factor}</Row>}
        {mem.slots != null && <Row label="Slots">{mem.slots === 0 ? 'On-board (fixed)' : mem.slots}</Row>}
        {mem.ecc_support && <Row label="ECC">Yes</Row>}
      </Section>

      {/* System */}
      <Section title="System">
        <Row label="OS">{formatOS(cs.os_support)}</Row>
        {cs.sdk?.length > 0 && <Row label="SDK">{cs.sdk.join(', ')}</Row>}
        {cs.power_input && <Row label="Power Input">{cs.power_input}</Row>}
        {cs.dimensions && (cs.dimensions.width_mm || cs.dimensions.depth_mm) && (
          <Row label="Dimensions">
            {[cs.dimensions.width_mm, cs.dimensions.depth_mm, cs.dimensions.height_mm]
              .filter(Boolean).join(' × ')} mm
          </Row>
        )}
      </Section>

      {/* I/O Ports */}
      <Section title="I/O Ports">
        {/* USB — 方案 A：label 含總數，value 列各規格明細 */}
        {(ports.usb?.length > 0) && (() => {
          const total = ports.usb.reduce((s, u) => s + u.count, 0);
          const detail = ports.usb
            .map(u => u.connector ? `${u.count}× ${u.standard} (${u.connector})` : `${u.count}× ${u.standard}`)
            .join(', ');
          return <Row label={`USB (×${total})`}>{detail}</Row>;
        })()}
        {/* Ethernet — speed 移進 value，PoE / chip 補充顯示 */}
        {ports.gbe?.map((g, i) => (
          <Row key={i} label="Ethernet">
            {g.count}× {g.speed_gbps >= 1 ? `${g.speed_gbps}GbE` : `${g.speed_gbps * 1000}M`}
            {g.poe_support ? ' PoE' : ''}
            {g.chip ? ` (${g.chip})` : ''}
          </Row>
        ))}
        {/* Serial — 標準名直接作 label */}
        {ports.serial?.map((s, i) => (
          <Row key={i} label={s.standard}>{s.count}×{s.note ? ` — ${s.note}` : ''}</Row>
        ))}
        {ports.can_bus_count != null && <Row label="CAN Bus">{ports.can_bus_count}×</Row>}
        {ports.gpio_pins != null && <Row label="GPIO">{ports.gpio_pins} pins</Row>}
        {ports.sim_slot_count != null && <Row label="SIM Slot">{ports.sim_slot_count}×</Row>}
        {ports.mipi_csi?.map((mi, i) => (
          <Row key={i} label="MIPI CSI-2">{mi.count}× {mi.lanes}-lane {mi.note ? `(${mi.note})` : ''}</Row>
        ))}
        {cs.display_outputs?.length > 0 && (
          <Row label="Display">
            {(() => {
              const counts = {};
              cs.display_outputs.forEach(d => counts[d] = (counts[d] || 0) + 1);
              return Object.entries(counts).map(([t, n]) => `${n}× ${t}`).join(', ');
            })()}
          </Row>
        )}
        {ports.audio && (ports.audio.line_out || ports.audio.mic_in || ports.audio.spk_out) && (
          <Row label={ports.audio.chip ? `Audio (${ports.audio.chip})` : 'Audio'}>
            {[
              ports.audio.line_out && 'Line-out',
              ports.audio.mic_in && 'Mic-in',
              ports.audio.spk_out && 'Speaker-out',
            ].filter(Boolean).join(', ')}
          </Row>
        )}
      </Section>

      {/* Expansion */}
      {(cs.m2_slots?.length > 0 || cs.pcie_slots?.length > 0) && (
        <Section title="Expansion">
          {cs.pcie_slots?.map((slot, i) => (
            <Row key={i} label={`PCIe slot`}>
              {slot.count} × PCIe Gen{slot.gen || '?'}{slot.width}{slot.note ? ` (${slot.note})` : ''}
            </Row>
          ))}
          {cs.m2_slots?.map((slot, i) => (
            <Row key={i} label={`M.2 ${slot.size} ${slot.key}-Key`}>
              {formatM2Interface(slot)}
            </Row>
          ))}
          {cs.storage_interfaces?.length > 0 && (
            <Row label="Storage I/F">{cs.storage_interfaces.join(', ')}</Row>
          )}
        </Section>
      )}
    </>
  );
}

/* ── EP / Camera detail ───────────────────────────────── */
function EpDetail({ product, co }) {
  const line = product.meta.product_line;
  const spec = product.networking_spec || product.io_spec || product.air_sensor_spec || product.camera_spec || {};

  return (
    <Section title="Specifications">
      {spec.subcategory && <Row label="Type">{spec.subcategory}</Row>}
      {spec.host_interface && <Row label="Host Interface">{spec.host_interface}</Row>}
      {spec.pcie_gen && <Row label="PCIe">Gen{spec.pcie_gen}{spec.pcie_lanes ? ` x${spec.pcie_lanes}` : ''}</Row>}
      {spec.port_count != null && (
        <Row label="Ports">{spec.port_count}{spec.port_type?.length ? ` (${spec.port_type.join(', ')})` : ''}</Row>
      )}
      {spec.speed_gbps != null && <Row label="Speed">{spec.speed_gbps} Gbps</Row>}
      {spec.protocol?.length > 0 && <Row label="Protocol">{spec.protocol.join(', ')}</Row>}
      {spec.poe_watt != null && <Row label="PoE Power">{spec.poe_watt} W</Row>}
      {spec.can_fd_support != null && <Row label="CAN FD">{spec.can_fd_support ? 'Yes' : 'No'}</Row>}
      {spec.isolation != null && <Row label="Isolation">{spec.isolation ? 'Yes' : 'No'}</Row>}

      {/* Camera specific */}
      {spec.interface_bus && <Row label="Interface">{spec.interface_bus}</Row>}
      {spec.resolution_mp != null && (
        <Row label="Resolution">{spec.resolution_mp} MP{spec.resolution_px ? ` (${spec.resolution_px})` : ''}</Row>
      )}
      {spec.fps != null && <Row label="Frame Rate">{spec.fps} fps</Row>}
      {spec.sensor_type && <Row label="Sensor">{spec.sensor_type}{spec.sensor_size ? ` ${spec.sensor_size}` : ''}</Row>}
      {spec.lens_fov_deg != null && <Row label="FOV">{spec.lens_fov_deg}°</Row>}
      {spec.hdr && <Row label="HDR">Yes</Row>}
      {spec.low_light && <Row label="Low Light">Yes</Row>}
      {spec.ir_filter && <Row label="IR Filter">Yes</Row>}
      {spec.adapter_board_compatible?.length > 0 && (
        <Row label="Compatible">{spec.adapter_board_compatible.join(', ')}</Row>
      )}

      {/* Air sensor */}
      {spec.detected_pollutants?.length > 0 && (
        <Row label="Detects">{spec.detected_pollutants.join(', ')}</Row>
      )}

      {/* Common */}
      {(co.op_temp_min_c != null || co.op_temp_max_c != null) && (
        <Row label="Op Temp">{formatTemp(co.op_temp_min_c, co.op_temp_max_c)}</Row>
      )}
    </Section>
  );
}

/* ── Helpers ─────────────────────────────────────────── */
function Section({ title, children }) {
  return (
    <div className="modal-section">
      <h4 className="modal-section-title">{title}</h4>
      <div className="modal-rows">{children}</div>
    </div>
  );
}

function Row({ label, children }) {
  if (!children && children !== 0) return null;
  return (
    <div className="modal-row">
      <span className="modal-row-label">{label}</span>
      <span className="modal-row-value">{children}</span>
    </div>
  );
}
