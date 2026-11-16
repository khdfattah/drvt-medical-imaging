import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -------------------------------------------------
# 1. Page Configuration & Visual Identity
# -------------------------------------------------
st.set_page_config(
    page_title="DRVT Medical Imaging Suite",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 2.2rem; font-weight: 700; color: #1E3A8A;}
    .sub-header {font-size: 1.1rem; color: #4B5563; margin-bottom: 1.5rem;}
    .metric-card {background-color: #F8FAFC; padding: 15px; border-radius: 10px; border-left: 5px solid #2563EB;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# 2. Fundamental Constants from DRVT Framework
# -------------------------------------------------
V_EQ = 286.398          # nm^3 (Resonant Equilibrium Volume)
K_CONST = 13.0 / 3.0    # eV/nm^2 (Resonant Surface-Energy Density Coefficient)
LAMBDA_C = 0.002426     # nm (Compton Boundary Wavelength)
LAMBDA_R = 91.127       # nm (Reference Resonance Wavelength)
LAMBDA_B = 32550.0      # nm (Bohr-Horizon Boundary = 32.55 micrometers)
A_0 = 0.0529177         # nm (Bohr Radius)
C_VACUUM = 2.998e17     # nm/s (Speed of Light in Vacuum)

# -------------------------------------------------
# 3. Reference Databases (Clinical Fluorophores & Tissues)
# -------------------------------------------------
FLUOROPHORES = {
    "Custom Input": {"exc": 405.0, "em": 635.0, "eta": 0.10, "app": "Custom Biomedical Protocol"},
    "5-ALA / PpIX (Neuro-Oncology)": {"exc": 405.0, "em": 635.0, "eta": 0.15, "app": "Fluorescence-Guided Brain Tumor Surgery"},
    "Indocyanine Green - ICG (Vascular/Hepatic)": {"exc": 780.0, "em": 820.0, "eta": 0.09, "app": "NIR Angiography & Perfusion Imaging"},
    "Fluorescein Sodium (Ophthalmology/Neuro)": {"exc": 490.0, "em": 520.0, "eta": 0.79, "app": "Retinal Angiography & Microsurgery"},
    "Methylene Blue (Lymphatic Mapping)": {"exc": 665.0, "em": 686.0, "eta": 0.04, "app": "Sentinel Lymph Node Biopsy"}
}

TISSUES = {
    "Brain Tissue (n = 1.40)": {"n": 1.40, "v_scan": 1.0e14},
    "Tumor Microenvironment (n = 1.42)": {"n": 1.42, "v_scan": 5.0e13},
    "Skin / Epidermis (n = 1.44)": {"n": 1.44, "v_scan": 2.0e14},
    "Blood / Vascular (n = 1.36)": {"n": 1.36, "v_scan": 1.5e14}
}

# Initialize Session State for Multi-Scenario Comparison
if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = []

# -------------------------------------------------
# 4. DRVT Physics & Computational Engine
# -------------------------------------------------
def classify_drvt_regime(wavelength_nm):
    if wavelength_nm < LAMBDA_C:
        return "Pre-Resonant Domain", "Vacuum-dominated and sub-particle interaction regimes."
    elif LAMBDA_C <= wavelength_nm < LAMBDA_R:
        return "Above-Reference Resonance", "Transverse expansion compensates for shortened wavelengths."
    elif math.isclose(wavelength_nm, LAMBDA_R, rel_tol=1e-3):
        return "Reference Resonance", "Geometric equilibrium state derived from fundamental constants."
    elif LAMBDA_R < wavelength_nm < LAMBDA_B:
        return "Below-Reference Resonance", "Progressive transverse spatial localization at atomic/molecular scales."
    else:
        return "Post-Atomic Resonance Domain", "Transition from photonic to collective mechanical/phonon resonance."

def run_drvt_simulation(lambda_exc, lambda_em, p_exc_mw, eta_f, scan_volume, refractive_index, geometry_factor=1.0):
    A_exc = (V_EQ / lambda_exc) * geometry_factor
    E_exc = K_CONST * A_exc
    
    A_em = (V_EQ / lambda_em) * geometry_factor
    E_em = K_CONST * A_em
    
    r_res_exc = math.sqrt(V_EQ / (math.pi * lambda_exc))
    r_res_em = math.sqrt(V_EQ / (math.pi * lambda_em))
    
    E_exc_J = E_exc * 1.60218e-19
    N_exc = (p_exc_mw * 1e-3) / E_exc_J
    
    vg = C_VACUUM / refractive_index
    tau_exc = lambda_exc / vg
    N_photons = N_exc * tau_exc
    
    N_res = scan_volume / V_EQ
    PCI = N_photons / N_res
    CED = PCI * E_exc
    FVI = eta_f * max(0.0, (1.0 - PCI))
    
    return {
        "A_exc": A_exc, "E_exc": E_exc, "r_res_exc": r_res_exc,
        "A_em": A_em, "E_em": E_em, "r_res_em": r_res_em,
        "N_exc": N_exc, "vg": vg, "tau_exc": tau_exc,
        "N_photons": N_photons, "N_res": N_res,
        "PCI": PCI, "CED": CED, "FVI": FVI
    }

# -------------------------------------------------
# 5. Sidebar Controls (Clinical & Physical Presets)
# -------------------------------------------------
with st.sidebar:
    st.image("https://flaticon.com", width=60)
    st.title("Simulation Controls")
    st.markdown("---")
    
    selected_dye = st.selectbox("Clinical Fluorophore Preset:", list(FLUOROPHORES.keys()), index=1)
    dye_data = FLUOROPHORES[selected_dye]
    st.caption(f"Clinical Application: **{dye_data['app']}**")
    
    selected_tissue = st.selectbox("Target Biological Tissue:", list(TISSUES.keys()), index=0)
    tissue_data = TISSUES[selected_tissue]
    
    st.markdown("### 🎛️ Optical & Laser Parameters")
    lambda_exc = st.number_input("Excitation Wavelength λ_exc (nm)", value=dye_data["exc"], min_value=10.0, max_value=50000.0, step=5.0)
    lambda_em = st.number_input("Emission Wavelength λ_em (nm)", value=dye_data["em"], min_value=10.0, max_value=50000.0, step=5.0)
    p_exc_mw = st.slider("Excitation Laser Power (mW)", min_value=1.0, max_value=500.0, value=30.0, step=1.0)
    eta_f = st.slider("Fluorescence Quantum Yield η_f", min_value=0.01, max_value=1.00, value=dye_data["eta"], step=0.01)
    
    with st.expander("Advanced Theoretical Parameters"):
        scan_volume = st.number_input("Interaction Scan Volume V_scan (nm³)", value=tissue_data["v_scan"], format="%.2e")
        refractive_index = st.number_input("Tissue Refractive Index (n)", value=tissue_data["n"], min_value=1.0, max_value=2.5, step=0.01)
        geometry_factor = st.slider(
            "Geometric Anisotropy Factor", 
            0.5, 2.0, 1.0, 0.05, 
            help="1.0 represents ideal circular symmetry (Assumption B in DRVT)."
        )

# -------------------------------------------------
# 6. Main Interface & Execution
# -------------------------------------------------
st.markdown('<div class="main-header">🧠 DRVT Medical Imaging Design Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Clinical & Engineering Platform applying Dynamic Resonant Volume Theory (Dr. Khalid Abdel Fattah) to optimize fluorescence contrast and prevent photobleaching.</div>', unsafe_allow_html=True)

res = run_drvt_simulation(lambda_exc, lambda_em, p_exc_mw, eta_f, scan_volume, refractive_index, geometry_factor)
regime_title, regime_desc = classify_drvt_regime(lambda_exc)

st.info(f"**DRVT Resonance Classification:** {regime_title} — *{regime_desc}*")

# -------------------------------------------------
# 7. Key Performance Indicators (KPIs)
# -------------------------------------------------
st.subheader("📊 Primary Engineering & Clinical Metrics")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Photon Congestion Index (PCI)", 
        f"{res['PCI']:.2e}", 
        delta="Safe Regime" if res['PCI'] < 1e-6 else "High Congestion", 
        delta_color="inverse"
    )
with c2:
    st.metric(
        "Fluorescence Visibility Index (FVI)", 
        f"{res['FVI']:.4f}", 
        delta="Optimal" if res['FVI'] > 0.7 else ("Acceptable" if res['FVI'] > 0.3 else "Poor Contrast")
    )
with c3:
    st.metric(
        "Resonant State Radius (r_res)", 
        f"{res['r_res_exc']:.4f} nm", 
        delta=f"{res['r_res_exc']/A_0:.2f}x Bohr Radius", 
        delta_color="off"
    )
with c4:
    st.metric("Congestion Energy Density (CED)", f"{res['CED']:.2e} eV/nm³")

# -------------------------------------------------
# 8. Interactive Analysis Tabs
# -------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Dynamic Simulation & Plots", 
    "🎯 Auto-Optimizer & Clinical Guidance", 
    "📋 Complete Physical Parameters", 
    "⚖️ Scenario Comparison & Export"
])

# --- Tab 1: Interactive Visualization ---
with tab1:
    st.markdown("#### Impact of Laser Excitation Power on Photon Congestion (PCI)")
    powers = np.linspace(1, 500, 100)
    pci_list = []
    
    for p in powers:
        sim = run_drvt_simulation(lambda_exc, lambda_em, p, eta_f, scan_volume, refractive_index, geometry_factor)
        pci_list.append(sim["PCI"])
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=powers, y=pci_list, name="Photon Congestion Index (PCI)", line=dict(color="#EF4444", width=3)))
    fig.add_vline(x=p_exc_mw, line_dash="dash", line_color="#1E3A8A", annotation_text="Current Laser Power")
    
    fig.update_layout(
        title="Photon Congestion Index (PCI) vs. Excitation Power (mW)",
        xaxis_title="Excitation Laser Power (mW)",
        yaxis_title="Photon Congestion Index (PCI)",
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Clinical Recommendations & Auto-Optimizer ---
with tab2:
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.markdown("#### 🛡️ Photobleaching Risk Assessment")
        if res['PCI'] < 1e-8:
            st.success("✅ **Low Photobleaching Risk:** Photon density is well within the safe resonant capacity, ensuring prolonged fluorophore stability.")
        elif res['PCI'] < 1e-6:
            st.warning("⚠️ **Moderate Photobleaching Risk:** Monitor exposure duration to prevent signal decay during extended procedures.")
        else:
            st.error("🚨 **High Photobleaching Risk:** Severe photon congestion detected. Rapid fluorophore degradation and tissue heating may occur.")
            
    with col_rec2:
