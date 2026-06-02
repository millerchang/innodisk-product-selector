import { useState, useEffect } from 'react';

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
        // Only keep computing products for now (AIoT/IPA BU)
        const computing = data.filter(
          p => p.meta.product_line === 'computing_aiot' || p.meta.product_line === 'computing_ipa'
        );
        setProducts(computing);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return { products, loading, error };
}
