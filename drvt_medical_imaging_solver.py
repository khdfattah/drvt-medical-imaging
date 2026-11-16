import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
    .footer-card {background-color: #F1F5F9; padding: 15px; border-radius: 8px; border-left: 4px solid #1E3A8A; margin-top: 2rem; font-size: 0.9rem; color: #334155;}
</style>
""", unsafe_allow_html=True)

V_EQ = 286.398
K_CONST = 13.0 / 3.0
LAMBDA_C = 0.002426
LAMBDA_R = 91.127
LAMBDA_B = 32550.0
A_0 = 0.0529177
C_VACUUM = 2.998e17

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

if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = []

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

with st.sidebar:
    st.title("Simulation Controls")
    st.markdown("---")
    selected_dye = st.selectbox("Clinical Fluorophore Preset:", list(FLUOROPHORES.keys()), index=1)
    dye_data = FLUOROPHORES[selected_dye]
    st.caption("Clinical Application: **" + dye_data['app'] + "**")
    selected_tissue = st.selectbox("Target Biological Tissue:", list(TISSUES.keys()), index=0)
    tissue_data = TISSUES[selected_tissue]
    st.markdown("### Optical & Laser Parameters")
    lambda_exc = st.number_input("Excitation Wavelength λ_exc (nm)", value=dye_data["exc"], min_value=10.0, max_value=50000.0, step=5.0)
    lambda_em = st.number_input("Emission Wavelength λ_em (nm)", value=dye_data["em"], min_value=10.0, max_value=50000.0, step=5.0)
    p_exc_mw = st.slider("Excitation Laser Power (mW)", min_value=1.0, max_value=500.0, value=30.0, step=1.0)
    eta_f = st.slider("Fluorescence Quantum Yield η_f", min_value=0.01, max_value=1.00, value=dye_data["eta"], step=0.01)
    with st.expander("Advanced Theoretical Parameters"):
        scan_volume = st.number_input("Interaction Scan Volume V_scan (nm³)", value=tissue_data["v_scan"], format="%.2e")
        refractive_index = st.number_input("Tissue Refractive Index (n)", value=tissue_data["n"], min_value=1.0, max_value=2.5, step=0.01)
        geometry_factor = st.slider("Geometric Anisotropy Factor", 0.5, 2.0, 1.0, 0.05)

st.markdown('<div class="main-header">DRVT Medical Imaging Design Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Clinical & Engineering Platform applying Dynamic Resonant Volume Theory (DRVT) by Dr. Khalid Abdel Fattah to optimize fluorescence contrast and prevent photobleaching.</div>', unsafe_allow_html=True)

res = run_drvt_simulation(lambda_exc, lambda_em, p_exc_mw, eta_f, scan_volume, refractive_index, geometry_factor)
regime_title, regime_desc = classify_drvt_regime(lambda_exc)
st.info("**DRVT Resonance Classification:** " + regime_title + " — *" + regime_desc + "*")

st.subheader("Primary Engineering & Clinical Metrics")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Photon Congestion Index (PCI)", f"{res['PCI']:.2e}", delta="Safe Regime" if res['PCI'] < 1e-6 else "High Congestion", delta_color="inverse")
with c2:
    st.metric("Fluorescence Visibility Index (FVI)", f"{res['FVI']:.4f}", delta="Optimal" if res['FVI'] > 0.7 else ("Acceptable" if res['FVI'] > 0.3 else "Poor Contrast"))
with c3:
    st.metric("Resonant State Radius (r_res)", f"{res['r_res_exc']:.4f} nm", delta=f"{res['r_res_exc']/A_0:.2f}x Bohr Radius", delta_color="off")
with c4:
    st.metric("Congestion Energy Density (CED)", f"{res['CED']:.2e} eV/nm³")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dynamic Simulation & Plots",
    "Auto-Optimizer & Clinical Guidance",
    "Complete Physical Parameters",
    "Scenario Comparison & Export",
    "DRVT Hardware Advantage"
])

with tab1:
    st.markdown("#### Impact of Laser Excitation Power on Photon Congestion (PCI)")
    powers = np.linspace(1, 500, 100)
    pci_list = [run_drvt_simulation(lambda_exc, lambda_em, p, eta_f, scan_volume, refractive_index, geometry_factor)["PCI"] for p in powers]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=powers, y=pci_list, name="Photon Congestion Index (PCI)", line=dict(color="#EF4444", width=3)))
    fig.add_vline(x=p_exc_mw, line_dash="dash", line_color="#1E3A8A", annotation_text="Current Laser Power")
    fig.update_layout(title="PCI vs. Laser Power (mW)", xaxis_title="Excitation Laser Power (mW)", yaxis_title="Photon Congestion Index (PCI)", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        st.markdown("#### Photobleaching Risk Assessment")
        if res['PCI'] < 1e-8:
            st.success("**Low Photobleaching Risk:** Photon density is well within the safe resonant capacity.")
        elif res['PCI'] < 1e-6:
            st.warning("**Moderate Photobleaching Risk:** Monitor exposure duration during extended procedures.")
        else:
            st.error("**High Photobleaching Risk:** Severe photon congestion detected.")
    with col_rec2:
        st.markdown("#### Engineering & Clinical Recommendation")
        if res['FVI'] > 0.7:
            st.success("**Optimal Imaging Conditions:** Strong fluorescence visibility and high margin contrast.")
        elif res['FVI'] > 0.3:
            st.info("**Acceptable Imaging Conditions:** Usable contrast; optimization may improve clarity.")
        else:
            st.error("**Poor Fluorescence Visibility:** Low signal or excessive congestion. Use Auto-Optimizer.")
    st.markdown("---")
    st.markdown("#### DRVT Parameter Auto-Optimizer")
    if st.button("Compute Optimal Laser Settings for Current Tissue & Fluorophore"):
        safe_pci_target = 1e-8
        optimal_power = min(max(1.0, p_exc_mw * (safe_pci_target / res['PCI']) if res['PCI'] > 0 else p_exc_mw), 500.0)
        st.success(f"**Optimization Result:** Set excitation power to **{optimal_power:.2f} mW** to maintain PCI < 1e-8. At **{lambda_exc} nm**, A_eff = **{res['A_exc']:.4f} nm²** and r_res = **{res['r_res_exc']:.4f} nm**.")

with tab3:
    df_details = pd.DataFrame({
        "Physical Parameter": [
            "Excitation Effective Area (A_eff Exc)", "Excitation Photon Energy (E_exc)",
            "Excitation Resonant Radius (r_res Exc)", "Emission Effective Area (A_eff Em)",
            "Emission Photon Energy (E_em)", "Group Velocity in Tissue (v_g)",
            "Photon Flux (Φ)", "Transient Photons (N_photons)",
            "Tissue Resonant Capacity (N_res)", "Photon Congestion Index (PCI)",
            "Congestion Energy Density (CED)", "Fluorescence Visibility Index (FVI)"
        ],
        "Computed Value": [
            f"{res['A_exc']:.4f} nm²", f"{res['E_exc']:.4f} eV", f"{res['r_res_exc']:.5f} nm",
            f"{res['A_em']:.4f} nm²", f"{res['E_em']:.4f} eV", f"{res['vg']:.3e} nm/s",
            f"{res['N_exc']:.3e} photons/s", f"{res['N_photons']:.3e} photons",
            f"{res['N_res']:.3e} resonant states", f"{res['PCI']:.3e}",
            f"{res['CED']:.3e} eV/nm³", f"{res['FVI']:.4f}"
        ],
        "DRVT Theoretical Basis": [
            "A_eff = V_eq / λ", "E = k · A_eff (k = 13/3)", "r_res = √(286.398 / πλ)",
            "A_eff = V_eq / λ", "E = k · A_eff", "v_g = c / n", "Φ = P / E_J",
            "N_ph = Φ · (λ / v_g)", "N_res = V_scan / 286.398", "PCI = N_ph / N_res",
            "CED = PCI · E_exc", "FVI = η_f · (1 - PCI)"
        ]
    })
    st.dataframe(df_details, use_container_width=True, hide_index=True)

with tab4:
    st.markdown("#### Save & Compare Clinical Configurations")
    dye_short_name = selected_dye.split(" (")
    tissue_short_name = selected_tissue.split(" (")
    default_name = f"{dye_short_name} - {p_exc_mw}mW"
    scenario_name = st.text_input("Scenario Label:", value=default_name)
    if st.button("Save Current Scenario"):
        st.session_state.saved_scenarios.append({
            "Scenario": scenario_name, "Fluorophore": dye_short_name, "Tissue": tissue_short_name,
            "Power (mW)": p_exc_mw, "r_res (nm)": round(res['r_res_exc'], 5),
            "PCI": f"{res['PCI']:.2e}", "FVI": round(res['FVI'], 4),
            "Safety Status": "Safe" if res['PCI'] < 1e-8 else "Warning"
        })
        st.success("Scenario saved!")
    if st.session_state.saved_scenarios:
        df_comp = pd.DataFrame(st.session_state.saved_scenarios)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            csv = df_comp.to_csv(index=False).encode('utf-8')
            st.download_button("Export Comparison Report (CSV)", data=csv, file_name="DRVT_Report.csv", mime="text/csv")
        with col_btn2:
            if st.button("Clear Comparison Table"):
                st.session_state.saved_scenarios = []
                st.rerun()
    else:
        st.info("No scenarios saved yet.")

with tab5:
    st.subheader("Conventional System vs. DRVT Chip Design")
    st.markdown("Applying **Dynamic Resonant Volume Theory (DRVT)** enables miniaturized surgical and microscopic light sources:")
    df_hardware = pd.DataFrame({
        "Engineering Metric": [
            "Active Cavity Volume", "Operating Gas Pressure", "Small-Signal Gain (g₀)",
            "Output Power Regime", "Thermal Management", "Ballast Reservoir", "Volumetric Efficiency"
        ],
        "Conventional Macro System": [
            "314.16 mm³ (40 cm tube)", "3.6 Torr (Low-pressure CW)", "0.0020 cm⁻¹",
            "2 - 5 mW (Continuous Wave)", "Passive Air / Water Jacket", "~ 63.0 mL external jacket", "0.10%"
        ],
        "DRVT Chip Design": [
            "1.00 mm³ (Micro-cube)", "180 Torr (High-gain pulsed)", "0.0400 cm⁻¹ (20.0x boost)",
            "11.12 kW (Pulsed Peak)", "Synthetic CVD Diamond (T_core = 20.0 °C)", "0.20 mL integrated on-chip", "4.0%"
        ]
    })
    st.dataframe(df_hardware, use_container_width=True, hide_index=True)
    st.info("**Medical Device Integration:** 1.00 mm³ DRVT micro-cavities allow direct integration into endoscopes and surgical handpieces.")

st.markdown("""
<div class="footer-card">
    <strong>Theoretical Framework & Attribution:</strong><br>
    Based on <em>Dynamic Resonant Volume Theory (DRVT)</em> by <strong>Dr. Khalid Abdel Fattah</strong><br>
    Merowe Institute of Technology, Merowe University of Technology, Sudan | Contact: khdfattah@gmail.com
</div>
""", unsafe_allow_html=True)
