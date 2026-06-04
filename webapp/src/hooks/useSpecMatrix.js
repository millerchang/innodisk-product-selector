import { useState, useEffect, useMemo } from 'react';

// Product lines that act as a host/system (the "main board" of a solution).
const HOST_LINES = ['computing_aiot', 'computing_ipa'];
// Product lines that act as add-on / expansion (EP) cards.
const EP_LINES = ['io', 'networking', 'air_sensor'];

export function useSpecMatrix() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('./spec_matrix.json')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status} — spec_matrix.json not found in public/`);
        return res.json();
      })
      .then(data => {
        // Load ALL product lines — the solution builder needs hosts + EP cards.
        setProducts(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Grouped views derived once per data load.
  const { hosts, epCards, cameras } = useMemo(() => {
    const hosts = [];
    const epCards = [];
    const cameras = [];
    for (const p of products) {
      const line = p.meta.product_line;
      if (HOST_LINES.includes(line)) hosts.push(p);
      else if (EP_LINES.includes(line)) epCards.push(p);
      else if (line === 'camera') cameras.push(p);
    }
    return { hosts, epCards, cameras };
  }, [products]);

  return { products, hosts, epCards, cameras, loading, error };
}

export { HOST_LINES, EP_LINES };
