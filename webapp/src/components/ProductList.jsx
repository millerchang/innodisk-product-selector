import ProductCard from './ProductCard';

export default function ProductList({ products, recommendedPartNos, selectedForCompare, onToggleSelect, totalCount, hasSearched }) {
  if (!hasSearched) {
    return (
      <div className="all-products-grid">
        <div className="results-header">
          <span className="results-count">{totalCount} products available — enter a requirement above to filter</span>
        </div>
        <div className="products-grid">
          {products.map(p => (
            <ProductCard
              key={p.meta.part_no}
              product={p}
              recommendedPartNos={null}
              isSelected={selectedForCompare.includes(p.meta.part_no)}
              onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🔍</div>
        <h3>No products matched the hard constraints</h3>
        <p>Try relaxing temperature or TOPS requirements, or rephrase the requirement.</p>
      </div>
    );
  }

  const recommended = products.filter(p => recommendedPartNos?.includes(p.meta.part_no));
  const others = products.filter(p => !recommendedPartNos?.includes(p.meta.part_no));

  return (
    <div className="product-list">
      <div className="results-header">
        <span className="results-count">
          {products.length === totalCount
            ? `All ${totalCount} products`
            : `${products.length} of ${totalCount} products match`}
        </span>
        {selectedForCompare.length > 0 && (
          <span className="compare-count">{selectedForCompare.length} selected</span>
        )}
      </div>

      {/* AI Recommended */}
      {recommended.length > 0 && (
        <section className="result-section">
          <h4 className="section-label">AI Recommended</h4>
          <div className="products-grid">
            {recommended.map(p => (
              <ProductCard
                key={p.meta.part_no}
                product={p}
                recommendedPartNos={recommendedPartNos}
                isSelected={selectedForCompare.includes(p.meta.part_no)}
                onToggleSelect={onToggleSelect}
              />
            ))}
          </div>
        </section>
      )}

      {/* Other Matching Products */}
      {others.length > 0 && (
        <section className="result-section">
          <h4 className="section-label">
            {recommended.length > 0 ? 'Also Matches Constraints' : 'Matching Products'}
          </h4>
          <div className="products-grid">
            {others.map(p => (
              <ProductCard
                key={p.meta.part_no}
                product={p}
                recommendedPartNos={null}
                isSelected={selectedForCompare.includes(p.meta.part_no)}
                onToggleSelect={onToggleSelect}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
