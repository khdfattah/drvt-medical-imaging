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

def run_drvt_simulation(lambda_exc, lambda_em, p_exc_mw, eta_f, scan_volume, refractive_index, geometry_factor=1.0, mode="CW", pulse_width_ns=10.0, rep_rate_khz=10.0):
    A_exc = (V_EQ / lambda_exc) * geometry_factor
    E_exc = K_CONST * A_exc
    A_em = (V_EQ / lambda_em) * geometry_factor
    E_em = K_CONST * A_em
    r_res_exc = math.sqrt(V_EQ / (math.pi * lambda_exc))
    r_res_em = math.sqrt(V_EQ / (math.pi * lambda_em))
    
    E_exc_J = E_exc * 1.60218e-19
    vg = C_VACUUM / refractive_index
    tau_exc = lambda_exc / vg
    N_res = scan_volume / V_EQ

    if mode == "CW":
        duty_cycle = 1.0
        p_avg_mw = p_exc_mw
        p_peak_mw = p_exc_mw
    else:
        # Duty Cycle = Pulse Width (s) * Repetition Rate (Hz)
        duty_cycle = min(1.0, (pulse_width_ns * 1e-9) * (rep_rate_khz * 1e3))
        p_peak_mw = p_exc_mw
        p_avg_mw = p_peak_mw * duty_cycle

    # Peak metrics (during active pulse)
    N_exc_peak = (p_peak_mw * 1e-3) / E_exc_J
    N_photons_peak = N_exc_peak * tau_exc
    PCI_peak = N_photons_peak / N_res
    
    # Time-averaged metrics (thermal & cumulative photobleaching load)
    N_exc_avg = (p_avg_mw * 1e-3) / E_exc_J
    N_photons_avg = N_exc_avg * tau_exc
    PCI_avg = N_photons_avg / N_res
    CED_avg = PCI_avg * E_exc
    FVI = eta_f * max(0.0, (1.0 - PCI_avg))

    return {
        "A_exc": A_exc, "E_exc": E_exc, "r_res_exc": r_res_exc,
        "A_em": A_em, "E_em": E_em, "r_res_em": r_res_em,
        "N_exc": N_exc_avg, "vg": vg, "tau_exc": tau_exc,
        "N_photons": N_photons_avg, "N_res": N_res,
        "PCI": PCI_avg, "PCI_peak": PCI_peak, "CED": CED_avg, "FVI": FVI,
        "duty_cycle": duty_cycle, "p_avg_mw": p_avg_mw, "p_peak_mw": p_peak_mw
    }

with st.sidebar:
    st.title("Simulation Controls")
    st.markdown("---")
    selected_dye = st.selectbox("Clinical Fluorophore Preset:", list(FLUOROPHORES.keys()), index=1)
    dye_data = FLUOROPHORES[selected_dye]
    st.caption("Clinical Application: **" + dye_data['app'] + "**")
    selected_tissue = st.selectbox("Target Biological Tissue:", list(TISSUES.keys()), index=0)
    tissue_data = TISSUES[selected_tissue]
    
    st.markdown("### Laser Operation Mode")
    laser_mode = st.radio("Select Source Regime:", ["CW (Continuous Wave)", "Pulsed (DRVT Micro-Chip)"], index=0)
    mode_key = "CW" if "CW" in laser_mode else "Pulsed"
    
    if mode_key == "CW":
        p_exc_mw = st.slider("Continuous Laser Power (mW)", min_value=1.0, max_value=500.0, value=30.0, step=1.0)
        pulse_width_ns = 10.0
        rep_rate_khz = 10.0
    else:
        p_exc_mw = st.slider("Pulsed Peak Power (mW)", min_value=10.0, max_value=50000.0, value=1000.0, step=10.0, help="DRVT Micro-chip supports high-gain pulsed peaks.")
        pulse_width_ns = st.slider("Pulse Width (ns)", min_value=1.0, max_value=500.0, value=10.0, step=1.0)
        rep_rate_khz = st.slider("Repetition Rate (kHz)", min_value=1.0, max_value=1000.0, value=50.0, step=5.0)
        
    st.markdown("### Optical Parameters")
    lambda_exc = st.number_input("Excitation Wavelength λ_exc (nm)", value=dye_data["exc"], min_value=10.0, max_value=50000.0, step=5.0)
    lambda_em = st.number_input("Emission Wavelength λ_em (nm)", value=dye_data["em"], min_value=10.0, max_value=50000.0, step=5.0)
    eta_f = st.slider("Fluorescence Quantum Yield η_f", min_value=0.01, max_value=1.00, value=dye_data["eta"], step=0.01)
    
    with st.expander("Advanced Theoretical Parameters"):
        scan_volume = st.number_input("Interaction Scan Volume V_scan (nm³)", value=tissue_data["v_scan"], format="%.2e")
        refractive_index = st.number_input("Tissue Refractive Index (n)", value=tissue_data["n"], min_value=1.0, max_value=2.5, step=0.01)
        geometry_factor = st.slider("Geometric Anisotropy Factor", 0.5, 2.0, 1.0, 0.05)

st.markdown('<div class="main-header">DRVT Medical Imaging Design Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Clinical & Engineering Platform applying Dynamic Resonant Volume Theory (DRVT) by Dr. Khalid Abdel Fattah to optimize fluorescence contrast and prevent photobleaching.</div>', unsafe_allow_html=True)

res = run_drvt_simulation(lambda_exc, lambda_em, p_exc_mw, eta_f, scan_volume, refractive_index, geometry_factor, mode_key, pulse_width_ns, rep_rate_khz)
regime_title, regime_desc = classify_drvt_regime(lambda_exc)
st.info(f"**DRVT Regime:** {regime_title} | **Mode:** {mode_key} (Avg Power: {res['p_avg_mw']:.2f} mW, Duty Cycle: {res['duty_cycle']*100:.4f}%)")

st.subheader("Primary Engineering & Clinical Metrics")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Time-Avg PCI", f"{res['PCI']:.2e}", delta="Safe Regime" if res['PCI'] < 1e-6 else "High Congestion", delta_color="inverse")
with c2:
    st.metric("Fluorescence Visibility (FVI)", f"{res['FVI']:.4f}", delta="Optimal" if res['FVI'] > 0.7 else ("Acceptable" if res['FVI'] > 0.3 else "Poor Contrast"))
with c3:
    st.metric("Resonant Radius (r_res)", f"{res['r_res_exc']:.4f} nm", delta=f"{res['r_res_exc']/A_0:.2f}x Bohr Radius", delta_color="off")
with c4:
    st.metric("Peak Instantaneous PCI", f"{res['PCI_peak']:.2e}", delta=f"Peak: {res['p_peak_mw']} mW", delta_color="off")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dynamic Simulation & Plots",
    "Auto-Optimizer & Clinical Guidance",
    "Complete Physical Parameters",
    "Scenario Comparison & Export",
    "DRVT Hardware Advantage"
])

with tab1:
    st.markdown("#### Impact of Laser Power on Time-Averaged Photon Congestion (PCI)")
    max_p = 500.0 if mode_key == "CW" else 50000.0
    powers = np.linspace(1, max_p, 100)
    pci_list = [run_drvt_simulation(lambda_exc, lambda_em, p, eta_f, scan_volume, refractive_index, geometry_factor, mode_key, pulse_width_ns, rep_rate_khz)["PCI"] for p in powers]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=powers, y=pci_list, name="Time-Avg PCI", line=dict(color="#EF4444", width=3)))
    fig.add_vline(x=p_exc_mw, line_dash="dash", line_color="#1E3A8A", annotation_text="Current Setting")
    fig.update_layout(title=f"PCI vs. {mode_key} Power (mW)", xaxis_title=f"{mode_key} Power (mW)", yaxis_title="Time-Averaged PCI", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        st.markdown("#### Photobleaching Risk Assessment")
        if res['PCI'] < 1e-8:
            st.success("**Low Photobleaching Risk:** Time-averaged photon density is well within safe resonant capacity.")
        elif res['PCI'] < 1e-6:
            st.warning("**Moderate Photobleaching Risk:** Monitor exposure duration during extended procedures.")
        else:
            st.error("**High Photobleaching Risk:** Severe photon congestion detected.")
    with col_rec2:
        st.markdown("#### Engineering & Clinical Recommendation")
        if res['FVI'] > 0.7:
            st.success("**Optimal Imaging Conditions:** Strong fluorescence visibility and high margin contrast.")
        elif res['FVI'] > 0.3:
            st.info("**Acceptable Imaging Conditions:** Usable contrast; pulsed DRVT operation can further reduce thermal load.")
        else:
            st.error("**Poor Fluorescence Visibility:** Low signal or excessive congestion. Use Auto-Optimizer.")
    st.markdown("---")

with tab3:
    df_details = pd.DataFrame({
        "Physical Parameter": [
            "Operation Mode & Duty Cycle", "Average Delivered Power",
            "Excitation Effective Area (A_eff Exc)", "Excitation Photon Energy (E_exc)",
            "Excitation Resonant Radius (r_res Exc)", "Emission Effective Area (A_eff Em)",
            "Group Velocity in Tissue (v_g)", "Time-Avg Photon Flux (Φ)",
            "Tissue Resonant Capacity (N_res)", "Peak Instantaneous PCI",
            "Time-Averaged PCI", "Congestion Energy Density (CED)",
            "Fluorescence Visibility Index (FVI)"
        ],
        "Computed Value": [
            f"{mode_key} ({res['duty_cycle']*100:.4f}%)", f"{res['p_avg_mw']:.3f} mW",
            f"{res['A_exc']:.4f} nm²", f"{res['E_exc']:.4f} eV",
            f"{res['r_res_exc']:.5f} nm", f"{res['A_em']:.4f} nm²",
            f"{res['vg']:.3e} nm/s", f"{res['N_exc']:.3e} photons/s",
            f"{res['N_res']:.3e} states", f"{res['PCI_peak']:.3e}",
            f"{res['PCI']:.3e}", f"{res['CED']:.3e} eV/nm³",
            f"{res['FVI']:.4f}"
        ],
        "DRVT Theoretical Basis": [
            "Duty Cycle = τ_pulse · f_rep", "P_avg = P_peak · Duty Cycle",
            "A_eff = V_eq / λ", "E = k · A_eff (k = 13/3)",
            "r_res = √(286.398 / πλ)", "A_eff = V_eq / λ",
            "v_g = c / n", "Φ_avg = P_avg / E_J",
            "N_res = V_scan / 286.398", "PCI_peak = N_ph_peak / N_res",
            "PCI_avg = PCI_peak · Duty Cycle", "CED = PCI_avg · E_exc",
            "FVI = η_f · (1 - PCI_avg)"
        ]
    })
    st.dataframe(df_details, use_container_width=True, hide_index=True)

with tab4:
    st.markdown("#### Save & Compare Clinical Configurations")
    dye_short_name = selected_dye.split(" (")
    tissue_short_name = selected_tissue.split(" (")
    default_name = f"{dye_short_name} ({mode_key}) - {p_exc_mw}mW"
    scenario_name = st.text_input("Scenario Label:", value=default_name)
    if st.button("Save Current Scenario"):
        st.session_state.saved_scenarios.append({
            "Scenario": scenario_name, "Mode": mode_key, "Fluorophore": dye_short_name,
            "Peak Power (mW)": p_exc_mw, "Avg Power (mW)": round(res['p_avg_mw'], 3),
            "Avg PCI": f"{res['PCI']:.2e}", "FVI": round(res['FVI'], 4),
            "Safety Status": "Safe" if res['PCI'] < 1e-8 else "Warning"
        })
        st.success("Scenario saved!")
    if st.session_state.saved_scenarios:
        df_comp = pd.DataFrame(st.session_state.saved_scenarios)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            csv = df_comp.to_csv(index=False).encode('utf-8')
            st.download_button("Export Comparison Report (CSV)", data=csv, file_name="DRVT_Pulsed_Report.csv", mime="text/csv")
        with col_btn2:
            if st.button("Clear Comparison Table"):
                st.session_state.saved_scenarios = []
                st.rerun()
    else:
        st.info("No scenarios saved yet.")

with tab5:
    st.subheader("Conventional System vs. DRVT Chip Design")
    st.markdown("Applying **Dynamic Resonant Volume Theory (DRVT)** enables miniaturized, high-gain pulsed surgical and microscopic light sources:")
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
    st.info("**Medical Device Integration:** 1.00 mm³ DRVT pulsed micro-cavities allow direct integration into endoscopes and surgical handpieces without thermal damage.")

st.markdown("""
<div class="footer-card">
    <strong>Theoretical Framework & Attribution:</strong><br>
    Based on <em>Dynamic Resonant Volume Theory (DRVT)</em> by <strong>Dr. Khalid Abdel Fattah</strong><br>
    Merowe Institute of Technology, Merowe University of Technology, Sudan | Contact: khdfattah@gmail.com
</div>
""", unsafe_allow_html=True)
