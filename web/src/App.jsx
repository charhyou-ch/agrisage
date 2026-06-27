import { useState, useEffect, useCallback } from "react";

// â”€â”€ Design tokens AgriSage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const C = {
  vert:      "#27500A",
  vertMid:   "#3D7A18",
  vertClair: "#6DB842",
  creme:     "#F4F8EE",
  cremeBord: "#DDE9CC",
  ambre:     "#C97A10",
  ambreFond: "#FEF3DC",
  gris:      "#4A5568",
  grisClair: "#718096",
  rouge:     "#C0392B",
  rougeFond: "#FEE8E6",
  blanc:     "#FFFFFF",
  texte:     "#1A2E0A",
};

const API_BASE = "https://agrisage-production-9611.up.railway.app";

// â”€â”€ Utilitaires â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function apiCall(endpoint, options = {}) {
  const key = localStorage.getItem("agrisage_key") || "as_test_demo";
  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Authorization": `Bearer ${key}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  }).then(r => r.json());
}

function Badge({ color, bg, children }) {
  return (
    <span style={{
      background: bg || C.cremeBord,
      color: color || C.vert,
      padding: "2px 10px",
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: 0.3,
    }}>{children}</span>
  );
}

function RisqueBadge({ valeur }) {
  const map = {
    "Ã©levÃ©":      { bg: C.rougeFond, color: C.rouge },
    "trÃ¨s Ã©levÃ©": { bg: C.rougeFond, color: C.rouge },
    "modÃ©rÃ©":     { bg: C.ambreFond, color: C.ambre },
    "faible":     { bg: C.cremeBord, color: C.vertMid },
    "trÃ¨s faible":{ bg: C.cremeBord, color: C.vertMid },
  };
  const s = map[valeur] || { bg: C.cremeBord, color: C.gris };
  return <Badge bg={s.bg} color={s.color}>{valeur || "â€”"}</Badge>;
}

function Alerte({ texte }) {
  const isUrgent = texte.startsWith("âš ï¸") || texte.startsWith("DANGER");
  return (
    <div style={{
      background: isUrgent ? C.rougeFond : C.ambreFond,
      border: `1px solid ${isUrgent ? "#F5C6C2" : "#F5DFA0"}`,
      borderRadius: 8,
      padding: "8px 14px",
      fontSize: 13,
      color: isUrgent ? C.rouge : C.ambre,
      marginTop: 6,
      display: "flex",
      gap: 8,
      alignItems: "flex-start",
    }}>
      <span>{isUrgent ? "âš ï¸" : "ðŸŒ¿"}</span>
      <span>{texte.replace("âš ï¸","").replace("ðŸŒ¿","").trim()}</span>
    </div>
  );
}

// â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Header({ onglet, setOnglet }) {
  const tabs = [
    { id: "conseil",  label: "ðŸŒ± Conseil", },
    { id: "produits", label: "ðŸ“¦ Produits", },
    { id: "historique", label: "ðŸ“‹ Historique", },
  ];
  return (
    <header style={{
      background: C.vert,
      color: "#fff",
      padding: "0 32px",
      display: "flex",
      alignItems: "center",
      gap: 32,
      minHeight: 60,
      boxShadow: "0 2px 12px rgba(0,0,0,.18)",
      position: "sticky",
      top: 0,
      zIndex: 100,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginRight: 16 }}>
        <span style={{ fontSize: 26 }}>ðŸŒ¿</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: 0.5 }}>AgriSage</div>
          <div style={{ fontSize: 10, opacity: 0.7, letterSpacing: 1, textTransform: "uppercase" }}>
            Conseil phytosanitaire
          </div>
        </div>
      </div>
      <nav style={{ display: "flex", gap: 4, flex: 1 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setOnglet(t.id)} style={{
            background: onglet === t.id ? "rgba(255,255,255,.18)" : "transparent",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "8px 18px",
            cursor: "pointer",
            fontWeight: onglet === t.id ? 700 : 400,
            fontSize: 14,
            borderBottom: onglet === t.id ? "2px solid #6DB842" : "2px solid transparent",
            transition: "all .15s",
          }}>{t.label}</button>
        ))}
      </nav>
      <KeyInput />
    </header>
  );
}

function KeyInput() {
  const [key, setKey] = useState(localStorage.getItem("agrisage_key") || "as_test_demo");
  const [editing, setEditing] = useState(false);
  return editing ? (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input value={key} onChange={e => setKey(e.target.value)}
        style={{ background: "rgba(255,255,255,.15)", border: "1px solid rgba(255,255,255,.3)",
          color: "#fff", borderRadius: 6, padding: "4px 10px", fontSize: 12, width: 200 }}
        placeholder="as_live_..."
      />
      <button onClick={() => { localStorage.setItem("agrisage_key", key); setEditing(false); }}
        style={{ background: C.vertClair, color: "#fff", border: "none", borderRadius: 6,
          padding: "4px 12px", cursor: "pointer", fontWeight: 700, fontSize: 12 }}>
        OK
      </button>
    </div>
  ) : (
    <button onClick={() => setEditing(true)} style={{
      background: "rgba(255,255,255,.12)", color: "rgba(255,255,255,.85)",
      border: "1px solid rgba(255,255,255,.2)", borderRadius: 6,
      padding: "4px 12px", cursor: "pointer", fontSize: 12,
    }}>ðŸ”‘ {key.slice(0, 18)}â€¦</button>
  );
}

// â”€â”€ Onglet Conseil â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const CULTURES_FREQ = ["tomate","vigne","agrumes","fraisier","pomme de terre",
  "poivron","concombre","melon","pastÃ¨que","blÃ© tendre","orge","maÃ¯s",
  "olivier","rosacÃ©es","laitue","carotte","oignon","artichaut","piment"];

const RAVAGEURS_FREQ = {
  fongicide: ["botrytis","mildiou","oÃ¯dium","alternariose","fusariose",
    "cladosporiose","septoriose","anthracnose","pourriture grise"],
  insecticide: ["tuta absoluta","puceron","mouche mineuse","aleurode",
    "thrips","cochenille","acarien","noctuelles","mineuse"],
  herbicide: ["adventices graminÃ©es","adventices dicotylÃ©dones","ray-grass"],
};

const STADES = ["germination","levee","vegetation","floraison",
  "fructification","recolte","post-recolte"];

function OngletConseil({ addHistorique }) {
  const [form, setForm] = useState({
    culture: "", ravageur: "", stade: "vegetation",
    dar_max: "", historique_frac: "", nb_alternatives: 2,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.culture || !form.ravageur || !form.stade) {
      setError("Culture, ravageur et stade sont requis.");
      return;
    }
    setLoading(true); setError(null); setResult(null);
    try {
      const body = {
        culture: form.culture,
        ravageur: form.ravageur,
        stade: form.stade,
        nb_alternatives: form.nb_alternatives,
      };
      if (form.dar_max) body.dar_max = parseInt(form.dar_max);
      if (form.historique_frac) {
        body.historique_frac = form.historique_frac.split(",").map(s => s.trim()).filter(Boolean);
      }
      const data = await apiCall("/v1/conseil", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (data.error) throw new Error(data.error.message);
      setResult(data);
      addHistorique({ ...data, _query: form });
    } catch(e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const ravageursSuggeres = RAVAGEURS_FREQ.fongicide.concat(
    RAVAGEURS_FREQ.insecticide, RAVAGEURS_FREQ.herbicide
  );

  return (
    <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 24, alignItems: "start" }}>

      {/* Formulaire */}
      <div style={{ background: C.blanc, borderRadius: 16, padding: 28,
        border: `1px solid ${C.cremeBord}`, boxShadow: "0 2px 12px rgba(0,0,0,.06)" }}>
        <h2 style={{ color: C.vert, fontSize: 17, fontWeight: 700, marginBottom: 20 }}>
          Nouveau conseil
        </h2>

        <Label>Culture *</Label>
        <input list="cultures-list" value={form.culture}
          onChange={e => set("culture", e.target.value)}
          placeholder="ex: tomate, vigne..."
          style={inputStyle} />
        <datalist id="cultures-list">
          {CULTURES_FREQ.map(c => <option key={c} value={c} />)}
        </datalist>

        <Label>Ravageur / Maladie *</Label>
        <input list="ravageurs-list" value={form.ravageur}
          onChange={e => set("ravageur", e.target.value)}
          placeholder="ex: botrytis, mildiou..."
          style={inputStyle} />
        <datalist id="ravageurs-list">
          {ravageursSuggeres.map(r => <option key={r} value={r} />)}
        </datalist>

        <Label>Stade phÃ©nologique *</Label>
        <select value={form.stade} onChange={e => set("stade", e.target.value)}
          style={inputStyle}>
          {STADES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
        </select>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <Label>DAR max (jours)</Label>
            <input type="number" min="0" max="90" value={form.dar_max}
              onChange={e => set("dar_max", e.target.value)}
              placeholder="ex: 7" style={inputStyle} />
          </div>
          <div>
            <Label>Alternatives</Label>
            <select value={form.nb_alternatives}
              onChange={e => set("nb_alternatives", parseInt(e.target.value))}
              style={inputStyle}>
              {[0,1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>

        <Label>Groupes FRAC dÃ©jÃ  utilisÃ©s</Label>
        <input value={form.historique_frac}
          onChange={e => set("historique_frac", e.target.value)}
          placeholder="ex: 11, 3, M3 (sÃ©parÃ©s par virgule)"
          style={inputStyle} />

        {error && (
          <div style={{ background: C.rougeFond, color: C.rouge, borderRadius: 8,
            padding: "10px 14px", fontSize: 13, marginBottom: 12 }}>
            {error}
          </div>
        )}

        <button onClick={submit} disabled={loading} style={{
          width: "100%", background: loading ? C.grisClair : C.vert,
          color: "#fff", border: "none", borderRadius: 10,
          padding: "13px 0", fontWeight: 700, fontSize: 15,
          cursor: loading ? "not-allowed" : "pointer",
          marginTop: 4, transition: "background .15s",
        }}>
          {loading ? "â³ Analyse en cours..." : "ðŸŒ± GÃ©nÃ©rer le conseil"}
        </button>
      </div>

      {/* RÃ©sultat */}
      <div>
        {!result && !loading && (
          <div style={{ background: C.creme, borderRadius: 16, padding: 48,
            textAlign: "center", border: `2px dashed ${C.cremeBord}` }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>ðŸŒ¿</div>
            <div style={{ color: C.gris, fontSize: 15 }}>
              Remplissez le formulaire et cliquez<br />
              <strong style={{ color: C.vert }}>GÃ©nÃ©rer le conseil</strong> pour obtenir<br />
              une recommandation basÃ©e sur l'index ONSSA.
            </div>
          </div>
        )}
        {loading && (
          <div style={{ background: C.creme, borderRadius: 16, padding: 48,
            textAlign: "center", border: `1px solid ${C.cremeBord}` }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>â³</div>
            <div style={{ color: C.gris }}>Consultation de l'index ONSSAâ€¦</div>
          </div>
        )}
        {result && <ResultatConseil data={result} />}
      </div>
    </div>
  );
}

function ResultatConseil({ data }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* Produit principal */}
      <div style={{ background: C.blanc, borderRadius: 16, padding: 28,
        border: `2px solid ${C.vertClair}`, boxShadow: "0 4px 20px rgba(39,80,10,.1)" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 11, color: C.vertClair, fontWeight: 700,
              letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
              Produit recommandÃ© Â· ONSSA âœ“
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: C.texte, margin: 0 }}>
              {data.produit}
            </h2>
            <div style={{ color: C.gris, fontSize: 14, marginTop: 4 }}>
              {data.matiere_active}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 11, color: C.gris, marginBottom: 4 }}>DAR</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: C.vert }}>
              {data.dar ?? "â€”"}
            </div>
            <div style={{ fontSize: 11, color: C.gris }}>jours</div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
          <InfoBox label="Dose" value={data.dose || "â€”"} />
          <InfoBox label="Formulation" value={data.formulation || "â€”"} />
          <InfoBox label="Groupe FRAC" value={data.groupe_frac || "â€”"} />
          <InfoBox label="Groupe IRAC" value={data.groupe_irac || "â€”"} />
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: data.alertes?.length ? 12 : 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: C.gris }}>
            <span>ðŸ Abeilles :</span>
            <RisqueBadge valeur={data.risque_abeilles} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: C.gris }}>
            <span>âš¡ RÃ©sistance :</span>
            <RisqueBadge valeur={data.risque_resistance} />
          </div>
          {data.valable_jusquau && (
            <div style={{ fontSize: 13, color: C.gris }}>
              ðŸ“… HomologuÃ© jusqu'au {data.valable_jusquau}
            </div>
          )}
        </div>

        {data.alertes?.map((a, i) => <Alerte key={i} texte={a} />)}

        {data.usage_homologue && (
          <div style={{ marginTop: 12, padding: "8px 12px", background: C.creme,
            borderRadius: 8, fontSize: 12, color: C.gris }}>
            <strong>Usage homologuÃ© :</strong> {data.usage_homologue}
          </div>
        )}

        {data.rotation_note && (
          <div style={{ marginTop: 8, padding: "8px 12px", background: C.ambreFond,
            borderRadius: 8, fontSize: 12, color: C.ambre }}>
            <strong>Rotation :</strong> {data.rotation_note}
          </div>
        )}
      </div>

      {/* Alternatives */}
      {data.alternatives?.length > 0 && (
        <div style={{ background: C.blanc, borderRadius: 16, padding: 24,
          border: `1px solid ${C.cremeBord}` }}>
          <h3 style={{ color: C.vert, fontSize: 15, fontWeight: 700, marginBottom: 16 }}>
            â†º Alternatives de rotation ({data.alternatives.length})
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {data.alternatives.map((alt, i) => (
              <div key={i} style={{ display: "grid",
                gridTemplateColumns: "1fr auto auto auto",
                gap: 12, alignItems: "center",
                padding: "12px 16px", background: C.creme,
                borderRadius: 10, border: `1px solid ${C.cremeBord}` }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: C.texte }}>{alt.produit}</div>
                  <div style={{ fontSize: 12, color: C.gris }}>{alt.matiere_active}</div>
                </div>
                <Badge>{alt.groupe_frac ? `FRAC ${alt.groupe_frac}` : alt.groupe_irac ? `IRAC ${alt.groupe_irac}` : "â€”"}</Badge>
                <div style={{ fontSize: 12, color: C.gris, textAlign: "right" }}>
                  {alt.dar != null ? `DAR ${alt.dar}j` : "DAR â€”"}
                </div>
                <div style={{ fontSize: 12, color: C.gris }}>{alt.dose || "â€”"}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MÃ©ta */}
      <div style={{ fontSize: 11, color: C.grisClair, textAlign: "right" }}>
        conseil_id: {data.conseil_id} Â· {data.timestamp?.slice(0,19).replace("T"," ")}
        Â· {data.meta?.nb_produits_trouves} produits analysÃ©s
      </div>
    </div>
  );
}

function InfoBox({ label, value }) {
  return (
    <div style={{ background: C.creme, borderRadius: 10, padding: "10px 14px" }}>
      <div style={{ fontSize: 10, color: C.grisClair, textTransform: "uppercase",
        letterSpacing: 0.8, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 600, color: C.texte }}>{value}</div>
    </div>
  );
}

// â”€â”€ Onglet Produits â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function OngletProduits() {
  const [filtres, setFiltres] = useState({ culture: "", usage: "", q: "", groupe_frac: "" });
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selectedProduit, setSelectedProduit] = useState(null);

  const setF = (k, v) => { setFiltres(f => ({ ...f, [k]: v })); setPage(1); };

  const charger = useCallback(async () => {
    setLoading(true);
    const qs = new URLSearchParams({ page });
    if (filtres.culture) qs.set("culture", filtres.culture);
    if (filtres.usage)   qs.set("usage", filtres.usage);
    if (filtres.q)       qs.set("q", filtres.q);
    if (filtres.groupe_frac) qs.set("groupe_frac", filtres.groupe_frac);
    const res = await apiCall(`/v1/produits?${qs}`);
    setData(res);
    setLoading(false);
  }, [filtres, page]);

  useEffect(() => { charger(); }, [charger]);

  const chargerDetail = async (id) => {
    const res = await apiCall(`/v1/produits/${id}`);
    setSelectedProduit(res);
  };

  return (
    <div>
      {/* Filtres */}
      <div style={{ background: C.blanc, borderRadius: 14, padding: "16px 20px",
        border: `1px solid ${C.cremeBord}`, marginBottom: 20,
        display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12 }}>
        <div>
          <Label>Recherche libre</Label>
          <input value={filtres.q} onChange={e => setF("q", e.target.value)}
            placeholder="Nom commercial, matiÃ¨re active..." style={inputStyle} />
        </div>
        <div>
          <Label>Culture</Label>
          <input value={filtres.culture} onChange={e => setF("culture", e.target.value)}
            placeholder="ex: tomate" style={inputStyle} />
        </div>
        <div>
          <Label>Type de produit</Label>
          <select value={filtres.usage} onChange={e => setF("usage", e.target.value)}
            style={inputStyle}>
            <option value="">Tous</option>
            <option value="fongicide">Fongicide</option>
            <option value="insecticide">Insecticide</option>
            <option value="herbicide">Herbicide</option>
            <option value="acaricide">Acaricide</option>
            <option value="nematicide">NÃ©maticide</option>
          </select>
        </div>
        <div>
          <Label>Groupe FRAC</Label>
          <input value={filtres.groupe_frac} onChange={e => setF("groupe_frac", e.target.value)}
            placeholder="ex: 11, 9, M3" style={inputStyle} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selectedProduit ? "1fr 420px" : "1fr", gap: 20 }}>
        {/* Liste */}
        <div>
          {loading && (
            <div style={{ textAlign: "center", padding: 40, color: C.gris }}>â³ Chargementâ€¦</div>
          )}
          {data && !loading && (
            <>
              <div style={{ fontSize: 13, color: C.gris, marginBottom: 12 }}>
                <strong style={{ color: C.texte }}>{data.pagination?.total}</strong> produits Â·
                page {data.pagination?.page}/{data.pagination?.pages_total}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {data.data?.map(p => (
                  <div key={p.id} onClick={() => chargerDetail(p.id)} style={{
                    background: selectedProduit?.id === p.id ? C.creme : C.blanc,
                    border: `1px solid ${selectedProduit?.id === p.id ? C.vertClair : C.cremeBord}`,
                    borderRadius: 12, padding: "14px 18px",
                    cursor: "pointer", transition: "all .12s",
                    display: "grid", gridTemplateColumns: "1fr auto auto auto",
                    gap: 12, alignItems: "center",
                  }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14, color: C.texte }}>
                        {p.nom_commercial}
                      </div>
                      <div style={{ fontSize: 12, color: C.gris, marginTop: 2 }}>
                        {p.matiere_active?.slice(0, 60)}{p.matiere_active?.length > 60 ? "â€¦" : ""}
                      </div>
                      {p.cultures_homologuees?.length > 0 && (
                        <div style={{ fontSize: 11, color: C.grisClair, marginTop: 3 }}>
                          {p.cultures_homologuees.slice(0, 4).join(", ")}
                          {p.cultures_homologuees.length > 4 ? ` +${p.cultures_homologuees.length-4}` : ""}
                        </div>
                      )}
                    </div>
                    <Badge bg={p.type_produit === "fongicide" ? "#E8F5E1" :
                               p.type_produit?.includes("insecticide") ? "#FEF3DC" :
                               p.type_produit === "herbicide" ? "#E8F0FE" : C.cremeBord}
                           color={p.type_produit === "fongicide" ? C.vertMid :
                                  p.type_produit?.includes("insecticide") ? C.ambre :
                                  p.type_produit === "herbicide" ? "#3D57C2" : C.gris}>
                      {p.type_produit || "â€”"}
                    </Badge>
                    {p.groupe_frac && <Badge>FRAC {p.groupe_frac}</Badge>}
                    <RisqueBadge valeur={p.risque_abeilles} />
                  </div>
                ))}
              </div>

              {/* Pagination */}
              <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "center" }}>
                <PaginBtn disabled={page===1} onClick={() => setPage(p=>p-1)}>â† PrÃ©cÃ©dent</PaginBtn>
                <span style={{ padding: "6px 14px", fontSize: 13, color: C.gris }}>
                  Page {page} / {data.pagination?.pages_total}
                </span>
                <PaginBtn disabled={page>=data.pagination?.pages_total}
                  onClick={() => setPage(p=>p+1)}>Suivant â†’</PaginBtn>
              </div>
            </>
          )}
        </div>

        {/* DÃ©tail */}
        {selectedProduit && (
          <div style={{ background: C.blanc, borderRadius: 16, padding: 24,
            border: `1px solid ${C.cremeBord}`, position: "sticky", top: 80,
            maxHeight: "calc(100vh - 120px)", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h3 style={{ color: C.vert, fontSize: 16, fontWeight: 800 }}>
                {selectedProduit.nom_commercial}
              </h3>
              <button onClick={() => setSelectedProduit(null)} style={{
                background: "none", border: "none", fontSize: 18,
                cursor: "pointer", color: C.gris }}>âœ•</button>
            </div>
            <div style={{ fontSize: 13, color: C.gris, marginBottom: 8 }}>
              {selectedProduit.matiere_active}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
              <Badge>{selectedProduit.type_produit}</Badge>
              {selectedProduit.groupe_frac && <Badge>FRAC {selectedProduit.groupe_frac}</Badge>}
              {selectedProduit.groupe_irac && <Badge>IRAC {selectedProduit.groupe_irac}</Badge>}
              <RisqueBadge valeur={selectedProduit.risque_abeilles} />
            </div>
            <div style={{ fontSize: 12, color: C.gris, marginBottom: 4 }}>
              <strong>DÃ©tenteur :</strong> {selectedProduit.detenteur}
            </div>
            <div style={{ fontSize: 12, color: C.gris, marginBottom: 12 }}>
              <strong>HomologuÃ© jusqu'au :</strong> {selectedProduit.valable_jusquau}
            </div>
            {selectedProduit.frac_info && (
              <div style={{ background: C.creme, borderRadius: 10, padding: "10px 14px", marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.vert, marginBottom: 4 }}>
                  FRAC {selectedProduit.frac_info.groupe}
                </div>
                <div style={{ fontSize: 12, color: C.gris }}>{selectedProduit.frac_info.mecanisme}</div>
                <div style={{ fontSize: 11, color: C.ambre, marginTop: 4 }}>
                  {selectedProduit.frac_info.recommandation}
                </div>
              </div>
            )}
            <div style={{ fontSize: 12, fontWeight: 700, color: C.texte, marginBottom: 8 }}>
              Usages homologuÃ©s ({selectedProduit.usages?.length})
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 300, overflowY: "auto" }}>
              {selectedProduit.usages?.map((u, i) => (
                <div key={i} style={{ background: C.creme, borderRadius: 8,
                  padding: "8px 12px", fontSize: 12 }}>
                  <div style={{ fontWeight: 600, color: C.texte }}>{u.culture}</div>
                  <div style={{ color: C.gris }}>{u.usage_desc}</div>
                  <div style={{ color: C.grisClair, marginTop: 2 }}>
                    Dose : {u.dose || "â€”"} Â· DAR : {u.dar_jours != null ? u.dar_jours + "j" : "â€”"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PaginBtn({ children, disabled, onClick }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: disabled ? C.creme : C.vert,
      color: disabled ? C.grisClair : "#fff",
      border: `1px solid ${disabled ? C.cremeBord : C.vert}`,
      borderRadius: 8, padding: "6px 14px",
      cursor: disabled ? "not-allowed" : "pointer",
      fontSize: 13, fontWeight: 600,
    }}>{children}</button>
  );
}

// â”€â”€ Onglet Historique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function OngletHistorique({ historique, clearHistorique }) {
  const [selected, setSelected] = useState(null);

  if (historique.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: 60, color: C.gris }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>ðŸ“‹</div>
        <div style={{ fontSize: 15 }}>
          Aucun conseil gÃ©nÃ©rÃ© dans cette session.<br />
          <span style={{ color: C.vertMid }}>Utilisez l'onglet Conseil pour commencer.</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 14, color: C.gris }}>
          <strong style={{ color: C.texte }}>{historique.length}</strong> conseil(s) dans cette session
        </div>
        <button onClick={clearHistorique} style={{
          background: "none", border: `1px solid ${C.cremeBord}`,
          color: C.gris, borderRadius: 8, padding: "6px 14px",
          cursor: "pointer", fontSize: 13 }}>
          Effacer
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {[...historique].reverse().map((item, i) => (
          <div key={item.conseil_id} onClick={() => setSelected(selected?.conseil_id === item.conseil_id ? null : item)}
            style={{
              background: selected?.conseil_id === item.conseil_id ? C.creme : C.blanc,
              border: `1px solid ${selected?.conseil_id === item.conseil_id ? C.vertClair : C.cremeBord}`,
              borderRadius: 14, padding: "16px 20px", cursor: "pointer",
            }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <Badge bg={C.creme} color={C.vertMid}>
                {item._query?.culture} / {item._query?.ravageur}
              </Badge>
              <span style={{ fontSize: 11, color: C.grisClair }}>
                {item.timestamp?.slice(11,19)}
              </span>
            </div>
            <div style={{ fontWeight: 700, fontSize: 15, color: C.texte }}>{item.produit}</div>
            <div style={{ fontSize: 12, color: C.gris, marginTop: 2 }}>
              {item.matiere_active?.slice(0,50)}
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              {item.groupe_frac && <Badge>FRAC {item.groupe_frac}</Badge>}
              <span style={{ fontSize: 12, color: C.gris }}>DAR {item.dar ?? "â€”"}j</span>
              <RisqueBadge valeur={item.risque_abeilles} />
            </div>
            {selected?.conseil_id === item.conseil_id && (
              <div style={{ marginTop: 12, borderTop: `1px solid ${C.cremeBord}`, paddingTop: 12 }}>
                {item.alertes?.map((a, j) => <Alerte key={j} texte={a} />)}
                {item.rotation_note && (
                  <div style={{ fontSize: 12, color: C.ambre, marginTop: 8 }}>
                    â†º {item.rotation_note}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// â”€â”€ Composants utilitaires â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Label({ children }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 600, color: C.gris,
      marginBottom: 5, marginTop: 14 }}>{children}</div>
  );
}

const inputStyle = {
  width: "100%", boxSizing: "border-box",
  border: `1.5px solid ${C.cremeBord}`, borderRadius: 8,
  padding: "9px 12px", fontSize: 14, color: C.texte,
  background: C.creme, outline: "none",
  fontFamily: "inherit",
};

// â”€â”€ App principale â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function AgriSageApp() {
  const [onglet, setOnglet] = useState("conseil");
  const [historique, setHistorique] = useState([]);

  const addHistorique = useCallback((item) => {
    setHistorique(h => [...h, item]);
  }, []);

  const clearHistorique = useCallback(() => setHistorique([]), []);

  return (
    <div style={{ minHeight: "100vh", background: C.creme, fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: C.texte }}>
      <Header onglet={onglet} setOnglet={setOnglet} />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 24px" }}>
        {onglet === "conseil"   && <OngletConseil addHistorique={addHistorique} />}
        {onglet === "produits"  && <OngletProduits />}
        {onglet === "historique"&& <OngletHistorique historique={historique} clearHistorique={clearHistorique} />}
      </main>
    </div>
  );
}
