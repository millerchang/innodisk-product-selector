/**
 * FilterBar — checkbox-based category filter with an "All" master checkbox.
 *
 * Behaviour:
 *   • Default: All ✓, every category ✓ → show everything
 *   • Uncheck All  → uncheck all categories
 *   • Check any individual category → show only checked ones; All becomes indeterminate
 *   • Check All again → re-check everything
 */

import { useRef, useEffect } from 'react';

const LINE_OPTIONS = [
  { key: 'computing_aiot', label: 'Computing AIoT' },
  { key: 'computing_ipa',  label: 'Computing IPA'  },
  { key: 'camera',         label: 'Camera'          },
  { key: 'io',             label: 'I/O'             },
  { key: 'networking',     label: 'Networking'      },
  { key: 'air_sensor',     label: 'Air Sensor'      },
];

const ALL_KEYS = LINE_OPTIONS.map(o => o.key);

export const EMPTY_FILTERS = { lines: [...ALL_KEYS] };   // all checked = no filter

export function isFilterEmpty(f) {
  return !f?.lines || f.lines.length === ALL_KEYS.length;
}

export function applyFilters(products, filters) {
  if (isFilterEmpty(filters)) return products;
  if (!filters.lines.length) return [];
  return products.filter(p => filters.lines.includes(p.meta.product_line));
}

// ── "All" checkbox with indeterminate support ──────────────────────────────
function AllCheckbox({ checked, indeterminate, onChange }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={onChange}
    />
  );
}

export default function FilterBar({ filters, onChange, counts = {} }) {
  const checked = filters?.lines ?? [...ALL_KEYS];

  const allChecked     = checked.length === ALL_KEYS.length;
  const noneChecked    = checked.length === 0;
  const someChecked    = !allChecked && !noneChecked;   // → indeterminate

  const handleAll = () => {
    if (allChecked || someChecked) {
      onChange({ lines: [] });          // uncheck all
    } else {
      onChange({ lines: [...ALL_KEYS] }); // check all
    }
  };

  const handleOne = (key) => {
    if (checked.includes(key)) {
      onChange({ lines: checked.filter(k => k !== key) });
    } else {
      onChange({ lines: [...checked, key] });
    }
  };

  return (
    <div className="filter-bar">
      <div className="filter-bar-row">
        <span className="filter-bar-title">Category</span>

        {/* All */}
        <label className="filter-cb-item filter-cb-all">
          <AllCheckbox
            checked={allChecked}
            indeterminate={someChecked}
            onChange={handleAll}
          />
          <span className="filter-cb-label">All</span>
        </label>

        <div className="filter-bar-divider" />

        {/* Individual categories */}
        {LINE_OPTIONS.map(opt => {
          const isChecked = checked.includes(opt.key);
          const cnt = counts.byLine?.[opt.key] ?? 0;
          return (
            <label key={opt.key} className={`filter-cb-item ${isChecked ? 'cb-active' : 'cb-dim'}`}>
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => handleOne(opt.key)}
              />
              <span className="filter-cb-label">{opt.label}</span>
              {cnt > 0 && <span className="filter-cb-count">{cnt}</span>}
            </label>
          );
        })}
      </div>
    </div>
  );
}
