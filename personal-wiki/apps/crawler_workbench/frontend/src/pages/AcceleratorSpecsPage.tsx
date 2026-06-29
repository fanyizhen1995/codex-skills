import { ChevronDown, ChevronUp, RefreshCw, RotateCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { extractAcceleratorSpecs, getAcceleratorSpecs } from "../api";
import type { AcceleratorResolvedField, AcceleratorSpecRecord } from "../types";

function fieldValue(field: AcceleratorResolvedField) {
  return field.unit === "none" ? field.value_text : `${field.value_text} ${field.unit}`;
}

function observationCount(specs: AcceleratorSpecRecord[]) {
  return specs.reduce((count, spec) => count + spec.observations.length, 0);
}

export function AcceleratorSpecsPage() {
  const [specs, setSpecs] = useState<AcceleratorSpecRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [expandedSkuIds, setExpandedSkuIds] = useState<Set<string>>(new Set());

  async function loadSpecs() {
    setLoading(true);
    try {
      const response = await getAcceleratorSpecs();
      setSpecs(response);
      setError("");
      return response;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载参数库失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSpecs();
  }, []);

  const totals = useMemo(
    () => ({
      skus: specs.length,
      observations: observationCount(specs),
      resolved: specs.reduce((count, spec) => count + spec.resolved_specs.length, 0)
    }),
    [specs]
  );

  async function handleExtract() {
    setExtracting(true);
    setNotice("");
    setError("");
    try {
      const counts = await extractAcceleratorSpecs();
      await loadSpecs();
      setNotice(`已处理 ${counts.skus} 个 SKU，${counts.observations} 条观测，${counts.resolved} 个 resolved 字段`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "回填参数失败");
    } finally {
      setExtracting(false);
    }
  }

  function toggleObservations(skuId: string) {
    setExpandedSkuIds((current) => {
      const next = new Set(current);
      if (next.has(skuId)) {
        next.delete(skuId);
      } else {
        next.add(skuId);
      }
      return next;
    });
  }

  return (
    <section className="page-section accelerator-specs-page" aria-labelledby="accelerator-specs-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Compute Accelerators</p>
          <h1 id="accelerator-specs-title">参数库</h1>
        </div>
        <div className="inline-actions">
          <button className="icon-button" type="button" onClick={loadSpecs} disabled={loading || extracting}>
            <RefreshCw aria-hidden="true" size={16} />
            刷新
          </button>
          <button className="icon-button" type="button" onClick={handleExtract} disabled={loading || extracting}>
            <RotateCw aria-hidden="true" size={16} />
            {extracting ? "回填中" : "回填参数"}
          </button>
        </div>
      </div>

      {error && (
        <small className="notice error-notice" role="alert">
          {error}
        </small>
      )}
      {!error && notice && (
        <small className="notice" role="status">
          {notice}
        </small>
      )}

      <div className="metrics-grid specs-metrics" aria-label="参数库概览">
        <div className="metric-card">
          <span className="metric-label">SKU</span>
          <strong>{totals.skus}</strong>
          <span className="metric-help">已识别型号</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">观测</span>
          <strong>{totals.observations}</strong>
          <span className="metric-help">保留来源证据</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Resolved</span>
          <strong>{totals.resolved}</strong>
          <span className="metric-help">规则确认字段</span>
        </div>
      </div>

      <div className="work-panel specs-panel">
        <h2>规格记录</h2>
        {specs.length === 0 ? (
          <div className="empty-state">{loading ? "正在加载参数库" : "暂无结构化参数"}</div>
        ) : (
          <div className="responsive-table specs-table" role="table" aria-label="计算卡参数库">
            <div className="table-row specs-row table-head" role="row">
              <span role="columnheader">SKU</span>
              <span role="columnheader">Resolved 字段</span>
              <span role="columnheader">观测证据</span>
              <span role="columnheader">来源</span>
            </div>
            {specs.map((spec) => (
              <div className="table-row specs-row" role="row" key={spec.sku_id}>
                <span role="cell">
                  <strong>{spec.sku_id}</strong>
                  <small>
                    {spec.vendor} · {spec.scope} · {spec.source_profile_id}
                  </small>
                </span>
                <span role="cell">
                  {spec.resolved_specs.length === 0 ? (
                    <small>暂无 resolved 字段</small>
                  ) : (
                    <div className="spec-field-list">
                      {spec.resolved_specs.map((field) => (
                        <span className="spec-field-pill" key={field.field}>
                          <b>{field.field}</b>
                          {fieldValue(field)}
                        </span>
                      ))}
                    </div>
                  )}
                </span>
                <span role="cell">
                  <div className="spec-observation-list">
                    {spec.observations.length === 0 ? (
                      <small>暂无观测证据</small>
                    ) : (
                      <>
                        <small>
                          {spec.observations[0].field}: {spec.observations[0].evidence_text} ·{" "}
                          {spec.observations[0].source_rank}
                        </small>
                        <button
                          className="link-button"
                          type="button"
                          aria-expanded={expandedSkuIds.has(spec.sku_id)}
                          aria-label={`${expandedSkuIds.has(spec.sku_id) ? "收起" : "展开"} ${spec.sku_id} 观测证据`}
                          onClick={() => toggleObservations(spec.sku_id)}
                        >
                          {expandedSkuIds.has(spec.sku_id) ? (
                            <ChevronUp aria-hidden="true" size={14} />
                          ) : (
                            <ChevronDown aria-hidden="true" size={14} />
                          )}
                          {expandedSkuIds.has(spec.sku_id)
                            ? "收起观测"
                            : `展开 ${spec.observations.length} 条观测`}
                        </button>
                        {expandedSkuIds.has(spec.sku_id) && (
                          <div className="spec-observation-details">
                            {spec.observations.map((observation) => (
                              <div className="spec-observation-card" key={observation.id}>
                                <strong>{observation.field}</strong>
                                <small>{observation.evidence_text}</small>
                                <small>
                                  {observation.source_profile_id} · {observation.source_rank} · raw item{" "}
                                  {observation.raw_item_id ?? "n/a"}
                                </small>
                                <small>{observation.raw_path}</small>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </span>
                <span role="cell">
                  <a href={spec.source_url} target="_blank" rel="noreferrer">
                    {spec.source_url}
                  </a>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
